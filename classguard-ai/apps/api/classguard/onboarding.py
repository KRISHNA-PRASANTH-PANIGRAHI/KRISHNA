"""Institution administration with tenant-scoped permissions and one-use invites."""

from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import Principal, get_principal, require_membership
from .database import get_database
from .email_addresses import normalize_email_address
from .identities import sync_identity
from .models import AccountIdentity, Classroom, Enrollment, Institution, Invitation, Membership
from .schemas import (
    EnrollmentCreate, InstitutionCreate, InvitationAccept, InvitationCreate,
    InvitationCreated, InvitationResponse, InvitationsResponse, MemberResponse,
    MembersResponse, MemberUpdate, MembershipResponse,
)

router = APIRouter(prefix="/v1", tags=["Institution administration"])
Database = Annotated[Session, Depends(get_database)]
CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def lock_institution(database: Session, institution_id: UUID) -> Institution:
    institution = database.scalar(
        select(Institution)
        .where(Institution.id == institution_id, Institution.active.is_(True))
        .with_for_update()
    )
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


def require_admin(database: Session, institution_id: UUID, principal: Principal) -> Membership:
    membership = require_membership(database, institution_id, principal)
    if membership.role != "admin":
        raise HTTPException(status_code=403, detail="Only an administrator can manage institution access")
    return membership


def member_response(database: Session, member: Membership) -> MemberResponse:
    identity = database.get(AccountIdentity, member.user_id)
    return MemberResponse(
        user_id=member.user_id, email=identity.email if identity else None,
        role=member.role, active=member.active,
    )


def invitation_response(invitation: Invitation) -> InvitationResponse:
    if invitation.accepted_at is not None:
        status = "accepted"
    elif invitation.revoked_at is not None:
        status = "revoked"
    elif invitation.expires_at <= datetime.now(UTC):
        status = "expired"
    else:
        status = "pending"
    return InvitationResponse(
        id=invitation.id, email=invitation.email, role=invitation.role,
        created_at=invitation.created_at, expires_at=invitation.expires_at, status=status,
    )


def require_class_manager(
    database: Session, institution_id: UUID, classroom_id: UUID, principal: Principal,
) -> Classroom:
    membership = require_membership(database, institution_id, principal)
    if membership.role not in {"admin", "teacher"}:
        raise HTTPException(status_code=403, detail="Only an administrator or teacher can manage enrollment")
    query = select(Classroom).where(
        Classroom.id == classroom_id, Classroom.institution_id == institution_id,
    )
    if membership.role == "teacher":
        query = query.where(Classroom.created_by == principal.user_id)
    classroom = database.scalar(query)
    if classroom is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return classroom


@router.post("/institutions", response_model=MembershipResponse, status_code=201)
def create_institution(payload: InstitutionCreate, principal: CurrentPrincipal, database: Database):
    institution = Institution(name=payload.name)
    database.add(institution)
    database.flush()
    database.add(Membership(institution_id=institution.id, user_id=principal.user_id, role="admin"))
    sync_identity(database, principal)
    database.commit()
    return MembershipResponse(
        institution_id=institution.id, institution_name=institution.name, role="admin",
    )


@router.get("/institutions/{institution_id}/members", response_model=MembersResponse)
def list_members(institution_id: UUID, principal: CurrentPrincipal, database: Database):
    actor = require_membership(database, institution_id, principal)
    if actor.role not in {"admin", "teacher"}:
        raise HTTPException(status_code=403, detail="Only an administrator or teacher can view the directory")
    query = (
        select(Membership, AccountIdentity.email)
        .outerjoin(AccountIdentity, AccountIdentity.user_id == Membership.user_id)
        .where(Membership.institution_id == institution_id)
    )
    if actor.role == "teacher":
        query = query.where(Membership.role == "student", Membership.active.is_(True))
    rows = database.execute(query.order_by(AccountIdentity.email, Membership.user_id)).all()
    return MembersResponse(items=[
        MemberResponse(user_id=member.user_id, email=email, role=member.role, active=member.active)
        for member, email in rows
    ])


