from datetime import datetime, timedelta, timezone
from typing import Optional, Type, Any, Dict

import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.models import Model
from django.http import HttpResponse
from django.utils import timezone as dj_timezone
from jwt import ExpiredSignatureError, PyJWTError
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError

from .utils.schema import generate_schema


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


def register_auth_routes(
    api: NinjaAPI,
    *,
    profile_model: Optional[Type[Model]] = None,
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

    UserPublicSchema = generate_schema(User, exclude=["password"])
    ProfileSchema = generate_schema(profile_model) if profile_model else None  # type: ignore[assignment]

    class TokenPairSchema(Schema):
        access: str
        refresh: str

    class AuthResponseSchema(TokenPairSchema):
        user: UserPublicSchema  # type: ignore[valid-type]
        profile: Optional[ProfileSchema] = None if ProfileSchema else None  # type: ignore[valid-type]

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
        user: UserPublicSchema  # type: ignore[valid-type]
        profile: Optional[ProfileSchema] = None if ProfileSchema else None  # type: ignore[valid-type]

    def _generate_token(user: Any, *, expires_in: int, token_type: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
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
        return UserPublicSchema.model_validate(user).model_dump()

    def _serialize_profile(profile: Optional[Any]) -> Optional[dict]:
        if not profile or not ProfileSchema:
            return None
        return ProfileSchema.model_validate(profile).model_dump()

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
            "profile": _serialize_profile(getattr(user, "profile", None)),
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
            user = User.objects.select_related("profile").get(id=user_id)
        except User.DoesNotExist as exc:
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
            raise HttpError(401, "Invalid credentials.")

        user.last_login = dj_timezone.now()
        user.save(update_fields=["last_login"])

        return _build_response(request, _build_auth_payload(user))

    @api.post("/auth/register", response=AuthResponseSchema, tags=auth_tags)
    def register(request, payload: RegisterSchema):
        if User.objects.filter(email__iexact=payload.email).exists():
            raise HttpError(400, "E-mail already registered.")

        with transaction.atomic():
            user_kwargs: Dict[str, Any] = {
                "email": payload.email,
                "password": payload.password,
                "username": payload.username or payload.email,
            }

            if hasattr(User, "first_name") and payload.first_name is not None:
                user_kwargs["first_name"] = payload.first_name
            if hasattr(User, "last_name") and payload.last_name is not None:
                user_kwargs["last_name"] = payload.last_name

            user = User.objects.create_user(**user_kwargs)  # type: ignore[attr-defined]

            if profile_model and hasattr(user, "profile"):
                profile = user.profile
                if payload.first_name and hasattr(profile, "first_name"):
                    profile.first_name = payload.first_name
                if payload.last_name and hasattr(profile, "last_name"):
                    profile.last_name = payload.last_name
                profile.save()

        return _build_response(request, _build_auth_payload(user))

    @api.post("/auth/refresh", response=TokenPairSchema, tags=auth_tags)
    def refresh_token(request, payload: RefreshSchema):
        token_source = payload.refresh or _token_from_request(request, expected_type="refresh")
        if not token_source:
            raise HttpError(401, "Renewal token missing.")

        data = _decode_token(token_source, expected_type="refresh")
        user_id = data.get("sub")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise HttpError(401, "User not found.") from exc

        token_pair = {
            "access": _generate_token(user, expires_in=lifetimes["access"], token_type="access"),
            "refresh": _generate_token(user, expires_in=lifetimes["refresh"], token_type="refresh"),
        }

        response = api.create_response(request, token_pair, status=200)
        _apply_auth_cookies(response, token_pair["access"], token_pair["refresh"])
        return response

    @api.get("/auth/me", response=MeResponseSchema, tags=auth_tags)
    def me(request):
        user = _get_user_from_authorization(request, expected_type="access")
        return {
            "user": _serialize_user(user),
            "profile": _serialize_profile(getattr(user, "profile", None)),
        }

    @api.post("/auth/logout", tags=auth_tags)
    def logout(request):
        response = api.create_response(request, {"detail": "Logged out"}, status=200)
        _clear_auth_cookies(response)
        return response
