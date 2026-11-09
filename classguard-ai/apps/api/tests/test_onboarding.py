from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import hashlib
from types import SimpleNamespace
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from classguard.auth import Principal, get_principal
from classguard.database import Base, get_database, make_engine
from classguard.main import app
from classguard.models import AccountIdentity, Classroom, Enrollment, Institution, Invitation, Membership


@pytest.fixture
def access(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'onboarding.db'}")
    ids = {name: uuid4() for name in (
        "tenant", "foreign_tenant", "admin", "teacher", "other_teacher", "student",
        "inactive", "outsider", "newcomer", "second_newcomer", "classroom", "other_classroom", "foreign_classroom",
    )}
    Base.metadata.create_all(engine)
    with Session(engine) as database:
        database.add_all([
            Institution(id=ids["tenant"], name="Example College"),
            Institution(id=ids["foreign_tenant"], name="Other College"),
        ])
        database.flush()
        for name, role, active in (
            ("admin", "admin", True), ("teacher", "teacher", True),
            ("other_teacher", "teacher", True), ("student", "student", True), ("inactive", "student", False),
        ):
            database.add(Membership(institution_id=ids["tenant"], user_id=ids[name], role=role, active=active))
            database.add(AccountIdentity(user_id=ids[name], email=f"{name}@school.test"))
        database.add(Membership(institution_id=ids["foreign_tenant"], user_id=ids["outsider"], role="student"))
        database.flush()
        for name, institution, teacher in (
            ("classroom", "tenant", "teacher"), ("other_classroom", "tenant", "other_teacher"),
            ("foreign_classroom", "foreign_tenant", "outsider"),
        ):
            database.add(Classroom(
                id=ids[name], institution_id=ids[institution], created_by=ids[teacher], title=name,
                subject="Science", starts_at=datetime.now(UTC), duration_minutes=45,
            ))
        database.commit()

    actor = [Principal(ids["admin"], "admin@school.test")]

    def database_dependency():
        with Session(engine) as database:
            yield database

    def sign_in(name, email="default"):
        actor[0] = Principal(ids[name], f"{name}@school.test" if email == "default" else email)

    app.dependency_overrides[get_database] = database_dependency
    app.dependency_overrides[get_principal] = lambda: actor[0]
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client, engine=engine, ids=ids, sign_in=sign_in,
            root=f"/v1/institutions/{ids['tenant']}",
        )
    app.dependency_overrides.clear()
    engine.dispose()


def invite(access, email="newcomer@school.test", role="student"):
    result = access.client.post(f"{access.root}/invitations", json={"email": email, "role": role})
    assert result.status_code == 201, result.text
    return result.json()


def accept(access, token):
    return access.client.post("/v1/invitations/accept", json={"token": token})


def test_institution_creation_assigns_only_callers_admin_membership(access):
    access.sign_in("newcomer")
    response = access.client.post("/v1/institutions", json={"name": "  New Institute  "})
    assert response.status_code == 201
    assert response.json()["institution_name"] == "New Institute"
    assert response.json()["role"] == "admin"
    memberships = access.client.get("/v1/me").json()["memberships"]
    assert memberships == [response.json()]
    with Session(access.engine) as database:
        member = database.get(Membership, (UUID(response.json()["institution_id"]), access.ids["newcomer"]))
        assert member.role == "admin" and member.active
        assert database.get(AccountIdentity, access.ids["newcomer"]).email == "newcomer@school.test"
    assert access.client.post("/v1/institutions", json={"name": " ", "user_id": str(access.ids["admin"])}).status_code == 422


def test_members_directory_is_role_scoped_and_uses_verified_identity(access):
    assert len(access.client.get(f"{access.root}/members").json()["items"]) == 5
    access.sign_in("teacher")
    assert access.client.get(f"{access.root}/members").json()["items"] == [{
        "user_id": str(access.ids["student"]), "email": "student@school.test", "role": "student", "active": True,
    }]
    access.sign_in("student", "UPDATED@school.test")
    assert access.client.get("/v1/me").status_code == 200
    assert access.client.get(f"{access.root}/members").status_code == 403
    access.sign_in("admin")
    members = access.client.get(f"{access.root}/members").json()["items"]
    assert next(item for item in members if item["role"] == "student" and item["active"])["email"] == "updated@school.test"


@pytest.mark.parametrize("actor,status", [("teacher", 403), ("student", 403), ("outsider", 404), ("inactive", 404)])
def test_only_active_admin_can_manage_members_and_invites(access, actor, status):
    access.sign_in(actor)
    assert access.client.get(f"{access.root}/invitations").status_code == status
    assert access.client.post(f"{access.root}/invitations", json={"email": "new@school.test", "role": "teacher"}).status_code == status
    assert access.client.patch(f"{access.root}/members/{access.ids['student']}", json={"role": "teacher"}).status_code == status


