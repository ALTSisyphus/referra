import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def sms_fake(monkeypatch):
    monkeypatch.setattr("accounts.services.secrets.randbelow", lambda upper: 1234)
    monkeypatch.setattr("accounts.services.send_simulated_sms", lambda phone, code: None)


@pytest.fixture
def client_api():
    return APIClient()


@pytest.fixture
def user_factory(db):
    from accounts.models import User

    def create(phone_number):
        return User.objects.create_user(phone_number=phone_number)

    return create


@pytest.fixture
def login_api(client_api, db):
    def login(phone):
        response = client_api.post("/api/auth/request-code/", {"phone_number": phone}, format="json")
        assert response.status_code == 202, response.data
        response = client_api.post(
            "/api/auth/verify-code/",
            {"phone_number": phone, "code": "1234"},
            format="json",
        )
        assert response.status_code == 200, response.data
        return response.data

    return login
