"""Default Lazy Ninja authenticator for Django Ninja."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from ninja.errors import HttpError
from ninja.security import APIKeyCookie, HttpBearer
from ninja.utils import check_csrf

from .tokens import decode_token


def _user_from_token(token):
    payload = decode_token(token, "access")
    user_id = payload.get("sub")
    if not user_id:
        raise HttpError(401, "Invalid token.")
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValidationError, ValueError, TypeError) as exc:
        raise HttpError(401, "User not found.") from exc
    if not getattr(user, "is_active", True):
        raise HttpError(401, "Inactive user.")
    return user


class LazyNinjaAccessToken(HttpBearer):
    """Authenticate requests using Lazy Ninja access JWTs."""

    def authenticate(self, request, token):
        return _user_from_token(token)


class LazyNinjaAccessCookie(APIKeyCookie):
    """Authenticate access cookies with Django Ninja's CSRF protection."""

    def __init__(self, cookie_name="lazy_ninja_access_token"):
        self.param_name = cookie_name
        super().__init__()

    def _get_key(self, request):
        if check_csrf(request):
            raise HttpError(403, "CSRF check failed.")
        return request.COOKIES.get(self.param_name)

    def authenticate(self, request, key):
        return _user_from_token(key) if key else None
