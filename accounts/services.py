"""Application service layer shared by API and Django Template views."""

import math
import re
import secrets
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.authtoken.models import Token

from .models import PhoneChallenge

PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
INVITE_RE = re.compile(r"^[A-Z0-9]{6}$")


class DomainError(Exception):
    """A user-facing business rule violation."""


class CooldownError(DomainError):
    def __init__(self, retry_after):
        self.retry_after = max(1, math.ceil(retry_after))
        super().__init__(f"Повторный код можно запросить через {self.retry_after} сек.")


class InvalidCodeError(DomainError):
    pass


class ExpiredCodeError(DomainError):
    pass


class AttemptsExceededError(DomainError):
    pass


class InvalidReferralError(DomainError):
    pass


def normalize_phone(value):
    """Require an international number in +XXXXXXXX format (E.164-like)."""
    value = value.strip() if isinstance(value, str) else ""
    if not PHONE_RE.fullmatch(value):
        raise ValueError("Введите телефон в международном формате, например +79991234567")
    return value


def code_digest(phone, code):
    # A keyed digest resists offline brute force if only the DB is leaked.
    return salted_hmac("tb4.phone.otp", f"{phone}:{code}").hexdigest()


def send_simulated_sms(phone, code):
    """Development ONLY. Demo OTP is printed to server logs, not HTTP responses."""
    if not settings.DEBUG:
        raise RuntimeError("Demo SMS backend requires DEBUG=1; configure a real provider for production")
    time.sleep(settings.SMS_SIMULATED_DELAY_SECONDS)
    print(f"[DEMO SMS / НЕ ДЛЯ PRODUCTION] Номер: {phone}; код: {code}", flush=True)


def request_phone_code(phone):
    """Upsert a challenge, enforce resend cooldown, simulate SMS outside the lock."""
    phone = normalize_phone(phone)
    now = timezone.now()
    code = f"{secrets.randbelow(10000):04d}"
    with transaction.atomic():
        # A unique constraint on phone ensures one row even for simultaneous requests.
        PhoneChallenge.objects.get_or_create(
            phone_number=phone,
            defaults={
                "code_digest": code_digest(phone, code),
                "expires_at": now,
                "last_sent_at": now - timedelta(days=1),
            },
        )
        challenge = PhoneChallenge.objects.select_for_update().get(phone_number=phone)
        retry_after = (
            challenge.last_sent_at + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS) - now
        ).total_seconds()
        if retry_after > 0:
            raise CooldownError(retry_after)
        challenge.code_digest = code_digest(phone, code)
        challenge.expires_at = now + timedelta(seconds=settings.OTP_TTL_SECONDS)
        challenge.last_sent_at = now
        challenge.attempts = 0
        challenge.consumed_at = None
        challenge.save(
            update_fields=[
                "code_digest",
                "expires_at",
                "last_sent_at",
                "attempts",
                "consumed_at",
            ]
        )
    send_simulated_sms(phone, code)
    return settings.OTP_TTL_SECONDS


def verify_phone_code(phone, code):
    """Verify OTP once, then create/load user and return a DRF auth token."""
    phone = normalize_phone(phone)
    if not isinstance(code, str) or not re.fullmatch(r"\d{4}", code):
        raise InvalidCodeError("Код должен состоять из четырёх цифр")
    outcome = None
    with transaction.atomic():
        challenge = PhoneChallenge.objects.select_for_update().filter(phone_number=phone).first()
        if challenge is None or challenge.consumed_at is not None:
            raise InvalidCodeError("Неверный или уже использованный код")
        if challenge.expires_at <= timezone.now():
            raise ExpiredCodeError("Срок действия кода истёк")
        if challenge.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise AttemptsExceededError("Лимит попыток исчерпан. Запросите новый код")
        valid = constant_time_compare(challenge.code_digest, code_digest(phone, code))
        if not valid:
            challenge.attempts += 1
            challenge.save(update_fields=["attempts"])
            outcome = (
                AttemptsExceededError("Лимит попыток исчерпан. Запросите новый код")
                if challenge.attempts >= settings.OTP_MAX_ATTEMPTS
                else InvalidCodeError("Неверный код")
            )
        else:
            user_model = get_user_model()
            user = user_model.objects.filter(phone_number=phone).first()
            created = user is None
            if created:
                try:
                    user = user_model.objects.create_user(phone_number=phone)
                except IntegrityError:
                    # A concurrent verification may have already created this user.
                    user = user_model.objects.get(phone_number=phone)
                    created = False
            token, _ = Token.objects.get_or_create(user=user)
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=["consumed_at"])
    if outcome is not None:
        raise outcome
    return user, token.key, created


def activate_invite_code(user, code):
    code = code.strip().upper() if isinstance(code, str) else ""
    if not INVITE_RE.fullmatch(code):
        raise InvalidReferralError("Инвайт-код должен содержать 6 букв/цифр")
    model = get_user_model()
    with transaction.atomic():
        current = model.objects.select_for_update().get(pk=user.pk)
        if current.invited_by_id is not None:
            raise InvalidReferralError("Инвайт-код уже активирован")
        inviter = model.objects.filter(invite_code=code).first()
        if inviter is None:
            raise InvalidReferralError("Инвайт-код не найден")
        if inviter.pk == current.pk:
            raise InvalidReferralError("Нельзя активировать собственный код")
        # Do not allow referral cycles, even with multiple invitations.
        ancestor = inviter
        seen = set()
        while ancestor is not None and ancestor.pk not in seen:
            if ancestor.pk == current.pk:
                raise InvalidReferralError("Нельзя создать циклическую цепочку приглашений")
            seen.add(ancestor.pk)
            ancestor = ancestor.invited_by
        current.invited_by = inviter
        current.save(update_fields=["invited_by"])
    user.invited_by = inviter
    return inviter
