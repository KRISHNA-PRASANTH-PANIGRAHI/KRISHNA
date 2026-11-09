from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from classguard import database
from classguard.config import Settings
from classguard.models import Institution, Membership


@pytest.mark.parametrize("schema", ["classguard", "institution_2", "_private", "a" * 63, ""])
def test_database_schema_accepts_single_identifier_or_default(schema):
    assert Settings(database_schema=schema, _env_file=None).database_schema == schema


@pytest.mark.parametrize("schema", [
    "public.classguard", "classguard,public", "classguard;select 1", '"classguard"',
    "ClassGuard", "1classguard", "class-guard", "class guard", "a" * 64,
])
def test_database_schema_rejects_paths_and_sql_fragments(schema):
    with pytest.raises(ValidationError, match="DATABASE_SCHEMA"):
        Settings(database_schema=schema, _env_file=None)


def test_postgres_orm_queries_and_foreign_keys_target_configured_schema(monkeypatch):
    settings = Settings(
        database_url="postgresql+psycopg://classguard_test@127.0.0.1/classguard_test",
        database_schema="classguard",
        _env_file=None,
    )
    monkeypatch.setattr(database, "get_settings", lambda: settings)
    database.get_engine.cache_clear()
    engine = database.get_engine()
    try:
        options = engine.get_execution_options()
        query = select(Membership).join(Institution, Institution.id == Membership.institution_id)
        compiled = str(query.compile(
            dialect=engine.dialect,
            schema_translate_map=options.get("schema_translate_map"),
            render_schema_translate=True,
        ))
        assert "FROM classguard.memberships JOIN classguard.institutions" in compiled
        ddl = str(CreateTable(Membership.__table__).compile(
            dialect=engine.dialect,
            schema_translate_map=options.get("schema_translate_map"),
            render_schema_translate=True,
        ))
        assert "CREATE TABLE classguard.memberships" in ddl
        assert "REFERENCES classguard.institutions" in ddl
        assert Membership.__table__.schema is None
    finally:
        engine.dispose()
        database.get_engine.cache_clear()


def test_sqlite_remains_usable_and_enforces_foreign_keys_with_schema_setting(tmp_path):
    engine = database.make_engine(f"sqlite:///{tmp_path / 'local.db'}", "classguard")
    try:
        database.Base.metadata.create_all(engine)
        assert "institutions" in inspect(engine).get_table_names()
        with Session(engine) as session:
            institution = Institution(name="Local school")
            session.add(institution)
            session.commit()
            assert session.scalar(select(Institution.name)) == "Local school"
            session.add(Membership(institution_id=uuid4(), user_id=uuid4(), role="student"))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        engine.dispose()
