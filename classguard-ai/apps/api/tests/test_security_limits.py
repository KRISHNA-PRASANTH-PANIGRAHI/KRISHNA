import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from classguard.auth import Principal, get_principal
from classguard.main import app
from classguard.security import MAX_BODY_BYTES, RequestGuardMiddleware, RequestLimits, limit_account


def request(method="POST", path="/v1/institutions", peer="127.0.0.1"):
    return Request({"type": "http", "method": method, "path": path, "headers": [], "client": (peer, 1234), "scheme": "http", "server": ("testserver", 80), "query_string": b""})


def test_account_creation_limit_follows_identity_across_client_addresses():
    user = uuid4()
    for index in range(5):
        limit_account(request(peer=f"192.0.2.{index}"), user)
    with pytest.raises(HTTPException) as error:
        limit_account(request(peer="192.0.2.90"), user)
    assert error.value.status_code == 429
    assert 1 <= int(error.value.headers["Retry-After"]) <= 3600
    limit_account(request(), uuid4())


def test_write_limit_and_read_limit_have_distinct_budgets():
    user = uuid4()
    for _ in range(30):
        limit_account(request(path="/v1/invitations/accept"), user)
    with pytest.raises(HTTPException) as error:
        limit_account(request(path="/v1/invitations/accept"), user)
    assert error.value.status_code == 429
    limit_account(request(method="GET", path="/v1/me"), user)


def test_rate_store_expires_windows_and_never_grows_beyond_bound():
    limits = RequestLimits(max_keys=2)
    assert limits.consume([("one", 2, 60)], now=0) == 0
    assert limits.consume([("one", 2, 60)], now=1) == 0
    assert limits.consume([("one", 2, 60)], now=2) == 58
    assert limits.consume([("two", 2, 60)], now=2) == 0
    assert limits.consume([("three", 2, 60)], now=3) > 0
    assert limits.consume([("three", 2, 60)], now=63) == 0


def test_oversized_valid_json_rejected_before_authentication():
    invoked = []
    def principal():
        invoked.append(True)
        return Principal(uuid4(), "fixture@school.test")
    app.dependency_overrides[get_principal] = principal
    try:
        with TestClient(app) as client:
            response = client.post("/v1/institutions", content=b'{"name":"test"}' + b" " * MAX_BODY_BYTES, headers={"Content-Type": "application/json"})
        assert response.status_code == 413
        assert invoked == []
    finally:
        app.dependency_overrides.clear()


def test_chunked_body_and_false_content_length_cannot_bypass_byte_limit():
    async def probe(length):
        entered, responses = [], []
        async def downstream(scope, receive, send):
            entered.append(True)
        messages = iter([
            {"type": "http.request", "body": b"a" * (MAX_BODY_BYTES // 2), "more_body": True},
            {"type": "http.request", "body": b"b" * (MAX_BODY_BYTES // 2 + 1), "more_body": False},
        ])
        async def receive():
            return next(messages)
        async def send(message):
            responses.append(message)
        scope = dict(request().scope)
        scope["headers"] = [] if length is None else [(b"content-length", length)]
        await RequestGuardMiddleware(downstream, RequestLimits())(scope, receive, send)
        assert not entered
        assert responses[0]["status"] == 413
    asyncio.run(probe(None))
    asyncio.run(probe(b"1"))


def test_peer_limiter_ignores_spoofed_forwarding_header():
    with TestClient(app) as client:
        for index in range(240):
            assert client.get("/v1/capabilities", headers={"X-Forwarded-For": f"192.0.2.{index}"}).status_code == 200
        response = client.get("/v1/capabilities", headers={"X-Forwarded-For": "198.51.100.1", "Origin": "http://localhost:3000"})
        assert response.status_code == 429
        assert response.headers["Retry-After"]
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert client.get("/health").status_code == 200


def test_validation_does_not_echo_invitation_secret():
    app.dependency_overrides[get_principal] = lambda: Principal(uuid4(), "fixture@school.test")
    try:
        with TestClient(app) as client:
            response = client.post("/v1/invitations/accept", json={"token": "PRIVATE-INVALID-SECRET!"})
        assert response.status_code == 422
        assert "PRIVATE-INVALID-SECRET" not in response.text
        assert "input" not in response.text
    finally:
        app.dependency_overrides.clear()
