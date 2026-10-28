import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_web_login_verify_profile_logout(client):
    assert client.get("/").status_code == 200
    login_response = client.post("/", {"phone_number": "+79991234567"})
    assert login_response.status_code == 302
    assert login_response.url == "/verify/"
    assert client.get("/verify/").status_code == 200
    response = client.post("/verify/", {"code": "1234"})
    assert response.status_code == 302
    assert response.url == "/profile/"
    assert client.get("/profile/").status_code == 200
    assert client.get("/logout/").status_code == 405
    assert client.post("/logout/").status_code == 302
    assert client.get("/profile/").status_code == 302


def test_web_invalid_phone_and_code(client):
    assert client.post("/", {"phone_number": "123"}).status_code == 200
    assert client.get("/verify/").status_code == 302
    client.post("/", {"phone_number": "+79991234567"})
    wrong = client.post("/verify/", {"code": "2222"})
    assert wrong.status_code == 200
    assert "Неверный код" in wrong.content.decode()
    assert get_user_model().objects.count() == 0


def test_web_invitation_flow(client):
    model = get_user_model()
    inviter = model.objects.create_user("+79990000001")
    invited = model.objects.create_user("+79990000002")
    client.force_login(invited)
    response = client.post("/profile/", {"invite_code": inviter.invite_code})
    assert response.status_code == 302
    assert model.objects.get(pk=invited.pk).invited_by_id == inviter.pk
    response = client.get("/profile/")
    assert inviter.invite_code in response.content.decode()
    client.force_login(inviter)
    assert invited.phone_number in client.get("/profile/").content.decode()


def test_web_cannot_activate_own_invite(client):
    user = get_user_model().objects.create_user("+79990000001")
    client.force_login(user)
    response = client.post("/profile/", {"invite_code": user.invite_code})
    assert response.status_code == 200
    assert "собственный код" in response.content.decode()


def test_api_docs_exist(client):
    assert client.get("/api/redoc/").status_code == 200
    assert client.get("/api/swagger/").status_code == 200
    assert client.get("/api/schema/").status_code == 200
