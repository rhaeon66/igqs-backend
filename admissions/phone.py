import re

from django.core.cache import cache

PHONE_RE = re.compile(r"^01[3-9]\d{8}$")

# "My payments" is unlocked by mobile + the student's date of birth. A
# school-age DOB has only a few thousand plausible values, so failed guesses
# are counted per phone number (not just per IP) and the number is locked
# for a while once the limit is hit.
LOOKUP_MAX_FAILURES = 5
LOOKUP_LOCK_SECONDS = 60 * 60


class PhoneError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def normalize_bd_phone(value: str) -> str:
    raw = (value or "").strip().replace(" ", "").replace("-", "")
    if raw.startswith("+880"):
        raw = "0" + raw[4:]
    elif raw.startswith("880"):
        raw = "0" + raw[3:]
    if not PHONE_RE.fullmatch(raw):
        raise PhoneError("invalid_phone", "Enter a valid Bangladeshi mobile number (01XXXXXXXXX).")
    return raw


def _failure_key(phone: str) -> str:
    return f"admissions:payment-lookup-failures:{phone}"


def ensure_lookup_allowed(phone: str) -> None:
    if cache.get(_failure_key(phone), 0) >= LOOKUP_MAX_FAILURES:
        raise PhoneError(
            "lookup_locked",
            "Too many attempts for this mobile number. Please try again in an hour.",
            429,
        )


def record_lookup_failure(phone: str) -> None:
    key = _failure_key(phone)
    if cache.add(key, 1, LOOKUP_LOCK_SECONDS):
        return
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOOKUP_LOCK_SECONDS)


def clear_lookup_failures(phone: str) -> None:
    cache.delete(_failure_key(phone))