@router.patch("/institutions/{institution_id}/members/{user_id}", response_model=MemberResponse)
def update_member(
    institution_id: UUID, user_id: UUID, payload: MemberUpdate,
    principal: CurrentPrincipal, database: Database,
):
    lock_institution(database, institution_id)
    require_admin(database, institution_id, principal)
    member = database.get(Membership, (institution_id, user_id))
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == "admin":
        raise HTTPException(status_code=403, detail="Administrator memberships cannot be changed here")
    if payload.role is not None and payload.role != member.role:
        # Changing a role must not resurrect historical student enrollments.
        database.execute(delete(Enrollment).where(
            Enrollment.institution_id == institution_id, Enrollment.user_id == user_id,
        ))
        member.role = payload.role
    if payload.active is not None:
        member.active = payload.active
    database.commit()
    return member_response(database, member)


@router.get("/institutions/{institution_id}/invitations", response_model=InvitationsResponse)
def list_invitations(institution_id: UUID, principal: CurrentPrincipal, database: Database):
    require_admin(database, institution_id, principal)
    invitations = database.scalars(select(Invitation).where(
        Invitation.institution_id == institution_id,
    ).order_by(Invitation.created_at.desc(), Invitation.id)).all()
    return InvitationsResponse(items=[invitation_response(item) for item in invitations])


@router.post("/institutions/{institution_id}/invitations", response_model=InvitationCreated, status_code=201)
def create_invitation(
    institution_id: UUID, payload: InvitationCreate,
    principal: CurrentPrincipal, database: Database,
):
    lock_institution(database, institution_id)
    require_admin(database, institution_id, principal)
    now = datetime.now(UTC)
    # Reissuing also revokes expired outstanding entries, keeping the partial
    # unique index valid without a clock-dependent database predicate.
    database.execute(update(Invitation).where(
        Invitation.institution_id == institution_id, Invitation.email == payload.email,
        Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None),
    ).values(revoked_at=now))
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        institution_id=institution_id, email=payload.email, role=payload.role,
        token_hash=hashlib.sha256(token.encode("ascii")).hexdigest(),
        created_by=principal.user_id, created_at=now, expires_at=now + timedelta(days=7),
    )
    database.add(invitation)
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(status_code=409, detail="Invitation changed concurrently. Please try again.") from error
    return InvitationCreated(**invitation_response(invitation).model_dump(), token=token)


@router.post("/institutions/{institution_id}/invitations/{invitation_id}/revoke", response_model=InvitationResponse)
def revoke_invitation(
    institution_id: UUID, invitation_id: UUID, principal: CurrentPrincipal, database: Database,
):
    lock_institution(database, institution_id)
    require_admin(database, institution_id, principal)
    invitation = database.scalar(select(Invitation).where(
        Invitation.id == invitation_id, Invitation.institution_id == institution_id,
    ))
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="An accepted invitation cannot be revoked. Manage the member instead.")
    database.execute(update(Invitation).where(
        Invitation.id == invitation_id, Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None),
    ).values(revoked_at=datetime.now(UTC)))
    database.commit()
    database.refresh(invitation)
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="An accepted invitation cannot be revoked. Manage the member instead.")
    return invitation_response(invitation)


