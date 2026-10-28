import pytest

from accounts.models import PhoneChallenge, User
from accounts.services import (
    AttemptsExceededError,
    InvalidCodeError,
    InvalidReferralError,
    activate_invite_code,
    normalize_phone,
    request_phone_code,
    verify_phone_code,
)

pytestmark = pytest.mark.django_db


def test_phone_normalization():
    assert normalize_phone("  +79991234567 ") == "+79991234567"
    with pytest.raises(ValueError):
        normalize_phone("8 (999) 123-45-67")


def test_direct_code_service_consumes_code():
    request_phone_code("+79991234567")
    user, token, created = verify_phone_code("+79991234567", "1234")
    assert created is True
    assert user.invite_code
    assert token
    with pytest.raises(InvalidCodeError):
        verify_phone_code("+79991234567", "1234")


def test_no_referral_reactivation():
    inviter = User.objects.create_user("+79990000001")
    invited = User.objects.create_user("+79990000002")
    activate_invite_code(invited, inviter.invite_code)
    with pytest.raises(InvalidReferralError):
        activate_invite_code(invited, inviter.invite_code)


def test_wrong_codes_really_consume_attempts():
    request_phone_code("+79991234567")
    for _ in range(4):
        with pytest.raises(InvalidCodeError):
            verify_phone_code("+79991234567", "4321")
    with pytest.raises(AttemptsExceededError):
        verify_phone_code("+79991234567", "4321")
    assert PhoneChallenge.objects.get(phone_number="+79991234567").attempts == 5
