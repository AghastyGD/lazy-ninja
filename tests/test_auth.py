import json

import pytest
from django.contrib.auth import get_user_model


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