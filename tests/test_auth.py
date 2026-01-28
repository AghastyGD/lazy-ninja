import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings


@pytest.mark.django_db
def test_register_success(client):
    payload = {
        "email": "user1@example.com",
        "password": "S0mePassw0rd!",
        "username": "user1",
        "first_name": "User",
        "last_name": "One",
    }

    response = client.post(
        "/api/auth/register",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert "access" in data
    assert "refresh" in data
    assert "user" in data
    assert data["user"]["email"] == payload["email"]


@pytest.mark.django_db
def test_register_duplicate_email_fails(client):
    User = get_user_model()
    User.objects.create_user(
        username="userdup",
        email="dup@example.com",
        password="S0mePassw0rd!",
    )

    response = client.post(
        "/api/auth/register",
        data=json.dumps({
            "email": "dup@example.com",
            "password": "S0mePassw0rd!",
        }),
        content_type="application/json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_login_success_and_me_flow(client):
    with override_settings(LAZY_NINJA_AUTH={"LOGIN_FIELDS": ["email", "username", "login"]}):
        User = get_user_model()
        User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="S0mePassw0rd!",
        )
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "user2@example.com",
                "password": "S0mePassw0rd!",
            }),
            content_type="application/json",
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["access"]
        assert access_token

        me_response = client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["user"]["email"] == "user2@example.com"


@pytest.mark.django_db
def test_login_invalid_credentials(client):
    with override_settings(LAZY_NINJA_AUTH={"LOGIN_FIELDS": ["email", "username", "login"]}):
        response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "unknown@example.com",
                "password": "badpass",
            }),
            content_type="application/json",
        )

        assert response.status_code == 401


@pytest.mark.django_db
def test_refresh_token_flow(client):
    with override_settings(LAZY_NINJA_AUTH={"LOGIN_FIELDS": ["email", "username", "login"]}):
        User = get_user_model()
        User.objects.create_user(
            username="user3@example.com",
            email="user3@example.com",
            password="S0mePassw0rd!",
        )

        login_response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "user3@example.com",
                "password": "S0mePassw0rd!",
            }),
            content_type="application/json",
        )

        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh"]

        refresh_response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh": refresh_token}),
            content_type="application/json",
        )

        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access" in refresh_data
        assert "refresh" in refresh_data


@pytest.mark.django_db
def test_logout_clears_cookies(client):
    with override_settings(LAZY_NINJA_AUTH={"LOGIN_FIELDS": ["email", "username", "login"]}):
        User = get_user_model()
        User.objects.create_user(
            username="user4@example.com",
            email="user4@example.com",
            password="S0mePassw0rd!",
        )

        login_response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "user4@example.com",
                "password": "S0mePassw0rd!",
            }),
            content_type="application/json",
        )

        assert login_response.status_code == 200
        access_cookie = login_response.cookies.get("lazy_ninja_access_token")
        refresh_cookie = login_response.cookies.get("lazy_ninja_refresh_token")
        assert access_cookie is not None
        assert refresh_cookie is not None

        logout_response = client.post(
            "/api/auth/logout",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert logout_response.status_code == 200
        assert logout_response.cookies.get("lazy_ninja_access_token") is not None
        assert logout_response.cookies.get("lazy_ninja_refresh_token") is not None


@pytest.mark.django_db
def test_login_with_username_identifier(client):
    with override_settings(LAZY_NINJA_AUTH={"LOGIN_FIELDS": ["username"]}):
        User = get_user_model()
        User.objects.create_user(
            username="userlogin",
            email="userlogin@example.com",
            password="S0mePassw0rd!",
        )

        response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "username": "userlogin",
                "password": "S0mePassw0rd!",
            }),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["access"]


@pytest.mark.django_db
def test_login_with_login_identifier(client):
    with override_settings(LAZY_NINJA_AUTH={"LOGIN_FIELDS": ["login", "email"]}):
        User = get_user_model()
        User.objects.create_user(
            username="loginalias",
            email="loginalias@example.com",
            password="S0mePassw0rd!",
        )

        response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "login": "loginalias@example.com",
                "password": "S0mePassw0rd!",
            }),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["access"]


@pytest.mark.django_db
def test_issuer_audience_mismatch_rejected(client):
    with override_settings(LAZY_NINJA_AUTH={"LOGIN_FIELDS": ["email"]}):
        User = get_user_model()
        User.objects.create_user(
            username="issuser",
            email="issuser@example.com",
            password="S0mePassw0rd!",
        )

        login_response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "issuser@example.com",
                "password": "S0mePassw0rd!",
            }),
            content_type="application/json",
        )

        assert login_response.status_code == 200
        access_token = login_response.json()["access"]

    with override_settings(LAZY_NINJA_AUTH={"JWT_ISS": "other-iss", "JWT_AUD": "other-aud"}):
        me_response = client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

    assert me_response.status_code == 401


@pytest.mark.django_db
def test_stateful_refresh_blacklists_refresh_token(client):
    cache.clear()
    User = get_user_model()
    User.objects.create_user(
        username="stateful1",
        email="stateful1@example.com",
        password="S0mePassw0rd!",
    )

    with override_settings(LAZY_NINJA_AUTH={"STATEFUL": True, "LOGIN_FIELDS": ["email"]}):
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "stateful1@example.com",
                "password": "S0mePassw0rd!",
            }),
            content_type="application/json",
        )

        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh"]

        first_refresh = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh": refresh_token}),
            content_type="application/json",
        )
        assert first_refresh.status_code == 200

        second_refresh = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh": refresh_token}),
            content_type="application/json",
        )
        assert second_refresh.status_code == 401


@pytest.mark.django_db
def test_stateful_logout_blacklists_access_token(client):
    cache.clear()
    User = get_user_model()
    User.objects.create_user(
        username="stateful2",
        email="stateful2@example.com",
        password="S0mePassw0rd!",
    )

    with override_settings(LAZY_NINJA_AUTH={"STATEFUL": True, "LOGIN_FIELDS": ["email"]}):
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "stateful2@example.com",
                "password": "S0mePassw0rd!",
            }),
            content_type="application/json",
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access"]

        logout_response = client.post(
            "/api/auth/logout",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        assert logout_response.status_code == 200

        me_response = client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        assert me_response.status_code == 401