def test_invitation_secret_is_returned_once_hash_only_at_rest_and_email_bound(access):
    invitation = invite(access, "  Newcomer@SCHOOL.test  ", "teacher")
    assert invitation["email"] == "newcomer@school.test" and invitation["status"] == "pending"
    with Session(access.engine) as database:
        stored = database.get(Invitation, UUID(invitation["id"]))
        assert stored.token_hash == hashlib.sha256(invitation["token"].encode("ascii")).hexdigest()
        assert stored.expires_at - stored.created_at == timedelta(days=7)
        assert invitation["token"] not in repr(stored.__dict__)
    listed = access.client.get(f"{access.root}/invitations").json()["items"][0]
    assert "token" not in listed and "token_hash" not in listed
    access.sign_in("second_newcomer")
    assert accept(access, invitation["token"]).status_code == 403
    access.sign_in("newcomer", None)
    assert accept(access, invitation["token"]).status_code == 403
    access.sign_in("newcomer", "NEWCOMER@school.test")
    response = accept(access, invitation["token"])
    assert response.status_code == 200 and response.json()["role"] == "teacher"
    assert accept(access, invitation["token"]).status_code == 410
    assert access.client.get("/v1/me").json()["memberships"] == [response.json()]
    access.sign_in("admin")
    assert access.client.get(f"{access.root}/invitations").json()["items"][0]["status"] == "accepted"


def test_invitation_reissue_revokes_old_link(access):
    old = invite(access)
    new = invite(access, role="teacher")
    access.sign_in("newcomer")
    assert accept(access, old["token"]).status_code == 410
    assert accept(access, new["token"]).json()["role"] == "teacher"


@pytest.mark.parametrize("state", ["expired", "revoked", "inactive_institution"])
def test_expired_revoked_or_inactive_institution_invites_fail_without_membership(access, state):
    invitation = invite(access)
    if state == "revoked":
        response = access.client.post(f"{access.root}/invitations/{invitation['id']}/revoke")
        assert response.status_code == 200 and response.json()["status"] == "revoked"
    else:
        with Session(access.engine) as database:
            if state == "expired":
                database.get(Invitation, UUID(invitation["id"])).expires_at = datetime.now(UTC) - timedelta(seconds=1)
            else:
                database.get(Institution, access.ids["tenant"]).active = False
            database.commit()
    access.sign_in("newcomer")
    assert accept(access, invitation["token"]).status_code == (404 if state == "inactive_institution" else 410)
    assert access.client.get("/v1/me").json()["memberships"] == []


@pytest.mark.parametrize("member", ["student", "inactive", "admin"])
def test_invitation_cannot_change_or_reactivate_existing_membership(access, member):
    invitation = invite(access, email=f"{member}@school.test", role="teacher")
    access.sign_in(member)
    assert accept(access, invitation["token"]).status_code == 409
    with Session(access.engine) as database:
        record = database.get(Membership, (access.ids["tenant"], access.ids[member]))
        assert record.role == ("admin" if member == "admin" else "student")
        assert record.active == (member != "inactive")
        assert database.get(Invitation, UUID(invitation["id"])).accepted_at is None


def test_invites_cannot_grant_admin_or_accept_forged_fields(access):
    assert access.client.post(f"{access.root}/invitations", json={"email": "a@school.test", "role": "admin"}).status_code == 422
    assert access.client.post(f"{access.root}/invitations", json={"email": "missing-at", "role": "student"}).status_code == 422
    invitation = invite(access)
    access.sign_in("newcomer")
    assert access.client.post("/v1/invitations/accept", json={"token": invitation["token"], "role": "admin"}).status_code == 422
    assert accept(access, "x" * 43).status_code == 404


def test_cross_tenant_invitation_and_member_ids_are_not_authority(access):
    invitation = invite(access)
    foreign = f"/v1/institutions/{access.ids['foreign_tenant']}"
    assert access.client.get(f"{foreign}/members").status_code == 404
    assert access.client.get(f"{foreign}/invitations").status_code == 404
    assert access.client.post(f"{foreign}/invitations/{invitation['id']}/revoke").status_code == 404
    assert access.client.patch(f"{access.root}/members/{access.ids['outsider']}", json={"active": False}).status_code == 404
    assert access.client.post(f"{access.root}/invitations/{uuid4()}/revoke").status_code == 404


def test_admins_cannot_be_demoted_deactivated_or_created_through_member_edit(access):
    admin_path = f"{access.root}/members/{access.ids['admin']}"
    assert access.client.patch(admin_path, json={"active": False}).status_code == 403
    assert access.client.patch(admin_path, json={"role": "teacher"}).status_code == 403
    student_path = f"{access.root}/members/{access.ids['student']}"
    for payload in ({"role": "admin"}, {}, {"active": None}, {"active": "false"}, {"email": "forged@school.test"}):
        assert access.client.patch(student_path, json=payload).status_code == 422


