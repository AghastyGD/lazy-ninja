"""Auth configuration helpers."""

from typing import Any, Dict, Optional, Callable

from django.conf import settings


def _auth_cfg() -> Dict[str, Any]:
    return getattr(settings, "LAZY_NINJA_AUTH", {}) or {}


def get_setting(keys: list[str], default: Any = None) -> Any:
    """Resolve setting from LAZY_NINJA_AUTH or Django settings."""
    cfg = _auth_cfg()
    for key in keys:
        if key in cfg:
            return cfg[key]
        val = getattr(settings, key, None)
        if val is not None:
            return val
    return default


def get_jwt_secret() -> str:
    """Return the secret key used to sign JWTs."""
    secret = get_setting(["JWT_SECRET", "SECRET_KEY"])
    if not secret:
        raise RuntimeError("JWT secret is not configured.")
    return str(secret)


def get_jwt_algorithm() -> str:
    return get_setting(["JWT_ALGORITHM"], "HS256")


def get_jwt_issuer() -> str:
    return str(get_setting(["JWT_ISS", "JWT_ISSUER"], "lazy-ninja"))


def get_jwt_audience() -> str:
    return str(get_setting(["JWT_AUD", "JWT_AUDIENCE"], "lazy-ninja-api"))


def get_token_lifetimes() -> Dict[str, int]:
    """Return access and refresh token lifetimes in seconds."""
    return {
        "access": int(get_setting(["JWT_ACCESS_EXP"], 60 * 60 * 24)),
        "refresh": int(get_setting(["JWT_REFRESH_EXP"], 60 * 60 * 24 * 30)),
    }


def cookie_secure_flag() -> bool:
    return bool(get_setting(["COOKIE_SECURE"], not getattr(settings, "DEBUG", False)))


def should_validate_password() -> bool:
    """Check if password validation is enabled (default: True)."""
    return bool(get_setting(["VALIDATE_PASSWORD"], True))


def should_log_auth_events() -> bool:
    """Check if authentication events should be logged (default: True)."""
    return bool(get_setting(["LOG_AUTH_EVENTS"], True))


def is_stateful() -> bool:
    """Check if stateful token mode is enabled (default: False)."""
    return bool(get_setting(["STATEFUL"], False))


def get_blacklist_prefix() -> str:
    return str(get_setting(["BLACKLIST_PREFIX"], "lazy_ninja:bl"))


def should_set_cookies() -> bool:
    """Check if auth endpoints should set cookies (default: True)."""
    return bool(get_setting(["SET_COOKIES"], True))


def should_rotate_refresh() -> bool:
    """Check if refresh tokens should be rotated (default: True)."""
    return bool(get_setting(["ROTATE_REFRESH"], True))


def get_auth_hook(keys: list[str]) -> Optional[Callable[..., Any]]:
    hook = get_setting(keys)
    return hook if callable(hook) else None


def get_login_fields() -> list[str]:
    login_fields_setting = get_setting(["LOGIN_FIELDS"], ["username"])
    if isinstance(login_fields_setting, (list, tuple, set)):
        return [str(field) for field in login_fields_setting]
    return [str(login_fields_setting)]
