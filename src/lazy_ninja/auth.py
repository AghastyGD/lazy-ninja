import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, cast

import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone as dj_timezone
from jwt import ExpiredSignatureError, PyJWTError
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError

from .utils.schema import generate_schema
from .utils.type_guards import (
    has_user_field,
    get_user_identifier,
)

logger = logging.getLogger(__name__)


def _auth_cfg() -> Dict[str, Any]:
    return getattr(settings, "LAZY_NINJA_AUTH", {}) or {}


def _get_setting(keys: list[str], default: Any = None) -> Any:
    """Resolve setting from LAZY_NINJA_AUTH or Django settings."""
    cfg = _auth_cfg()
    for key in keys:
        if key in cfg:
            return cfg[key]
        val = getattr(settings, key, None)
        if val is not None:
            return val
    return default


def _get_jwt_secret() -> str:
    """Return the secret key used to sign JWTs."""
    secret = _get_setting(["JWT_SECRET", "SECRET_KEY"])
    if not secret:
        raise RuntimeError("JWT secret is not configured.")
    return str(secret)


def _get_jwt_algorithm() -> str:
    return _get_setting(["JWT_ALGORITHM"], "HS256")


def _get_token_lifetimes() -> Dict[str, int]:
    """Return access and refresh token lifetimes in seconds."""
    return {
        "access": int(_get_setting(["JWT_ACCESS_EXP"], 60 * 60 * 24)),
        "refresh": int(_get_setting(["JWT_REFRESH_EXP"], 60 * 60 * 24 * 30)),
    }


def _cookie_secure_flag() -> bool:
    return bool(_get_setting(["COOKIE_SECURE"], not getattr(settings, "DEBUG", False)))


def _should_validate_password() -> bool:
    """Check if password validation is enabled (default: True)."""
    return bool(_get_setting(["VALIDATE_PASSWORD"], True))


