"""Conservative identity comparison without Unicode mailbox collisions."""

_ASCII_LOWERCASE = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def normalize_email_address(value: str) -> str:
    """Keep ASCII case-insensitivity without merging distinct Unicode addresses.

    Unicode casefold/lower can turn non-ASCII mailbox characters into ASCII
    (for example sharp-s into ``ss`` or Kelvin sign into ``k``). An invitation
    must not treat those distinct identities as interchangeable. Provider
    verification supplies the account email; this helper is not validation.
    """
    return value.strip().translate(_ASCII_LOWERCASE)