def test_membership_deactivation_blocks_next_request_and_explicit_reactivation_restores_access(access):
    path = f"{access.root}/members/{access.ids['teacher']}"
    assert access.client.patch(path, json={"active": False}).json()["active"] is False
    access.sign_in("teacher")
    assert access.client.get(f"{access.root}/classes").status_code == 404
    access.sign_in("admin")
    assert access.client.patch(path, json={"active": True}).json()["active"] is True
    access.sign_in("teacher")
    assert access.client.get(f"{access.root}/classes").status_code == 200


def test_enrollment_is_idempotent_and_controls_student_timetable(access):
    path = f"{access.root}/classes/{access.ids['classroom']}/enrollments"
    access.sign_in("student")
    assert access.client.get(f"{access.root}/classes").json()["items"] == []
    access.sign_in("teacher")
    for _ in range(2):
        response = access.client.post(path, json={"user_id": str(access.ids['student'])})
        assert response.status_code == 200 and response.json()["role"] == "student"
    assert len(access.client.get(path).json()["items"]) == 1
    access.sign_in("student")
    assert [item["id"] for item in access.client.get(f"{access.root}/classes").json()["items"]] == [str(access.ids["classroom"])]
    assert access.client.get(path).status_code == 403
    assert access.client.delete(f"{path}/{access.ids['student']}").status_code == 403
    access.sign_in("teacher")
    for _ in range(2):
        assert access.client.delete(f"{path}/{access.ids['student']}").status_code == 204
    access.sign_in("student")
    assert access.client.get(f"{access.root}/classes").json()["items"] == []


def test_enrollment_rejects_foreign_inactive_and_nonstudent_members(access):
    path = f"{access.root}/classes/{access.ids['classroom']}/enrollments"
    for member in ("teacher", "admin", "inactive", "outsider"):
        assert access.client.post(path, json={"user_id": str(access.ids[member])}).status_code == 404
    assert access.client.post(path, json={"user_id": str(access.ids['student']), "institution_id": str(access.ids['foreign_tenant'])}).status_code == 422


def test_teacher_cannot_manage_other_teachers_or_other_tenants_class(access):
    access.sign_in("teacher")
    for classroom in ("other_classroom", "foreign_classroom"):
        path = f"{access.root}/classes/{access.ids[classroom]}/enrollments"
        assert access.client.get(path).status_code == 404
        assert access.client.post(path, json={"user_id": str(access.ids['student'])}).status_code == 404
        assert access.client.delete(f"{path}/{access.ids['student']}").status_code == 404


def test_role_changes_remove_old_enrollments_before_returning_to_student(access):
    path = f"{access.root}/classes/{access.ids['classroom']}/enrollments"
    assert access.client.post(path, json={"user_id": str(access.ids['student'])}).status_code == 200
    member_path = f"{access.root}/members/{access.ids['student']}"
    assert access.client.patch(member_path, json={"role": "teacher"}).json()["role"] == "teacher"
    assert access.client.get(path).json()["items"] == []
    assert access.client.patch(member_path, json={"role": "student"}).json()["role"] == "student"
    access.sign_in("student")
    assert access.client.get(f"{access.root}/classes").json()["items"] == []


def test_concurrent_invite_acceptance_creates_exactly_one_membership(access):
    invitation = invite(access)
    access.sign_in("newcomer")
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(lambda _: accept(access, invitation["token"]).status_code, range(4)))
    assert statuses.count(200) == 1
    assert all(status in {200, 409, 410} for status in statuses)
    with Session(access.engine) as database:
        assert database.scalar(select(func.count()).select_from(Membership).where(
            Membership.institution_id == access.ids["tenant"], Membership.user_id == access.ids["newcomer"],
        )) == 1


def test_accepted_invitation_cannot_be_reported_as_revoked(access):
    invitation = invite(access)
    access.sign_in("newcomer")
    # Concurrent acceptance is exercised above. A successfully accepted invite
    # cannot later masquerade as revoked while retaining access.
    assert accept(access, invitation["token"]).status_code == 200
    access.sign_in("admin")
    assert access.client.post(f"{access.root}/invitations/{invitation['id']}/revoke").status_code == 409
    assert access.client.get(f"{access.root}/invitations").json()["items"][0]["status"] == "accepted"


def test_acceptance_winning_a_revocation_race_returns_conflict(access):
    invitation = invite(access)
    revocation_ready, acceptance_finished = Event(), Event()

    def pause_revocation(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.startswith("UPDATE invitations SET revoked_at="):
            revocation_ready.set()
            assert acceptance_finished.wait(timeout=10)

    event.listen(access.engine, "before_cursor_execute", pause_revocation)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(access.client.post, f"{access.root}/invitations/{invitation['id']}/revoke")
            assert revocation_ready.wait(timeout=10)
            access.sign_in("newcomer")
            try:
                assert accept(access, invitation["token"]).status_code == 200
            finally:
                acceptance_finished.set()
            assert pending.result(timeout=10).status_code == 409
    finally:
        acceptance_finished.set()
        event.remove(access.engine, "before_cursor_execute", pause_revocation)
