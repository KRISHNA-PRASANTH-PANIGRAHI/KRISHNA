from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from classguard.auth import Principal, get_principal
from classguard.config import Settings, get_settings
from classguard.database import Base, get_database, make_engine
from classguard.main import app
from classguard.models import Classroom, Enrollment, Institution, Membership


@pytest.fixture
def workspace(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    tenant_a, tenant_b = uuid4(), uuid4()
    teacher, other_teacher, student = uuid4(), uuid4(), uuid4()
    with Session(engine) as database:
        database.add_all([Institution(id=tenant_a, name="A"), Institution(id=tenant_b, name="B")])
        database.flush()
        database.add_all([
            Membership(institution_id=tenant_a, user_id=teacher, role="teacher"),
            Membership(institution_id=tenant_a, user_id=other_teacher, role="teacher"),
            Membership(institution_id=tenant_a, user_id=student, role="student"),
        ])
        database.flush()
        first = Classroom(
            institution_id=tenant_a, title="Algebra", subject="Maths", created_by=teacher,
            starts_at=datetime(2026, 11, 3, 10, tzinfo=UTC), duration_minutes=60,
        )
        second = Classroom(
            institution_id=tenant_a, title="Mechanics", subject="Physics", created_by=other_teacher,
            starts_at=datetime(2026, 11, 3, 11, tzinfo=UTC), duration_minutes=60,
        )
        database.add_all([first, second])
        database.flush()
        database.add(Enrollment(classroom_id=first.id, institution_id=tenant_a, user_id=student))
        database.commit()

    def test_database():
        with Session(engine) as database:
            yield database

    app.dependency_overrides[get_database] = test_database
    app.dependency_overrides[get_principal] = lambda: Principal(teacher, "teacher@example.test")
    with TestClient(app) as client:
        yield client, engine, tenant_a, tenant_b, teacher, student
    app.dependency_overrides.clear()
    engine.dispose()


def class_payload():
    return {
        "title": "Chemistry lab", "subject": "Chemistry", "description": "Review bonds",
        "starts_at": "2026-11-04T10:00:00+05:30", "duration_minutes": 45,
    }


def test_teacher_can_only_list_their_classes(workspace):
    client, _, tenant_a, _, _, _ = workspace
    response = client.get(f"/v1/institutions/{tenant_a}/classes")
    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["Algebra"]


def test_cross_tenant_list_and_create_are_denied(workspace):
    client, _, _, tenant_b, _, _ = workspace
    path = f"/v1/institutions/{tenant_b}/classes"
    assert client.get(path).status_code == 404
    assert client.post(path, json=class_payload()).status_code == 404


def test_student_sees_enrolled_class_and_cannot_create(workspace):
    client, _, tenant_a, _, _, student = workspace
    app.dependency_overrides[get_principal] = lambda: Principal(student, "student@example.test")
    path = f"/v1/institutions/{tenant_a}/classes"
    assert [item["title"] for item in client.get(path).json()["items"]] == ["Algebra"]
    assert client.post(path, json=class_payload()).status_code == 403


def test_membership_revocation_takes_effect_on_next_request(workspace):
    client, engine, tenant_a, _, teacher, _ = workspace
    with Session(engine) as database:
        membership = database.get(Membership, (tenant_a, teacher))
        membership.active = False
        database.commit()
    assert client.get(f"/v1/institutions/{tenant_a}/classes").status_code == 404
    assert client.get("/v1/me").json()["memberships"] == []


def test_create_uses_server_identity_and_normalizes_timestamp(workspace):
    client, _, tenant_a, _, teacher, _ = workspace
    path = f"/v1/institutions/{tenant_a}/classes"
    response = client.post(path, json=class_payload())
    assert response.status_code == 201
    assert response.json()["created_by"] == str(teacher)
    assert response.json()["starts_at"] == "2026-11-04T04:30:00Z"
    assert len(client.get(path).json()["items"]) == 2
    payload = {**class_payload(), "created_by": str(uuid4())}
    assert client.post(path, json=payload).status_code == 422


def test_naive_schedule_and_blank_titles_are_rejected(workspace):
    client, _, tenant_a, _, _, _ = workspace
    payload = {**class_payload(), "starts_at": "2026-11-04T10:00:00", "title": "   "}
    assert client.post(f"/v1/institutions/{tenant_a}/classes", json=payload).status_code == 422


def test_unconfigured_authentication_fails_closed():
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_url="", _env_file=None)
    try:
        with TestClient(app) as client:
            assert client.get("/v1/me").status_code == 503
            assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()
