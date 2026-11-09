import base64
from datetime import UTC, datetime, timedelta
import json
from io import BytesIO
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from classguard import auth, provider_identity
from classguard.config import Settings, get_settings
from classguard.database import Base, make_engine, get_database
from classguard.main import app


@pytest.fixture
def identity(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(supabase_url="https://example.supabase.co", supabase_publishable_key="sb_publishable_test_only", _env_file=None)
    claims = {"sub": str(uuid4()), "iss": settings.jwt_issuer, "aud": "authenticated", "role": "authenticated",
              "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5), "email": "old@school.test"}
    monkeypatch.setattr(auth, "jwks_client", lambda issuer: SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())))
    user = {"id": claims["sub"], "email": "CURRENT@school.test", "email_confirmed_at": "2026-11-01T00:00:00Z", "is_anonymous": False}
    http_fetch = provider_identity.fetch_current_user
    monkeypatch.setattr(provider_identity, "fetch_current_user", lambda token, settings: user)
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})
    return SimpleNamespace(key=key, settings=settings, claims=claims, token=token, user=user, http_fetch=http_fetch)


def get_principal(identity):
    request = Request({"type": "http", "method": "GET", "path": "/v1/me", "headers": [], "scheme": "http", "server": ("testserver", 80), "query_string": b""})
    return auth.get_principal(request, HTTPAuthorizationCredentials(scheme="Bearer", credentials=identity.token), identity.settings)


def test_current_verified_email_replaces_stale_jwt_email(identity):
    principal = get_principal(identity)
    assert principal.email == "current@school.test"
    assert str(principal.user_id) == identity.claims["sub"]


@pytest.mark.parametrize("changes,status", [
    ({"email_confirmed_at": None}, 403), ({"email_confirmed_at": ""}, 403),
    ({"email_confirmed_at": "not-a-date"}, 503), ({"email": None}, 403),
    ({"is_anonymous": True}, 403), ({"id": str(uuid4())}, 401), ({"id": []}, 401),
])
def test_unconfirmed_anonymous_or_mismatched_provider_identity_denied(identity, changes, status):
    identity.user.update(changes)
    with pytest.raises(HTTPException) as error:
        get_principal(identity)
    assert error.value.status_code == status


@pytest.mark.parametrize("status", [401, 503])
def test_provider_rejection_or_outage_never_falls_back_to_stale_jwt(identity, monkeypatch, status):
    def fail(*args):
        raise HTTPException(status, "simulated provider response")
    monkeypatch.setattr(provider_identity, "fetch_current_user", fail)
    with pytest.raises(HTTPException) as error:
        get_principal(identity)
    assert error.value.status_code == status


@pytest.mark.parametrize("header", [
    {"alg": "none", "kid": "x"}, {"alg": "HS256", "kid": "x"},
    {"alg": "RS256"}, {"alg": "RS256", "kid": []},
    {"alg": "RS256", "kid": "x", "crit": ["unrecognized"]},
    {"alg": "RS256", "kid": "x", "b64": False}, {"alg": [], "kid": "x"},
])
def test_rejected_headers_never_fetch_provider_keys(monkeypatch, header):
    def forbidden(*args):
        pytest.fail("Rejected input reached JWKS network boundary")
    monkeypatch.setattr(auth, "jwks_client", forbidden)
    encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(f"{encoded}.e30.AA", Settings(_env_file=None))
    assert error.value.status_code == 401


def test_oversized_token_is_rejected_before_provider_lookup(monkeypatch):
    monkeypatch.setattr(auth, "jwks_client", lambda *args: pytest.fail("Oversized token reached provider"))
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token("a" * 16_385, Settings(_env_file=None))
    assert error.value.status_code == 401


@pytest.mark.parametrize("field", ["exp", "iat"])
def test_nonfinite_time_claim_returns_401_instead_of_unhandled_500(identity, field):
    token = jwt.encode({**identity.claims, field: float("inf")}, identity.key, algorithm="RS256", headers={"kid": "test-key"})
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(token, identity.settings)
    assert error.value.status_code == 401


