"""ASGI entry point. Initialize the database with the CLI before first use."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import Principal, get_principal, require_membership
from .config import get_settings
from .database import get_database
from .identities import sync_identity
from .models import Classroom, Enrollment, Institution, Membership
from .onboarding import router as onboarding_router
from .schemas import ClassCreate, ClassesResponse, ClassResponse, MeResponse, MembershipResponse
from .security import RequestGuardMiddleware

app = FastAPI(title="ClassGuard AI API", version="0.2.0")
app.add_middleware(RequestGuardMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

Database = Annotated[Session, Depends(get_database)]
CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
app.include_router(onboarding_router)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request, error):
    # Validation input can contain invitation secrets; do not echo payloads.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]})


@app.middleware("http")
async def response_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": "classguard-api"}


@app.get("/v1/capabilities")
def capabilities():
    return {
        "authentication_configured": get_settings().authentication_configured,
        "stage": "onboarding",
        "features": {
            "class_planning": True,
            "institution_management": True,
            "invitations": True,
            "enrollment": True,
            "verified_entry": False,
            "live_video": False,
            "attendance": False,
            "polls": False,
        },
    }


@app.get("/v1/me", response_model=MeResponse)
def me(principal: CurrentPrincipal, database: Database):
    sync_identity(database, principal)
    database.commit()
    rows = database.execute(
        select(Membership, Institution)
        .join(Institution, Institution.id == Membership.institution_id)
        .where(
            Membership.user_id == principal.user_id,
            Membership.active.is_(True),
            Institution.active.is_(True),
        )
        .order_by(Institution.name)
    ).all()
    return MeResponse(
        id=principal.user_id,
        email=principal.email,
        memberships=[
            MembershipResponse(
                institution_id=institution.id,
                institution_name=institution.name,
                role=membership.role,
            )
            for membership, institution in rows
        ],
    )


@app.get("/v1/institutions/{institution_id}/classes", response_model=ClassesResponse)
def list_classes(institution_id: UUID, principal: CurrentPrincipal, database: Database):
    membership = require_membership(database, institution_id, principal)
    query = select(Classroom).where(Classroom.institution_id == institution_id)
    if membership.role == "teacher":
        query = query.where(Classroom.created_by == principal.user_id)
    elif membership.role == "student":
        query = query.join(
            Enrollment,
            (Enrollment.classroom_id == Classroom.id)
            & (Enrollment.institution_id == Classroom.institution_id),
        ).where(Enrollment.user_id == principal.user_id)
    elif membership.role != "admin":
        raise HTTPException(status_code=403, detail="Role is not supported")
    classes = database.scalars(query.order_by(Classroom.starts_at, Classroom.id)).all()
    return ClassesResponse(items=[ClassResponse.model_validate(item) for item in classes])


@app.post("/v1/institutions/{institution_id}/classes", response_model=ClassResponse, status_code=201)
def create_class(
    institution_id: UUID,
    payload: ClassCreate,
    principal: CurrentPrincipal,
    database: Database,
):
    membership = require_membership(database, institution_id, principal)
    if membership.role not in {"admin", "teacher"}:
        raise HTTPException(status_code=403, detail="Only an admin or teacher can create a class")
    classroom = Classroom(
        institution_id=institution_id,
        created_by=principal.user_id,
        **payload.model_dump(),
    )
    database.add(classroom)
    database.commit()
    database.refresh(classroom)
    return classroom
