# Authentication Guide

This guide explains the Lazy Ninja auth module, its configuration, and advanced usage. The auth feature is JWT-based, supports stateless or stateful flows, and is designed to adapt to different project setups.

## Quick start

Enable authentication by setting `auth=True` when initializing `DynamicAPI`.
This automatically registers the auth routes and protects all generated endpoints by default.

```python
from ninja import NinjaAPI
from lazy_ninja.builder import DynamicAPI

api = NinjaAPI()

auto_api = DynamicAPI(api, auth=True)
auto_api.init()
```


## Configuration

Set options under `LAZY_NINJA_AUTH` in Django settings.

### Core settings

- `JWT_SECRET`: Secret used to sign tokens. Defaults to `SECRET_KEY` if omitted.
- `JWT_ALGORITHM`: JWT algorithm (default: `HS256`).
- `JWT_ISS` / `JWT_ISSUER`: Token issuer (default: `lazy-ninja`).
- `JWT_AUD` / `JWT_AUDIENCE`: Token audience (default: `lazy-ninja-api`).
- `JWT_ACCESS_EXP`: Access token lifetime in seconds (default: 86400).
- `JWT_REFRESH_EXP`: Refresh token lifetime in seconds (default: 2592000).

### Login fields

Explicitly control which identifiers are accepted during login:

```python
LAZY_NINJA_AUTH = {
    "LOGIN_FIELDS": ["email", "username", "login"],
}
```

This avoids implicit fallback behavior and makes the login policy explicit.

### Cookies

- `SET_COOKIES`: Whether to set auth cookies (default: `True`).
- `COOKIE_SECURE`: Force secure cookies (default: `not DEBUG`).

### Password validation

- `VALIDATE_PASSWORD`: Whether to run Django password validators (default: `True`).

### Logging

- `LOG_AUTH_EVENTS`: Enables login/register/refresh/logout logs (default: `True`).

### Stateful mode

Enable server-side revocation using a cache-backed blacklist:

```python
LAZY_NINJA_AUTH = {
    "STATEFUL": True,
}
```

When stateful mode is on:

- Tokens include `jti` (JWT ID).
- Refresh rotates and blacklists old refresh tokens.
- Logout blacklists access + refresh when present.

The blacklist uses the Django cache backend and stores keys with a TTL matching the token expiration.

## Endpoints

- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/refresh`
- `GET /auth/me`
- `POST /auth/logout`

## Hooks

You can attach hooks for lifecycle events:

- `ON_LOGIN` / `LOGIN_HOOK`
- `ON_REGISTER` / `REGISTER_HOOK`
- `ON_REFRESH` / `REFRESH_HOOK`
- `ON_LOGOUT` / `LOGOUT_HOOK`

Example:

```python
def on_login(user, request):
    # audit or rate limit
    pass

LAZY_NINJA_AUTH = {
    "ON_LOGIN": on_login,
}
```

## Security notes

- Always set a strong `JWT_SECRET` in production.
- Use HTTPS with `COOKIE_SECURE=True`.
- Keep access tokens short-lived.
- Prefer stateful mode in high-security environments.

## Advanced concepts

### Stateless vs stateful

Stateless mode relies purely on token validity. Stateful mode adds revocation via blacklist, enabling immediate logout and refresh token invalidation.

### Token claims

Lazy Ninja includes:

- `iss` and `aud` for issuer/audience checks
- `jti` for stateful revocation

### Migration strategy

You can start with stateless mode and later enable stateful mode without breaking clients, since claims are compatible and both access and refresh endpoints remain stable.
