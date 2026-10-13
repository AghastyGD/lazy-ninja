"""Auth route registration and handlers."""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.utils import timezone as dj_timezone
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.utils import check_csrf

from .config import (
    cookie_secure_flag,
    get_login_fields,
    get_token_lifetimes,
    should_log_auth_events,
    should_rotate_refresh,
    should_set_cookies,
    should_validate_password,
    is_stateful,
)
from .hooks import (
    on_login_hook,
    on_register_hook,
    on_refresh_hook,
    on_logout_hook,
)
from .tokens import (
    generate_token,
    decode_token,
    blacklist_token_payload,
)
from ..utils.type_guards import (
    has_user_field,
    get_user_identifier,
)

logger = logging.getLogger(__name__)


def register_auth_routes(
    api: NinjaAPI,
    *,
    access_cookie_name: str = "lazy_ninja_access_token",
    refresh_cookie_name: str = "lazy_ninja_refresh_token",
    cookie_path: str = "/",
    tags: Optional[list[str]] = None,
) -> None:
    """
    Registers a full JWT-based authentication flow on the given NinjaAPI.

    Endpoints added:
        POST /auth/login
        POST /auth/register
        POST /auth/refresh
        GET  /auth/me
        POST /auth/logout
    """
    auth_tags = tags or ["Auth"]

    User = get_user_model()
    lifetimes = get_token_lifetimes()

    def _has_username_field() -> bool:
        return has_user_field(User, "username")

    class TokenPairSchema(Schema):
        access: str
        refresh: str

    class AuthResponseSchema(TokenPairSchema):
        user: dict

    class LoginSchema(Schema):
        login: Optional[str] = None
        email: Optional[str] = None
        username: Optional[str] = None
        password: str

    class RegisterSchema(Schema):
        login: Optional[str] = None
        email: Optional[str] = None
        password: str
        username: Optional[str] = None
        first_name: Optional[str] = None
        last_name: Optional[str] = None

    class RefreshSchema(Schema):
        refresh: Optional[str] = None

    class MeResponseSchema(Schema):
        user: dict

    def _serialize_user(user: Any) -> dict:
        """Expose only common identity fields, never arbitrary custom fields."""
        result = {"id": str(user.pk) if isinstance(user.pk, UUID) else user.pk}
        for field_name in dict.fromkeys((_get_username_field_name(), "username", "email", "first_name", "last_name")):
            if has_user_field(User, field_name):
                result[field_name] = getattr(user, field_name)
        return result

    def _apply_auth_cookies(request, response: HttpResponse, access: str, refresh: Optional[str]) -> None:
        if not should_set_cookies():
            return
        secure_flag = cookie_secure_flag()
        # Set a CSRF cookie even when the host project does not install
        # CsrfViewMiddleware. Cookie-authenticated unsafe requests need it.
        response["X-CSRFToken"] = get_token(request)
        CsrfViewMiddleware(lambda _request: response).process_response(request, response)
        response.set_cookie(
            access_cookie_name,
            access,
            max_age=lifetimes["access"],
            httponly=True,
            secure=secure_flag,
            samesite="Lax",
            path=cookie_path,
        )
        if refresh:
            response.set_cookie(
                refresh_cookie_name,
                refresh,
                max_age=lifetimes["refresh"],
                httponly=True,
                secure=secure_flag,
                samesite="Lax",
                path=cookie_path,
            )

    def _clear_auth_cookies(response: HttpResponse) -> None:
        if not should_set_cookies():
            return
        response.delete_cookie(access_cookie_name, path=cookie_path)
        response.delete_cookie(refresh_cookie_name, path=cookie_path)

    def _build_auth_payload(user: Any, *, rotate_refresh: bool = True) -> dict:
        access = generate_token(user, expires_in=lifetimes["access"], token_type="access")
        refresh = (
            generate_token(user, expires_in=lifetimes["refresh"], token_type="refresh")
            if rotate_refresh else None
        )
        return {
            "access": access,
            "refresh": refresh or "",
            "user": _serialize_user(user),
        }

    def _get_username_field_name() -> str:
        return str(getattr(User, "USERNAME_FIELD", "username"))

    def _resolve_login_identifier(payload: LoginSchema) -> str:
        login_fields = get_login_fields()
        if "login" in login_fields and payload.login:
            return payload.login
        if "email" in login_fields and payload.email:
            return payload.email
        if "username" in login_fields and payload.username:
            return payload.username
        raise HttpError(400, "Missing login identifier.")

    def _resolve_register_identifier(payload: RegisterSchema, username_field: str) -> str:
        identifier = payload.username or payload.login
        if username_field == "email":
            identifier = payload.email or payload.login
        if not identifier:
            raise HttpError(400, "Missing registration identifier.")
        return identifier

    def _authenticate_user(request, identifier: str, password: str):
        login_fields = get_login_fields()
        username_field = _get_username_field_name()
        user = authenticate(request, **{username_field: identifier}, password=password)
        if user or not has_user_field(User, "email"):
            return user
        if "email" in login_fields and username_field != "email" and "@" in identifier:
            user_by_email = User.objects.filter(email__iexact=identifier).first()
            if user_by_email is not None:
                username_value = user_by_email.get_username()
                return authenticate(request, username=username_value, password=password)
            return authenticate(request, email=identifier, password=password)
        return user

    def _bearer_from_request(request) -> Optional[str]:
        parts = (request.headers.get("Authorization") or "").split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None

    def _token_from_request(request, expected_type: str) -> Optional[str]:
        cookie_val = (
            request.COOKIES.get(access_cookie_name)
            if expected_type == "access"
            else request.COOKIES.get(refresh_cookie_name)
        ) if should_set_cookies() else None

        if expected_type == "refresh" and cookie_val:
            return cookie_val
        return _bearer_from_request(request) or cookie_val

    def _check_cookie_csrf(request) -> None:
        if check_csrf(request):
            raise HttpError(403, "CSRF check failed.")

    def _get_user_from_authorization(request, expected_type: str = "access") -> Any:
        token = _token_from_request(request, expected_type)
        if not token:
            raise HttpError(401, "Missing credentials")

        payload = decode_token(token, expected_type)
        user_id = payload.get("sub")

        try:
            user = User.objects.get(pk=user_id)  # type: ignore[misc]
        except (User.DoesNotExist, ValidationError, ValueError, TypeError) as exc:  # type: ignore[attr-defined]
            raise HttpError(401, "User not found.") from exc
        if not getattr(user, "is_active", True):
            raise HttpError(401, "Inactive user.")
        return user

    def _build_response(request, payload: dict, *, status: int = 200) -> HttpResponse:
        response = api.create_response(request, payload, status=status)
        _apply_auth_cookies(request, response, payload["access"], payload.get("refresh"))
        return response

    @api.post("/auth/login", response=AuthResponseSchema, tags=auth_tags, auth=None)
    def login(request, payload: LoginSchema):
        identifier = _resolve_login_identifier(payload)
        user = _authenticate_user(request, identifier, payload.password)
        if not user:
            if should_log_auth_events():
                logger.warning(
                    "Failed login attempt for email: %s from IP: %s",
                    identifier,
                    request.META.get("REMOTE_ADDR", "unknown")
                )
            raise HttpError(401, "Invalid credentials.")

        user.last_login = dj_timezone.now()  # type: ignore[attr-defined]
        user.save(update_fields=["last_login"])

        if should_log_auth_events():
            user_identifier = (
                getattr(user, "email", None) or
                getattr(user, "username", "unknown")
            )
            logger.info(
                "User logged in: %s (ID: %s) from IP: %s",
                user_identifier,
                user.id,  # type: ignore [attr-defined]
                request.META.get("REMOTE_ADDR", "unknown")
            )

        on_login = on_login_hook()
        if on_login:
            on_login(user=user, request=request)

        return _build_response(request, _build_auth_payload(user))

    @api.post("/auth/register", response=AuthResponseSchema, tags=auth_tags, auth=None)
    def register(request, payload: RegisterSchema):
        username_field = _get_username_field_name()
        identifier = _resolve_register_identifier(payload, username_field)

        normalized_email: Optional[str] = ""
        if has_user_field(User, "email"):
            email_value = payload.email or (identifier if username_field == "email" else None)
            email_field = User._meta.get_field("email")
            if not email_value and (username_field == "email" or not (email_field.blank or email_field.null)):
                raise HttpError(400, "E-mail is required.")
            normalized_email = email_value.lower().strip() if email_value else (None if email_field.null else "")
            if normalized_email and User.objects.filter(email__iexact=normalized_email).exists():
                raise HttpError(400, "E-mail already registered.")

        username = payload.username or (normalized_email or identifier)

        if _has_username_field() and User.objects.filter(username__iexact=username).exists():  # type: ignore
            raise HttpError(400, "Username already taken.")

        if should_validate_password():
            try:
                validate_password(payload.password)
            except ValidationError as exc:
                error_msg = "; ".join(exc.messages) if exc.messages else "Invalid password"
                raise HttpError(400, f"Password validation failed: {error_msg}")

        try:
            with transaction.atomic():
                user_kwargs: Dict[str, Any] = {
                    "password": payload.password,
                }

                if has_user_field(User, "email"):
                    user_kwargs["email"] = normalized_email
                if _has_username_field():
                    user_kwargs["username"] = username
                if has_user_field(User, username_field) and username_field not in user_kwargs:
                    user_kwargs[username_field] = identifier

                if payload.first_name is not None and hasattr(User, "first_name"):
                    user_kwargs["first_name"] = payload.first_name
                if payload.last_name is not None and hasattr(User, "last_name"):
                    user_kwargs["last_name"] = payload.last_name

                user = User.objects.create_user(**user_kwargs)  # type: ignore[misc]

                if should_log_auth_events():
                    logger.info(
                        "New user registered: %s from IP: %s",
                        get_user_identifier(user),
                        request.META.get("REMOTE_ADDR", "unknown")
                    )

                on_register = on_register_hook()
                if on_register:
                    on_register(user=user, request=request)

        except IntegrityError as exc:
            logger.error("Registration integrity error: %s", str(exc))
            raise HttpError(400, "Registration failed. Email or username may already be in use.")

        return _build_response(request, _build_auth_payload(user))

    @api.post("/auth/refresh", response=TokenPairSchema, tags=auth_tags, auth=None)
    def refresh_token(request, payload: RefreshSchema):
        if not payload.refresh and should_set_cookies() and request.COOKIES.get(refresh_cookie_name):
            _check_cookie_csrf(request)
        token_source = payload.refresh or _token_from_request(request, expected_type="refresh")
        if not token_source:
            raise HttpError(401, "Renewal token missing.")

        data = decode_token(token_source, expected_type="refresh")
        user_id = data.get("sub")

        try:
            user = User.objects.get(pk=user_id)  # type: ignore[misc]
        except (User.DoesNotExist, ValidationError, ValueError, TypeError) as exc:  # type: ignore[attr-defined]
            raise HttpError(401, "User not found.") from exc
        if not getattr(user, "is_active", True):
            raise HttpError(401, "Inactive user.")

        if is_stateful() and should_rotate_refresh():
            blacklist_token_payload(data)

        token_pair = {
            "access": generate_token(user, expires_in=lifetimes["access"], token_type="access"),
            "refresh": generate_token(
                user,
                expires_in=lifetimes["refresh"],
                token_type="refresh",
            ) if should_rotate_refresh() else token_source,
        }

        if should_log_auth_events():
            logger.debug("Token refreshed for user ID: %s", user.id)  # type: ignore[attr-defined]

        response = api.create_response(request, token_pair, status=200)
        _apply_auth_cookies(request, response, token_pair["access"], token_pair["refresh"])

        on_refresh = on_refresh_hook()
        if on_refresh:
            on_refresh(user=user, request=request)
        return response

    @api.get("/auth/me", response=MeResponseSchema, tags=auth_tags, auth=None)
    def me(request):
        user = _get_user_from_authorization(request, expected_type="access")
        return {"user": _serialize_user(user)}

    @api.post("/auth/logout", tags=auth_tags, auth=None)
    def logout(request):
        header_token = _bearer_from_request(request)
        if should_set_cookies() and (request.COOKIES.get(refresh_cookie_name) or (request.COOKIES.get(access_cookie_name) and not header_token)):
            _check_cookie_csrf(request)

        for token_type in ("access", "refresh"):
            token = _token_from_request(request, token_type)
            if not token:
                continue
            try:
                payload = decode_token(token, token_type)
            except HttpError:
                continue
            if should_log_auth_events() and token_type == "access":
                logger.info(
                    "User logged out: ID %s from IP: %s",
                    payload.get("sub"),
                    request.META.get("REMOTE_ADDR", "unknown"),
                )
            if is_stateful():
                blacklist_token_payload(payload)

        response = api.create_response(request, {"detail": "Logged out"}, status=200)
        _clear_auth_cookies(response)

        on_logout = on_logout_hook()
        if on_logout:
            on_logout(request=request)
        return response
