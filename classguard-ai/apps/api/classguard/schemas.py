"""Public API schemas shared with the web application."""

from datetime import UTC, datetime
import re
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from .email_addresses import normalize_email_address


class MembershipResponse(BaseModel):
    institution_id: UUID
    institution_name: str
    role: Literal["admin", "teacher", "student"]


class MeResponse(BaseModel):
    id: UUID
    email: str | None
    memberships: list[MembershipResponse]


class ClassCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    subject: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    starts_at: AwareDatetime
    duration_minutes: int = Field(ge=5, le=480, strict=True)

    @field_validator("starts_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    title: str
    subject: str
    description: str
    starts_at: datetime
    duration_minutes: int
    created_by: UUID
    created_at: datetime


class ClassesResponse(BaseModel):
    items: list[ClassResponse]


class InstitutionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)


class MemberResponse(BaseModel):
    user_id: UUID
    email: str | None
    role: Literal["admin", "teacher", "student"]
    active: bool


class MembersResponse(BaseModel):
    items: list[MemberResponse]


class MemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["teacher", "student"] | None = None
    active: bool | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set or any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Supply a role or active state; null values are not accepted")
        return self


class InvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=254)
    role: Literal["teacher", "student"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        # Conventional email addresses, without introducing an email-delivery dependency.
        if not re.fullmatch(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+", value):
            raise ValueError("Enter a valid email address")
        return normalize_email_address(value)


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    role: Literal["teacher", "student"]
    created_at: datetime
    expires_at: datetime
    status: Literal["pending", "accepted", "revoked", "expired"]


class InvitationCreated(InvitationResponse):
    token: str


class InvitationsResponse(BaseModel):
    items: list[InvitationResponse]


class InvitationAccept(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    token: str = Field(min_length=32, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class EnrollmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
