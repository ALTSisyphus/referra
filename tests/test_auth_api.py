from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import PhoneChallenge, User
from accounts.services import code_digest

pytestmark = pytest.mark.django_db


def test_request_code_returns_202_and_does_not_leak_code(client_api):
    response = client_api.post("/api/auth/request-code/", {"phone_number": "+79991234567"}, format="json")
    assert response.status_code == 202
    assert response.data["expires_in"] == 300
    assert "1234" not in str(response.data)
    challenge = PhoneChallenge.objects.get(phone_number="+79991234567")
    assert challenge.code_digest == code_digest("+79991234567", "1234")
    assert challenge.code_digest != "1234"
    assert User.objects.count() == 0


@pytest.mark.parametrize("value", ["79991234567", "+01234567890", "+1", "abc", "", "+123 456"])
def test_request_invalid_phone(client_api, value):
    response = client_api.post("/api/auth/request-code/", {"phone_number": value}, format="json")
    assert response.status_code == 400


def test_request_cooldown_is_429(client_api):
    data = {"phone_number": "+79991234567"}
    assert client_api.post("/api/auth/request-code/", data, format="json").status_code == 202
    response = client_api.post("/api/auth/request-code/", data, format="json")
    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0


def test_verify_new_user_and_token(client_api, login_api):
    payload = login_api("+79991234567")
    assert payload["created"] is True
    assert len(payload["profile"]["invite_code"]) == 6
    assert payload["profile"]["activated_invite_code"] is None
    assert payload["profile"]["invited_phones"] == []
    assert payload["token_type"] == "Token"
    assert User.objects.get(phone_number="+79991234567").has_usable_password() is False
    assert PhoneChallenge.objects.get(phone_number="+79991234567").consumed_at is not None


def test_bad_code_then_success(client_api):
    client_api.post("/api/auth/request-code/", {"phone_number": "+79991234567"}, format="json")
    bad = client_api.post(
        "/api/auth/verify-code/",
        {"phone_number": "+79991234567", "code": "5678"},
        format="json",
    )
    assert bad.status_code == 400
    assert PhoneChallenge.objects.get(phone_number="+79991234567").attempts == 1
    ok = client_api.post(
        "/api/auth/verify-code/",
        {"phone_number": "+79991234567", "code": "1234"},
        format="json",
    )
    assert ok.status_code == 200


def test_otp_attempt_limit_persists(client_api):
    phone = "+79991234567"
    client_api.post("/api/auth/request-code/", {"phone_number": phone}, format="json")
    for _ in range(4):
        assert (
            client_api.post(
                "/api/auth/verify-code/", {"phone_number": phone, "code": "9999"}, format="json"
            ).status_code
            == 400
        )
    assert (
        client_api.post(
            "/api/auth/verify-code/", {"phone_number": phone, "code": "9999"}, format="json"
        ).status_code
        == 429
    )
    assert PhoneChallenge.objects.get(phone_number=phone).attempts == 5
    assert (
        client_api.post(
            "/api/auth/verify-code/", {"phone_number": phone, "code": "1234"}, format="json"
        ).status_code
        == 429
    )


def test_otp_expires(client_api):
    phone = "+79991234567"
    client_api.post("/api/auth/request-code/", {"phone_number": phone}, format="json")
    PhoneChallenge.objects.filter(phone_number=phone).update(expires_at=timezone.now() - timedelta(seconds=1))
    response = client_api.post(
        "/api/auth/verify-code/", {"phone_number": phone, "code": "1234"}, format="json"
    )
    assert response.status_code == 400
    assert User.objects.count() == 0


def test_consumed_otp_cannot_be_replayed(client_api, login_api):
    login_api("+79991234567")
    response = client_api.post(
        "/api/auth/verify-code/", {"phone_number": "+79991234567", "code": "1234"}, format="json"
    )
    assert response.status_code == 400


def test_verify_without_request(client_api):
    response = client_api.post(
        "/api/auth/verify-code/", {"phone_number": "+79991234567", "code": "1234"}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize("bad", ["123", "12a4", "12345"])
def test_verify_invalid_code_format(client_api, bad):
    response = client_api.post(
        "/api/auth/verify-code/", {"phone_number": "+79991234567", "code": bad}, format="json"
    )
    assert response.status_code == 400


def test_existing_user_keeps_invite_code(client_api, login_api):
    first = login_api("+79991234567")
    PhoneChallenge.objects.filter(phone_number="+79991234567").update(
        last_sent_at=timezone.now() - timedelta(minutes=2)
    )
    second = login_api("+79991234567")
    assert second["created"] is False
    assert second["profile"]["invite_code"] == first["profile"]["invite_code"]
    assert second["token"] == first["token"]
    assert User.objects.count() == 1


def test_authenticated_profile_and_logout(client_api, login_api):
    payload = login_api("+79991234567")
    assert client_api.get("/api/profile/").status_code == 401
    client_api.credentials(HTTP_AUTHORIZATION=f"Token {payload['token']}")
    assert client_api.get("/api/profile/").status_code == 200
    assert client_api.post("/api/auth/logout/").status_code == 204
    assert client_api.get("/api/profile/").status_code == 401
