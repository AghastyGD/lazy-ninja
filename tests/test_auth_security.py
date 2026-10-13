import json
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, override_settings
from ninja import NinjaAPI

from lazy_ninja.builder import DynamicAPI
from tests.models import TestModel


def _login(client, username="security"):
    response = client.post(
        "/api/auth/login",
        data=json.dumps({"username": username, "password": "S0mePassw0rd!"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="security", email="security@example.com", password="S0mePassw0rd!"
    )


@pytest.mark.django_db
def test_logout_revokes_access_when_logging_disabled(client, user):
    cache.clear()
    with override_settings(LAZY_NINJA_AUTH={"STATEFUL": True, "LOG_AUTH_EVENTS": False, "SET_COOKIES": False}):
        token = _login(client)["access"]
        assert client.post("/api/auth/logout", HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 200
        assert client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 401


@pytest.mark.django_db
def test_logout_revokes_refresh_cookie_even_with_bearer_header(client, user):
    cache.clear()
    with override_settings(LAZY_NINJA_AUTH={"STATEFUL": True}):
        tokens = _login(client)
        assert client.post(
            "/api/auth/logout", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
        ).status_code == 200
        client.cookies.clear()
        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh": tokens["refresh"]}),
            content_type="application/json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
def test_refresh_without_rotation_remains_usable(client, user):
    cache.clear()
    with override_settings(LAZY_NINJA_AUTH={"STATEFUL": True, "ROTATE_REFRESH": False, "SET_COOKIES": False}):
        token = _login(client)["refresh"]
        for _ in range(2):
            response = client.post(
                "/api/auth/refresh", data=json.dumps({"refresh": token}), content_type="application/json"
            )
            assert response.status_code == 200
            assert response.json()["refresh"] == token


@pytest.mark.django_db
def test_inactive_user_token_is_rejected(client, user):
    with override_settings(LAZY_NINJA_AUTH={"SET_COOKIES": False}):
        tokens = _login(client)
        user.is_active = False
        user.save(update_fields=["is_active"])
        assert client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}").status_code == 401
        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh": tokens["refresh"]}),
            content_type="application/json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
def test_me_accepts_case_insensitive_bearer_scheme(client, user):
    with override_settings(LAZY_NINJA_AUTH={"SET_COOKIES": False}):
        token = _login(client)["access"]
        assert client.get("/api/auth/me", HTTP_AUTHORIZATION=f"bearer {token}").status_code == 200


@pytest.mark.django_db
def test_user_response_exposes_only_identity_fields(client, user):
    response = _login(client)["user"]
    assert response["email"] == user.email
    assert not {"password", "is_staff", "is_superuser", "last_login"} & response.keys()


@pytest.mark.django_db
def test_registration_accepts_optional_email(client):
    response = client.post(
        "/api/auth/register",
        data=json.dumps({"username": "without-email", "password": "S0mePassw0rd!"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "without-email"


@pytest.mark.django_db
def test_cookie_auth_and_csrf(user):
    with override_settings(ROOT_URLCONF="tests.urls_cookie", ALLOWED_HOSTS=["testserver"]):
        client = Client(enforce_csrf_checks=True)
        tokens = _login(client)
        assert client.cookies.get("csrftoken")
        assert client.get("/api/auth/me").status_code == 200
        assert client.post("/api/protected").status_code == 403
        csrf = client.cookies["csrftoken"].value
        assert client.post("/api/protected", HTTP_X_CSRFTOKEN=csrf).status_code == 200
        assert client.post(
            "/api/protected", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
        ).status_code == 200
        assert client.post("/api/auth/refresh", data="{}", content_type="application/json").status_code == 403
        assert client.post(
            "/api/auth/refresh", data="{}", content_type="application/json", HTTP_X_CSRFTOKEN=csrf
        ).status_code == 200
        assert client.post("/api/auth/logout").status_code == 403
        assert client.post("/api/auth/logout", HTTP_X_CSRFTOKEN=csrf).status_code == 200


@pytest.mark.django_db
def test_cookie_csrf_cookie_without_django_middleware(user):
    middleware = [entry for entry in settings.MIDDLEWARE if "CsrfViewMiddleware" not in entry]
    with override_settings(ROOT_URLCONF="tests.urls_cookie", MIDDLEWARE=middleware, ALLOWED_HOSTS=["testserver"]):
        client = Client(enforce_csrf_checks=True)
        _login(client)
        assert client.cookies.get("csrftoken")
        assert client.post("/api/protected").status_code == 403


@pytest.mark.django_db
def test_cookie_csrf_with_session_backed_csrf(user):
    with override_settings(ROOT_URLCONF="tests.urls_cookie", CSRF_USE_SESSIONS=True, ALLOWED_HOSTS=["testserver"]):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"username": "security", "password": "S0mePassw0rd!"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert client.post("/api/protected").status_code == 403
        assert client.post(
            "/api/protected", HTTP_X_CSRFTOKEN=response["X-CSRFToken"]
        ).status_code == 200


def test_user_model_never_gets_generated_crud(monkeypatch):
    api = NinjaAPI(urls_namespace="user-exclusion-test")
    builder = DynamicAPI(api, auth=True, is_async=False)
    monkeypatch.setattr(builder, "_get_existing_tables", lambda: [TestModel._meta.db_table])
    with patch("lazy_ninja.builder.get_user_model", return_value=TestModel), patch(
        "lazy_ninja.builder.apps.get_models", return_value=[TestModel]
    ), patch("lazy_ninja.builder.register_model_routes") as register:
        builder._register_all_models_sync()
    register.assert_not_called()
