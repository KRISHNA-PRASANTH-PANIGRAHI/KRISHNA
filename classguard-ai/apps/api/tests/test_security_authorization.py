"""Adversarial requests against disposable tenants, never a live user database."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from classguard.auth import Principal, get_principal
from classguard.database import Base, get_database, make_engine
from classguard.main import app
from classguard.models import Classroom, Enrollment, Institution, Invitation, Membership


@pytest.fixture
def attack_lab(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'security.db'}")
    Base.metadata.create_all(engine)
    ids = {name: uuid4() for name in (
        "tenant_a", "tenant_b", "actor", "teacher_b", "student", "newcomer", "class_a", "class_b",
    )}
    with Session(engine) as db:
        db.add_all([Institution(id=ids["tenant_a"], name="A"), Institution(id=ids["tenant_b"], name="B")])
        db.flush()
        db.add_all([
            Membership(institution_id=ids["tenant_a"], user_id=ids["actor"], role="admin"),
            Membership(institution_id=ids["tenant_b"], user_id=ids["actor"], role="student"),
            Membership(institution_id=ids["tenant_b"], user_id=ids["teacher_b"], role="teacher"),
            Membership(institution_id=ids["tenant_a"], user_id=ids["student"], role="student"),
            Membership(institution_id=ids["tenant_b"], user_id=ids["student"], role="student"),
        ])
        db.flush()
        for name, tenant, owner in (("class_a", "tenant_a", "actor"), ("class_b", "tenant_b", "teacher_b")):
            db.add(Classroom(id=ids[name], institution_id=ids[tenant], created_by=ids[owner],
                             title=name, subject="Math", starts_at=datetime.now(UTC), duration_minutes=45))
        db.flush()
        db.add_all([
            Enrollment(classroom_id=ids["class_a"], institution_id=ids["tenant_a"], user_id=ids["student"]),
            Enrollment(classroom_id=ids["class_b"], institution_id=ids["tenant_b"], user_id=ids["student"]),
        ])
        db.commit()

    # Only the provider boundary is replaced. Every real permission query runs.
    actor = [Principal(ids["actor"], "owner@school.test")]
    def database_dependency():
        with Session(engine) as db:
            yield db
    def sign_in(name, email):
        actor[0] = Principal(ids[name], email)

    app.dependency_overrides[get_database] = database_dependency
    app.dependency_overrides[get_principal] = lambda: actor[0]
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, engine=engine, ids=ids, sign_in=sign_in,
                              a=f"/v1/institutions/{ids['tenant_a']}", b=f"/v1/institutions/{ids['tenant_b']}")
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.parametrize("email,other_email", [
    ("strasse@school.test", "straße@school.test"),
    ("kate@school.test", "Kate@school.test"),
])
def test_distinct_unicode_mailbox_cannot_redeem_copied_invitation(attack_lab, email, other_email):
    lab = attack_lab
    invitation = lab.client.post(f"{lab.a}/invitations", json={"email": email, "role": "teacher"}).json()
    lab.sign_in("newcomer", other_email)
    result = lab.client.post("/v1/invitations/accept", json={"token": invitation["token"]})
    assert result.status_code == 403, result.text
    with Session(lab.engine) as db:
        assert db.get(Membership, (lab.ids["tenant_a"], lab.ids["newcomer"])) is None
        assert db.get(Invitation, UUID(invitation["id"])).accepted_at is None
    lab.sign_in("newcomer", email.upper())
    assert lab.client.post("/v1/invitations/accept", json={"token": invitation["token"]}).status_code == 200


def test_creating_distinct_unicode_invite_does_not_revoke_another_mailbox(attack_lab):
    lab = attack_lab
    first = lab.client.post(f"{lab.a}/invitations", json={"email": "strasse@school.test", "role": "student"}).json()
    second = lab.client.post(f"{lab.a}/invitations", json={"email": "straße@school.test", "role": "student"}).json()
    assert second["email"] == "straße@school.test"
    records = lab.client.get(f"{lab.a}/invitations").json()["items"]
    assert {record["status"] for record in records} == {"pending"}
    lab.sign_in("newcomer", "strasse@school.test")
    assert lab.client.post("/v1/invitations/accept", json={"token": first["token"]}).status_code == 200


def test_admin_in_one_institution_cannot_borrow_that_role_in_another(attack_lab):
    lab = attack_lab
    member_path = f"{lab.b}/members/{lab.ids['actor']}"
    assert lab.client.patch(member_path, json={"role": "teacher"}).status_code == 403
    assert lab.client.get(f"{lab.b}/members").status_code == 403
    assert lab.client.get(f"{lab.b}/invitations").status_code == 403
    assert lab.client.post(f"{lab.b}/invitations", json={"email": "helper@school.test", "role": "teacher"}).status_code == 403
    enrollment_path = f"{lab.b}/classes/{lab.ids['class_b']}/enrollments"
    assert lab.client.post(enrollment_path, json={"user_id": str(lab.ids['actor'])}).status_code == 403
    assert lab.client.delete(f"{enrollment_path}/{lab.ids['student']}").status_code == 403
    with Session(lab.engine) as db:
        assert db.get(Membership, (lab.ids["tenant_b"], lab.ids["actor"])).role == "student"
        assert db.get(Enrollment, (lab.ids["class_b"], lab.ids["tenant_b"], lab.ids["student"])) is not None


def test_shared_member_uuid_mutation_stays_inside_requested_institution(attack_lab):
    lab = attack_lab
    response = lab.client.patch(f"{lab.a}/members/{lab.ids['student']}", json={"role": "teacher", "active": False})
    assert response.status_code == 200
    with Session(lab.engine) as db:
        changed = db.get(Membership, (lab.ids["tenant_a"], lab.ids["student"]))
        untouched = db.get(Membership, (lab.ids["tenant_b"], lab.ids["student"]))
        assert changed.role == "teacher" and not changed.active
        assert untouched.role == "student" and untouched.active
        assert db.get(Enrollment, (lab.ids["class_a"], lab.ids["tenant_a"], lab.ids["student"])) is None
        assert db.get(Enrollment, (lab.ids["class_b"], lab.ids["tenant_b"], lab.ids["student"])) is not None


@pytest.mark.parametrize("operation", ["read", "enroll", "remove"])
def test_foreign_class_id_cannot_be_laundered_through_admins_own_tenant(attack_lab, operation):
    lab = attack_lab
    route = f"{lab.a}/classes/{lab.ids['class_b']}/enrollments"
    if operation == "read":
        response = lab.client.get(route)
    elif operation == "enroll":
        response = lab.client.post(route, json={"user_id": str(lab.ids['student'])})
    else:
        response = lab.client.delete(f"{route}/{lab.ids['student']}")
    assert response.status_code == 404
    with Session(lab.engine) as db:
        assert db.get(Enrollment, (lab.ids["class_b"], lab.ids["tenant_b"], lab.ids["student"])) is not None


@pytest.mark.parametrize("forged", [
    {"institution_id": "foreign"}, {"user_id": "victim"}, {"role": "admin"},
    {"active": True}, {"accepted_at": None}, {"expires_at": "2099-01-01T00:00:00Z"},
])
def test_invitation_body_cannot_override_bound_authority(attack_lab, forged):
    lab = attack_lab
    invitation = lab.client.post(f"{lab.a}/invitations", json={"email": "new@school.test", "role": "student"}).json()
    lab.sign_in("newcomer", "new@school.test")
    result = lab.client.post("/v1/invitations/accept", json={"token": invitation["token"], **forged})
    assert result.status_code == 422
    with Session(lab.engine) as db:
        assert db.get(Membership, (lab.ids["tenant_a"], lab.ids["newcomer"])) is None
        assert db.get(Invitation, UUID(invitation["id"])).accepted_at is None


def test_sql_metacharacters_are_stored_as_data_and_do_not_change_access(attack_lab):
    lab = attack_lab
    injection = "Robert'); DROP TABLE memberships;--"
    response = lab.client.post(f"{lab.a}/classes", json={
        "title": injection, "subject": "Math", "starts_at": "2026-11-06T10:00:00Z", "duration_minutes": 45,
    })
    assert response.status_code == 201
    assert response.json()["title"] == injection
    with Session(lab.engine) as db:
        assert db.scalar(select(func.count()).select_from(Membership)) == 5
        assert db.get(Membership, (lab.ids["tenant_b"], lab.ids["actor"])).role == "student"
