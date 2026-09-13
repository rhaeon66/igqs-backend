import hashlib
import logging
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import GuardianSession, PhoneOtp

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^01[3-9]\d{8}$")
OTP_TTL_SECONDS = 300
OTP_RESEND_SECONDS = 60
OTP_MAX_PER_HOUR = 5
OTP_MAX_ATTEMPTS = 5
SESSION_TTL_DAYS = 30


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


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def deliver_otp(phone: str, code: str) -> bool:
    provider = (getattr(settings, "SMS_PROVIDER", "") or "").strip()
    if not provider:
        logger.info("Admission OTP for %s: %s", phone, code)
        return False
    logger.info("Admission OTP for %s would be sent via %s", phone, provider)
    return True


def send_otp(phone_raw: str) -> dict:
    phone = normalize_bd_phone(phone_raw)
    now = timezone.now()
    recent = PhoneOtp.objects.filter(phone=phone, created_at__gte=now - timedelta(hours=1))
    if recent.count() >= OTP_MAX_PER_HOUR:
        raise PhoneError("rate_limited", "Too many OTP requests. Please try again later.", 429)

    latest = PhoneOtp.objects.filter(phone=phone).order_by("-created_at").first()
    if latest and latest.last_sent_at and (now - latest.last_sent_at).total_seconds() < OTP_RESEND_SECONDS:
        wait = OTP_RESEND_SECONDS - int((now - latest.last_sent_at).total_seconds())
        raise PhoneError(
            "resend_wait",
            f"Please wait {max(wait, 1)} seconds before requesting another OTP.",
            429,
        )

    PhoneOtp.objects.filter(phone=phone, consumed_at__isnull=True).update(consumed_at=now)
    code = f"{secrets.randbelow(1_000_000):06d}"
    otp = PhoneOtp.objects.create(
        phone=phone,
        code_hash=make_password(code),
        expires_at=now + timedelta(seconds=OTP_TTL_SECONDS),
        last_sent_at=now,
    )
    delivered = deliver_otp(phone, code)
    payload = {
        "ok": True,
        "phone": phone,
        "expires_in": OTP_TTL_SECONDS,
        "resend_in": OTP_RESEND_SECONDS,
        "sms_sent": delivered,
    }
    if settings.DEBUG and not delivered:
        payload["debug_otp"] = code
        payload["otp_id"] = otp.pk
    return payload


def verify_otp(phone_raw: str, code_raw: str) -> dict:
    phone = normalize_bd_phone(phone_raw)
    code = (code_raw or "").strip()
    if not re.fullmatch(r"\d{6}", code):
        raise PhoneError("invalid_otp", "Enter the 6-digit OTP.")

    otp = (
        PhoneOtp.objects.filter(phone=phone, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if not otp:
        raise PhoneError("otp_missing", "Request a new OTP first.")
    if otp.expires_at <= timezone.now():
        raise PhoneError("otp_expired", "This OTP has expired. Request a new one.")
    if otp.attempts >= OTP_MAX_ATTEMPTS:
        raise PhoneError("otp_locked", "Too many incorrect attempts. Request a new OTP.")
    if not check_password(code, otp.code_hash):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise PhoneError("otp_incorrect", "The OTP is incorrect.")

    otp.consumed_at = timezone.now()
    otp.save(update_fields=["consumed_at"])

    raw_token = secrets.token_urlsafe(32)
    GuardianSession.objects.filter(phone=phone, expires_at__gt=timezone.now()).update(
        expires_at=timezone.now()
    )
    session = GuardianSession.objects.create(
        phone=phone,
        token_hash=hash_session_token(raw_token),
        expires_at=timezone.now() + timedelta(days=SESSION_TTL_DAYS),
    )
    return {
        "ok": True,
        "phone": session.phone,
        "token": raw_token,
        "expires_at": session.expires_at,
    }


def get_guardian_session(request):
    header = request.META.get("HTTP_AUTHORIZATION") or ""
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return (
        GuardianSession.objects.filter(
            token_hash=hash_session_token(token.strip()),
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )
