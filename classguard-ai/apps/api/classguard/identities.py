"""The directory is descriptive; all access decisions use memberships."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import Principal
from .email_addresses import normalize_email_address
from .models import AccountIdentity


def sync_identity(database: Session, principal: Principal) -> None:
    email = normalize_email_address(principal.email) if principal.email else None
    identity = database.get(AccountIdentity, principal.user_id)
    if identity is None:
        # A second tab may request /me simultaneously. The savepoint keeps a
        # duplicate directory insertion from rolling back surrounding writes.
        try:
            with database.begin_nested():
                identity = AccountIdentity(user_id=principal.user_id, email=email)
                database.add(identity)
                database.flush()
        except IntegrityError:
            identity = database.get(AccountIdentity, principal.user_id)
    if identity is not None:
        identity.email = email