def test_jwks_outage_retries_are_bounded(monkeypatch):
    calls = []
    clock = [0.0]
    monkeypatch.setattr(auth, "monotonic", lambda: clock[0])
    def unavailable(self):
        calls.append(True)
        raise auth.PyJWKClientConnectionError("simulated outage")
    monkeypatch.setattr(auth.PyJWKClient, "fetch_data", unavailable)
    client = auth.BackoffJWKClient("https://example.supabase.co/auth/v1/.well-known/jwks.json")
    for _ in range(8):
        with pytest.raises(auth.PyJWKClientConnectionError):
            client.fetch_data()
    assert len(calls) == 1
    clock[0] = 6
    with pytest.raises(auth.PyJWKClientConnectionError):
        client.fetch_data()
    assert len(calls) == 2


@pytest.mark.parametrize("provider_status,expected", [(301, 503), (401, 401), (403, 401), (404, 401), (500, 503)])
def test_provider_http_failures_are_generic_and_redirects_not_followed(identity, monkeypatch, provider_status, expected):
    captured = []
    def opener(*handlers):
        assert isinstance(handlers[0], provider_identity.NoAuthRedirects)
        def fail(request, timeout):
            captured.append(request)
            assert timeout == 5
            raise HTTPError(request.full_url, provider_status, "private error", {}, None)
        return SimpleNamespace(open=fail)
    monkeypatch.setattr(provider_identity, "build_opener", opener)
    with pytest.raises(HTTPException) as error:
        identity.http_fetch(identity.token, identity.settings)
    assert error.value.status_code == expected
    assert identity.token not in error.value.detail
    assert captured[0].full_url == "https://example.supabase.co/auth/v1/user"
    assert provider_identity.NoAuthRedirects().redirect_request(None, None, 302, "", {}, "https://elsewhere.test") is None


def test_provider_request_uses_expected_origin_and_public_key(identity, monkeypatch):
    def open_response(request, timeout):
        assert request.full_url == "https://example.supabase.co/auth/v1/user"
        assert request.get_header("Authorization") == f"Bearer {identity.token}"
        assert request.get_header("Apikey") == "sb_publishable_test_only"
        return BytesIO(json.dumps(identity.user).encode())
    monkeypatch.setattr(provider_identity, "build_opener", lambda *args: SimpleNamespace(open=open_response))
    assert identity.http_fetch(identity.token, identity.settings)["email"] == "CURRENT@school.test"


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b" " * 65_537], ids=["malformed-json", "wrong-shape", "oversized"])
def test_invalid_or_oversized_provider_response_fails_closed(identity, monkeypatch, payload):
    monkeypatch.setattr(provider_identity, "build_opener", lambda *args: SimpleNamespace(open=lambda *args, **kwargs: BytesIO(payload)))
    with pytest.raises(HTTPException) as error:
        identity.http_fetch(identity.token, identity.settings)
    assert error.value.status_code == 503


def test_config_requires_public_key_and_rejects_credential_bearing_origins():
    assert not Settings(supabase_url="https://example.supabase.co", _env_file=None).authentication_configured
    for origin in ["http://example.test", "https://user:pass@example.test", "https://example.test/other", "https://example.test?x=1"]:
        with pytest.raises(ValidationError):
            Settings(supabase_url=origin, _env_file=None)
    with pytest.raises(ValidationError):
        Settings(supabase_publishable_key="sb_secret_wrong", _env_file=None)


def test_authenticated_http_creation_is_limited_per_account(identity, monkeypatch, tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'identity.db'}")
    Base.metadata.create_all(engine)
    def database():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_database] = database
    app.dependency_overrides[get_settings] = lambda: identity.settings
    try:
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {identity.token}"}
            results = [client.post("/v1/institutions", json={"name": "Disposable security test"}, headers={**headers, "X-Forwarded-For": f"192.0.2.{index}"}).status_code for index in range(8)]
        assert results == [201] * 5 + [429] * 3
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