def _should_log_auth_events() -> bool:
    """Check if authentication events should be logged (default: True)."""
    return bool(_get_setting(["LOG_AUTH_EVENTS"], True))


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
    lifetimes = _get_token_lifetimes()

    def _has_username_field() -> bool:
        return has_user_field(User, "username")

    UserPublicSchema = generate_schema(User, exclude=["password"])

    class TokenPairSchema(Schema):
        access: str
        refresh: str

    class AuthResponseSchema(TokenPairSchema):
        user: dict 

    class LoginSchema(Schema):
        email: str
        password: str

    class RegisterSchema(Schema):
        email: str
        password: str
        username: Optional[str] = None
        first_name: Optional[str] = None
        last_name: Optional[str] = None

    class RefreshSchema(Schema):
        refresh: Optional[str] = None

    class MeResponseSchema(Schema):
        user: dict 

    def _generate_token(user: Any, *, expires_in: int, token_type: str) -> str:
        """Generate JWT token for user.
        
        Args:
            user: Django user instance (requires .id attribute)
            expires_in: Token lifetime in seconds
            token_type: Token type ("access" or "refresh")
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),  # type: ignore[attr-defined]
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        }
        return jwt.encode(payload, _get_jwt_secret(), algorithm=_get_jwt_algorithm())

    def _decode_token(token: str, expected_type: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                _get_jwt_secret(),
                algorithms=[_get_jwt_algorithm()],
            )
        except ExpiredSignatureError as exc:
            raise HttpError(401, "Expired token.") from exc
        except PyJWTError as exc:
            raise HttpError(401, "Invalid token.") from exc

        if payload.get("type") != expected_type:
            raise HttpError(401, "Invalid token type.")
        return payload

    def _serialize_user(user: Any) -> dict:
        """Serialize user to dict using dynamic schema."""
        schema_instance = UserPublicSchema.model_validate(user)
        return cast(dict, schema_instance.model_dump())

    def _apply_auth_cookies(response: HttpResponse, access: str, refresh: Optional[str]) -> None:
        secure_flag = _cookie_secure_flag()
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
            )

    def _clear_auth_cookies(response: HttpResponse) -> None:
        response.delete_cookie(access_cookie_name, path=cookie_path)
        response.delete_cookie(refresh_cookie_name, path=cookie_path)

    def _build_auth_payload(user: Any, *, rotate_refresh: bool = True) -> dict:
        access = _generate_token(user, expires_in=lifetimes["access"], token_type="access")
        refresh = (
            _generate_token(user, expires_in=lifetimes["refresh"], token_type="refresh")
            if rotate_refresh else None
        )
        return {
            "access": access,
            "refresh": refresh or "",
            "user": _serialize_user(user),
        }

    def _token_from_request(request, expected_type: str) -> Optional[str]:
        cookie_val = (
            request.COOKIES.get(access_cookie_name)
            if expected_type == "access"
            else request.COOKIES.get(refresh_cookie_name)
        )

        auth_header = request.headers.get("Authorization") or ""
        if auth_header.startswith("Bearer "):
            return auth_header.split(" ", 1)[1]

        return cookie_val

    def _get_user_from_authorization(request, expected_type: str = "access") -> Any:
        token = _token_from_request(request, expected_type)
        if not token:
            raise HttpError(401, "Missing credentials")

        payload = _decode_token(token, expected_type)
        user_id = payload.get("sub")

        try:
            user = User.objects.get(id=user_id)  # type: ignore[misc]
        except User.DoesNotExist as exc:  # type: ignore[attr-defined]
            raise HttpError(401, "User not found.") from exc
        return user

    def _build_response(request, payload: dict, *, status: int = 200) -> HttpResponse:
        response = api.create_response(request, payload, status=status)
        _apply_auth_cookies(response, payload["access"], payload.get("refresh"))
        return response

    @api.post("/auth/login", response=AuthResponseSchema, tags=auth_tags)
    def login(request, payload: LoginSchema):
        user = authenticate(request, username=payload.email, password=payload.password)
        if not user:
            if _should_log_auth_events():
                logger.warning(
                    "Failed login attempt for email: %s from IP: %s",
                    payload.email,
                    request.META.get("REMOTE_ADDR", "unknown")
                )
            raise HttpError(401, "Invalid credentials.")

        user.last_login = dj_timezone.now()  # type: ignore[attr-defined]
        user.save(update_fields=["last_login"])

        if _should_log_auth_events():
            user_identifier = (
                getattr(user, 'email', None) or 
                getattr(user, 'username', 'unknown')
            )
            logger.info(
                "User logged in: %s (ID: %s) from IP: %s",
                user_identifier,
                user.id, # type: ignore [attr-defined]
                request.META.get("REMOTE_ADDR", "unknown")
            )

        return _build_response(request, _build_auth_payload(user))

    @api.post("/auth/register", response=AuthResponseSchema, tags=auth_tags)
    def register(request, payload: RegisterSchema):
        normalized_email = payload.email.lower().strip()

        if User.objects.filter(email__iexact=normalized_email).exists():
            raise HttpError(400, "E-mail already registered.")

        username = payload.username or normalized_email
        
        if _has_username_field() and User.objects.filter(username__iexact=username).exists(): # type: ignore
            raise HttpError(400, "Username already taken.")

        if _should_validate_password():
            try:
                validate_password(payload.password)
            except ValidationError as e:
                error_msg = "; ".join(e.messages) if e.messages else "Invalid password"
                raise HttpError(400, f"Password validation failed: {error_msg}")

        try:
            with transaction.atomic():
                user_kwargs: Dict[str, Any] = {
                    "email": normalized_email,
                    "password": payload.password,
                    "username": username,
                }

                if payload.first_name is not None and hasattr(User, "first_name"):
                    user_kwargs["first_name"] = payload.first_name
                if payload.last_name is not None and hasattr(User, "last_name"):
                    user_kwargs["last_name"] = payload.last_name

                user = User.objects.create_user(**user_kwargs)  # type: ignore[misc]

                if _should_log_auth_events():
                    logger.info(
                        "New user registered: %s from IP: %s",
                        get_user_identifier(user),
                        request.META.get("REMOTE_ADDR", "unknown")
                    )

        except IntegrityError as e:
            logger.error("Registration integrity error: %s", str(e))
            raise HttpError(400, "Registration failed. Email or username may already be in use.")

        return _build_response(request, _build_auth_payload(user))

    @api.post("/auth/refresh", response=TokenPairSchema, tags=auth_tags)
    def refresh_token(request, payload: RefreshSchema):
        token_source = payload.refresh or _token_from_request(request, expected_type="refresh")
        if not token_source:
            raise HttpError(401, "Renewal token missing.")

        data = _decode_token(token_source, expected_type="refresh")
        user_id = data.get("sub")

        try:
            user = User.objects.only("id").get(id=user_id)  # type: ignore[misc]
        except User.DoesNotExist as exc:  # type: ignore[attr-defined]
            raise HttpError(401, "User not found.") from exc

        token_pair = {
            "access": _generate_token(user, expires_in=lifetimes["access"], token_type="access"),
            "refresh": _generate_token(user, expires_in=lifetimes["refresh"], token_type="refresh"),
        }

        if _should_log_auth_events():
            logger.debug("Token refreshed for user ID: %s", user.id)  # type: ignore[attr-defined]

        response = api.create_response(request, token_pair, status=200)
        _apply_auth_cookies(response, token_pair["access"], token_pair["refresh"])
        return response

    @api.get("/auth/me", response=MeResponseSchema, tags=auth_tags)
    def me(request):
        user = _get_user_from_authorization(request, expected_type="access")
        return {"user": _serialize_user(user)}

    @api.post("/auth/logout", tags=auth_tags)
    def logout(request):
        try:
            if _should_log_auth_events():
                token = _token_from_request(request, "access")
                if token:
                    payload = _decode_token(token, "access")
                    user_id = payload.get("sub")
                    logger.info(
                        "User logged out: ID %s from IP: %s",
                        user_id,
                        request.META.get("REMOTE_ADDR", "unknown")
                    )
        except Exception:
            pass

        response = api.create_response(request, {"detail": "Logged out"}, status=200)
        _clear_auth_cookies(response)
        return response
