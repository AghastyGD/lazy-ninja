"""Auth hook helpers."""

from typing import Any, Callable, Optional

from .config import get_auth_hook


def on_login_hook() -> Optional[Callable[..., Any]]:
    return get_auth_hook(["ON_LOGIN", "LOGIN_HOOK"])


def on_register_hook() -> Optional[Callable[..., Any]]:
    return get_auth_hook(["ON_REGISTER", "REGISTER_HOOK"])


def on_refresh_hook() -> Optional[Callable[..., Any]]:
    return get_auth_hook(["ON_REFRESH", "REFRESH_HOOK"])


def on_logout_hook() -> Optional[Callable[..., Any]]:
    return get_auth_hook(["ON_LOGOUT", "LOGOUT_HOOK"])
