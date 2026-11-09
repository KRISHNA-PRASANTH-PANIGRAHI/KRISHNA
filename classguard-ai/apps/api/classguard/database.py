"""Shared database setup for SQLite development and PostgreSQL deployment."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session

from .config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str, database_schema: str = "") -> Engine:
    backend = make_url(database_url).get_backend_name()
    options = {"check_same_thread": False} if backend == "sqlite" else {}
    pool_options = {"pool_size": 3, "max_overflow": 2} if backend == "postgresql" else {}
    engine = create_engine(database_url, connect_args=options, pool_pre_ping=True, **pool_options)
    if backend == "postgresql" and database_schema:
        # Qualify all ORM tables, including foreign keys and joins, without
        # depending on a pooled connection's search_path or changing SQLite.
        engine = engine.execution_options(schema_translate_map={None: database_schema})
    if backend == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _connection_record):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return make_engine(settings.database_url, settings.database_schema)


def get_database() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
