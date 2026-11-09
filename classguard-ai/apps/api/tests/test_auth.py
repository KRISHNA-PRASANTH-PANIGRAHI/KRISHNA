from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from classguard import auth
from classguard.config import Settings


@pytest.fixture
def credentials(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private_key.public_key()))
    monkeypatch.setattr(auth, "jwks_client", lambda issuer: client)
    settings = Settings(supabase_url="https://example.supabase.co", _env_file=None)
    claims = {
        "sub": str(uuid4()), "iss": settings.jwt_issuer, "aud": "authenticated", "role": "authenticated",
        "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    return private_key, settings, claims


def test_valid_signed_identity(credentials):
    private_key, settings, claims = credentials
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})
    assert str(auth.verify_access_token(token, settings).user_id) == claims["sub"]


@pytest.mark.parametrize("overrides", [
    {"iss": "https://attacker.test"},
    {"aud": "wrong-audience"},
    {"exp": datetime.now(UTC) - timedelta(minutes=5)},
    {"sub": "invalid-uuid"},
    {"role": "service_role"},
    {"is_anonymous": True},
])
def test_invalid_identity_claims_are_rejected(credentials, overrides):
    private_key, settings, claims = credentials
    token = jwt.encode({**claims, **overrides}, private_key, algorithm="RS256", headers={"kid": "test-key"})
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(token, settings)
    assert error.value.status_code == 401


def test_untrusted_signature_is_rejected(credentials):
    _, settings, claims = credentials
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(claims, other_key, algorithm="RS256", headers={"kid": "test-key"})
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(token, settings)
    assert error.value.status_code == 401
