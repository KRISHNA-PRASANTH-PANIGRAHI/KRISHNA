"""Initial tenant, membership, classroom and enrollment records."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from .database import Base


class UTCDateTime(TypeDecorator):
    """Retain explicit UTC timestamps when SQLite discards timezone information."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone")
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (CheckConstraint("role IN ('admin', 'teacher', 'student')", name="membership_role"),)

    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Classroom(Base):
    __tablename__ = "classrooms"
    __table_args__ = (
        UniqueConstraint("id", "institution_id"),
        ForeignKeyConstraint(
            ["institution_id", "created_by"],
            ["memberships.institution_id", "memberships.user_id"],
        ),
        CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 480", name="class_duration"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    subject: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(2000), default="")
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime())
    duration_minutes: Mapped[int]
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["classroom_id", "institution_id"],
            ["classrooms.id", "classrooms.institution_id"],
        ),
        ForeignKeyConstraint(
            ["institution_id", "user_id"],
            ["memberships.institution_id", "memberships.user_id"],
        ),
    )

    classroom_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    institution_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)


class AccountIdentity(Base):
    """Directory information learned only from the verified identity provider."""

    __tablename__ = "account_identities"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint("role IN ('teacher', 'student')", name="invitation_role"),
        ForeignKeyConstraint(
            ["institution_id", "created_by"],
            ["memberships.institution_id", "memberships.user_id"],
        ),
        Index(
            "one_outstanding_invitation_per_email", "institution_id", "email", unique=True,
            sqlite_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
            postgresql_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), index=True)
    email: Mapped[str] = mapped_column(String(254))
    role: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
