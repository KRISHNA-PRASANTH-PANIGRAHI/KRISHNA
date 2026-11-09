"""Bound local request work. Deploy a shared edge limiter before public use."""

import asyncio
from math import ceil
from threading import Lock
from time import monotonic
from uuid import UUID

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 64 * 1024
MAX_HEADER_BYTES = 32 * 1024
BODY_TIMEOUT_SECONDS = 10
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RequestLimits:
    """Thread-safe, bounded fixed windows; keys never contain bearer tokens."""

    def __init__(self, max_keys: int = 4096):
        self.max_keys = max_keys
        self._windows: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def consume(self, policies: list[tuple[str, int, int]], *, now: float | None = None) -> int:
        current = monotonic() if now is None else now
        with self._lock:
            self._windows = {key: value for key, value in self._windows.items() if value[0] > current}
            new_keys = {key for key, _, _ in policies if key not in self._windows}
            if len(self._windows) + len(new_keys) > self.max_keys:
                return 60
            for key, limit, _ in policies:
                expires, count = self._windows.get(key, (0.0, 0))
                if count >= limit:
                    return max(1, ceil(expires - current))
            for key, _, seconds in policies:
                expires, count = self._windows.get(key, (current + seconds, 0))
                self._windows[key] = (expires, count + 1)
        return 0

    def reset(self) -> None:
        """Used by isolated tests; never exposed as an HTTP operation."""
        with self._lock:
            self._windows.clear()


request_limits = RequestLimits()


def limit_account(request: Request, user_id: UUID) -> None:
    account = str(user_id)
    policies = [(f"account:{account}", 120, 60)]
    if request.method in WRITE_METHODS:
        policies.append((f"account-write:{account}", 30, 60))
    if request.method == "POST" and request.url.path.rstrip("/") == "/v1/institutions":
        policies.append((f"institution-create:{account}", 5, 3600))
    retry = request_limits.consume(policies)
    if retry:
        raise HTTPException(429, "Too many requests. Please try again later.", headers={"Retry-After": str(retry)})


class RequestGuardMiddleware:
    """Limit bytes before JSON parsing, including chunked bodies and false sizes."""

    def __init__(self, app, limiter: RequestLimits = request_limits):
        self.app = app
        self.limiter = limiter

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/v1/"):
            return await self.app(scope, receive, send)

        async def reject(status: int, message: str, headers=None):
            await JSONResponse({"detail": message}, status_code=status, headers=headers)(scope, receive, send)

        if sum(len(name) + len(value) for name, value in scope["headers"]) > MAX_HEADER_BYTES:
            return await reject(431, "Request headers are too large")
        headers = dict(scope["headers"])
        try:
            sizes = [int(value) for name, value in scope["headers"] if name == b"content-length"]
            if any(size < 0 for size in sizes) or len(set(sizes)) > 1:
                raise ValueError
        except ValueError:
            return await reject(400, "Invalid content length")
        if sizes and sizes[0] > MAX_BODY_BYTES:
            return await reject(413, "Request body is too large")
        if headers.get(b"content-encoding", b"identity").lower() != b"identity":
            return await reject(415, "Compressed request bodies are not supported")
        if scope["method"] != "OPTIONS":
            # Forwarding headers are deliberately not parsed here. The trusted
            # reverse proxy/server must configure the actual ASGI client address.
            peer = (scope.get("client") or ("unknown", 0))[0]
            retry = self.limiter.consume([(f"peer:{peer}", 240, 60)])
            if retry:
                return await reject(429, "Too many requests. Please try again later.", {"Retry-After": str(retry)})

        chunks: list[bytes] = []
        total = 0
        deadline = monotonic() + BODY_TIMEOUT_SECONDS
        while True:
            if monotonic() >= deadline:
                return await reject(408, "Request body timed out")
            try:
                message = await asyncio.wait_for(receive(), timeout=max(0.001, deadline - monotonic()))
            except TimeoutError:
                return await reject(408, "Request body timed out")
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > MAX_BODY_BYTES:
                return await reject(413, "Request body is too large")
            if chunk:
                chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        delivered = False

        async def limited_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, limited_receive, send)
