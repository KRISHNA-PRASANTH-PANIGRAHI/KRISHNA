"""Recheck current account details with Supabase after local JWT verification."""

from datetime import datetime
import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from fastapi import HTTPException

from .config import Settings
from .email_addresses import normalize_email_address


class NoAuthRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an account token to a redirect target.
        return None


def fetch_current_user(token: str, settings: Settings) -> dict:
    request = Request(
        f"{settings.jwt_issuer}/user",
        headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_publishable_key, "Accept": "application/json"},
    )
    try:
        with build_opener(NoAuthRedirects()).open(request, timeout=5) as response:
            data = response.read(65_537)
        if len(data) > 65_536:
            raise ValueError("Identity response is too large")
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError("Invalid identity response")
        return result
    except HTTPError as error:
        if error.code in {401, 403, 404}:
            raise HTTPException(401, "Your session is no longer accepted. Please sign in again.", headers={"WWW-Authenticate": "Bearer"}) from error
        raise HTTPException(503, "Identity provider is temporarily unavailable") from error
    except (URLError, OSError, TimeoutError, ValueError) as error:
        raise HTTPException(503, "Identity provider is temporarily unavailable") from error


def confirmed_current_email(token: str, expected_user_id: UUID, settings: Settings) -> str:
    user = fetch_current_user(token, settings)
    try:
        if UUID(user["id"]) != expected_user_id:
            raise ValueError("Identity mismatch")
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        raise HTTPException(401, "Identity could not be verified") from error
    email = user.get("email")
    confirmed = user.get("email_confirmed_at")
    if user.get("is_anonymous", False) or not isinstance(email, str) or not email.strip() or not isinstance(confirmed, str) or not confirmed:
        raise HTTPException(403, "A confirmed email account is required")
    try:
        confirmed_at = datetime.fromisoformat(confirmed.replace("Z", "+00:00"))
        if confirmed_at.tzinfo is None:
            raise ValueError("Unqualified confirmation timestamp")
    except ValueError as error:
        raise HTTPException(503, "Identity provider returned an invalid account record") from error
    return normalize_email_address(email)