@router.post("/invitations/accept", response_model=MembershipResponse)
def accept_invitation(payload: InvitationAccept, principal: CurrentPrincipal, database: Database):
    token_hash = hashlib.sha256(payload.token.encode("ascii")).hexdigest()
    invitation = database.scalar(select(Invitation).where(Invitation.token_hash == token_hash))
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    institution = lock_institution(database, invitation.institution_id)
    if not principal.email or normalize_email_address(principal.email) != invitation.email:
        raise HTTPException(status_code=403, detail="Sign in using the email address this invitation was sent to")
    if invitation_response(invitation).status != "pending":
        raise HTTPException(status_code=410, detail="This invitation has expired, was revoked, or has already been used")
    if database.get(Membership, (institution.id, principal.user_id)) is not None:
        raise HTTPException(status_code=409, detail="You already have a membership. Ask an administrator to manage its role or access.")
    now = datetime.now(UTC)
    # Conditional consumption, not SELECT FOR UPDATE alone, protects SQLite as
    # well as PostgreSQL. Membership creation and consumption commit together.
    consumed = database.execute(update(Invitation).where(
        Invitation.id == invitation.id, Invitation.token_hash == token_hash,
        Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None),
        Invitation.expires_at > now,
    ).values(accepted_at=now))
    if consumed.rowcount != 1:
        database.rollback()
        raise HTTPException(status_code=410, detail="This invitation is no longer available")
    database.add(Membership(
        institution_id=institution.id, user_id=principal.user_id, role=invitation.role,
    ))
    try:
        database.flush()
        sync_identity(database, principal)
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(status_code=409, detail="Membership changed concurrently. Refresh your institution list.") from error
    return MembershipResponse(
        institution_id=institution.id, institution_name=institution.name, role=invitation.role,
    )


@router.get("/institutions/{institution_id}/classes/{classroom_id}/enrollments", response_model=MembersResponse)
def list_enrollments(
    institution_id: UUID, classroom_id: UUID, principal: CurrentPrincipal, database: Database,
):
    require_class_manager(database, institution_id, classroom_id, principal)
    rows = database.execute(
        select(Membership, AccountIdentity.email)
        .join(Enrollment, (Enrollment.institution_id == Membership.institution_id)
              & (Enrollment.user_id == Membership.user_id))
        .outerjoin(AccountIdentity, AccountIdentity.user_id == Membership.user_id)
        .where(Enrollment.institution_id == institution_id, Enrollment.classroom_id == classroom_id)
        .order_by(AccountIdentity.email, Membership.user_id)
    ).all()
    return MembersResponse(items=[
        MemberResponse(user_id=member.user_id, email=email, role=member.role, active=member.active)
        for member, email in rows
    ])


@router.post("/institutions/{institution_id}/classes/{classroom_id}/enrollments", response_model=MemberResponse)
def enroll_student(
    institution_id: UUID, classroom_id: UUID, payload: EnrollmentCreate,
    principal: CurrentPrincipal, database: Database,
):
    lock_institution(database, institution_id)
    require_class_manager(database, institution_id, classroom_id, principal)
    member = database.get(Membership, (institution_id, payload.user_id))
    if member is None or not member.active or member.role != "student":
        raise HTTPException(status_code=404, detail="Active student member not found")
    enrollment_id = (classroom_id, institution_id, payload.user_id)
    if database.get(Enrollment, enrollment_id) is None:
        database.add(Enrollment(
            classroom_id=classroom_id, institution_id=institution_id, user_id=payload.user_id,
        ))
        try:
            database.commit()
        except IntegrityError as error:
            database.rollback()
            if database.get(Enrollment, enrollment_id) is None:
                raise HTTPException(status_code=409, detail="Enrollment changed concurrently. Please try again.") from error
    return member_response(database, member)


@router.delete("/institutions/{institution_id}/classes/{classroom_id}/enrollments/{user_id}", status_code=204)
def unenroll_student(
    institution_id: UUID, classroom_id: UUID, user_id: UUID,
    principal: CurrentPrincipal, database: Database,
):
    lock_institution(database, institution_id)
    require_class_manager(database, institution_id, classroom_id, principal)
    database.execute(delete(Enrollment).where(
        Enrollment.classroom_id == classroom_id, Enrollment.institution_id == institution_id,
        Enrollment.user_id == user_id,
    ))
    database.commit()
    return Response(status_code=204)
