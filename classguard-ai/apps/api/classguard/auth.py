"""Verify identity cryptographically, then resolve permissions from the database."""

from dataclasses import dataclass
from functools import lru_cache
from time import monotonic
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientConnectionError, PyJWKClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .models import Institution, Membership
from .provider_identity import confirmed_current_email
from .security import limit_account

bearer_scheme = HTTPBearer(auto_error=False)
MAX_ACCESS_TOKEN_LENGTH = 16_384
JWKS_FAILURE_BACKOFF_SECONDS = 5


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str | None


class BackoffJWKClient(PyJWKClient):
    """Bound retries during provider outages without accepting stale credentials."""

    def __init__(self, uri: str):
        super().__init__(uri, lifespan=300, timeout=5, cooldown_duration=30)
        self._retry_after = 0.0

    def fetch_data(self):
        # The library's lock is reentrant and also protects normal key lookup.
        # The stock unknown-key cooldown only applies after successful fetches.
        with self._client_lock:
            if monotonic() < self._retry_after:
                raise PyJWKClientConnectionError("Identity provider retry is cooling down")
            try:
                result = super().fetch_data()
            except PyJWKClientConnectionError:
                self._retry_after = monotonic() + JWKS_FAILURE_BACKOFF_SECONDS
                raise
            self._retry_after = 0.0
            return result


@lru_cache(maxsize=4)
def jwks_client(issuer: str) -> PyJWKClient:
    return BackoffJWKClient(f"{issuer}/.well-known/jwks.json")


def verify_access_token(token: str, settings: Settings) -> Principal:
    try:
        # These untrusted values only reject invalid input. They never establish
        # identity or select a caller-supplied key endpoint.
        if len(token) > MAX_ACCESS_TOKEN_LENGTH:
            raise ValueError("Access token is too large")
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in {"ES256", "RS256"}:
            raise ValueError("Unsupported signing algorithm")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid or len(kid) > 256:
            raise ValueError("Invalid signing key identifier")
        if header.get("crit") not in (None, []) or header.get("b64", True) is not True:
            raise ValueError("Unsupported critical token extension")
        signing_key = jwks_client(settings.jwt_issuer).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            leeway=10,
        )
        user_id = UUID(claims["sub"])
        if claims.get("role") != "authenticated" or claims.get("is_anonymous", False):
            raise ValueError("Institution account required")
        email = claims.get("email")
        if email is not None and not isinstance(email, str):
            raise ValueError("Invalid email claim")
        return Principal(user_id=user_id, email=email)
    except PyJWKClientConnectionError as error:
        raise HTTPException(status_code=503, detail="Identity provider is temporarily unavailable") from error
    except (InvalidTokenError, PyJWKClientError, ValueError, KeyError, TypeError, OverflowError) as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def get_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if not settings.authentication_configured:
        raise HTTPException(status_code=503, detail="Supabase authentication has not been configured")
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Sign in to continue",
            headers={"WWW-Authenticate": "Bearer"},
        )
    principal = verify_access_token(credentials.credentials, settings)
    limit_account(request, principal.user_id)
    email = confirmed_current_email(credentials.credentials, principal.user_id, settings)
    return Principal(user_id=principal.user_id, email=email)


def require_membership(database: Session, institution_id: UUID, principal: Principal) -> Membership:
    membership = database.scalar(
        select(Membership)
        .join(Institution, Institution.id == Membership.institution_id)
        .where(
            Membership.institution_id == institution_id,
            Membership.user_id == principal.user_id,
            Membership.active.is_(True),
            Institution.active.is_(True),
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    return membership
