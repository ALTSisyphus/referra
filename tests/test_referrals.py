import pytest

from accounts.models import User
from accounts.services import InvalidReferralError, activate_invite_code

pytestmark = pytest.mark.django_db


def auth(client_api, token):
    client_api.credentials(HTTP_AUTHORIZATION=f"Token {token}")


def test_activate_referral_and_referrer_list(client_api, login_api):
    inviter = login_api("+79990000001")
    invited = login_api("+79990000002")
    auth(client_api, invited["token"])
    result = client_api.post(
        "/api/profile/activate-invite/",
        {"invite_code": inviter["profile"]["invite_code"].lower()},
        format="json",
    )
    assert result.status_code == 200
    assert result.data["activated_invite_code"] == inviter["profile"]["invite_code"]
    auth(client_api, inviter["token"])
    profile = client_api.get("/api/profile/")
    assert profile.data["invited_phones"] == ["+79990000002"]


def test_activate_referral_twice_forbidden(client_api, login_api):
    inviter = login_api("+79990000001")
    invited = login_api("+79990000002")
    auth(client_api, invited["token"])
    code = inviter["profile"]["invite_code"]
    assert (
        client_api.post("/api/profile/activate-invite/", {"invite_code": code}, format="json").status_code
        == 200
    )
    assert (
        client_api.post("/api/profile/activate-invite/", {"invite_code": code}, format="json").status_code
        == 400
    )
    assert User.objects.get(phone_number="+79990000002").invited_by.phone_number == "+79990000001"


def test_self_referral_is_forbidden(client_api, login_api):
    member = login_api("+79990000001")
    auth(client_api, member["token"])
    response = client_api.post(
        "/api/profile/activate-invite/",
        {"invite_code": member["profile"]["invite_code"]},
        format="json",
    )
    assert response.status_code == 400


def test_unknown_and_invalid_referral_code(client_api, login_api):
    member = login_api("+79990000001")
    auth(client_api, member["token"])
    assert (
        client_api.post("/api/profile/activate-invite/", {"invite_code": "NOT"}, format="json").status_code
        == 400
    )
    assert (
        client_api.post("/api/profile/activate-invite/", {"invite_code": "------"}, format="json").status_code
        == 400
    )
    assert (
        client_api.post("/api/profile/activate-invite/", {"invite_code": "ZZZZZZ"}, format="json").status_code
        == 400
    )


def test_activation_requires_auth(client_api, user_factory):
    another = user_factory("+79990000001")
    response = client_api.post(
        "/api/profile/activate-invite/", {"invite_code": another.invite_code}, format="json"
    )
    assert response.status_code == 401


def test_referral_cycle_rejected(user_factory):
    a = user_factory("+79990000001")
    b = user_factory("+79990000002")
    c = user_factory("+79990000003")
    activate_invite_code(b, a.invite_code)
    activate_invite_code(c, b.invite_code)
    with pytest.raises(InvalidReferralError, match="циклическую"):
        activate_invite_code(a, c.invite_code)


def test_unique_invite_codes(user_factory):
    codes = {user_factory(f"+79990000{i:03d}").invite_code for i in range(25)}
    assert len(codes) == 25


def test_no_phone_numbers_in_another_users_profile(client_api, login_api):
    login_api("+79990000001")
    member = login_api("+79990000002")
    auth(client_api, member["token"])
    profile = client_api.get("/api/profile/")
    assert "+79990000001" not in str(profile.data)
