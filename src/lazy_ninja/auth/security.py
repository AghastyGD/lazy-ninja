"""Default Lazy Ninja authenticator for Django Ninja."""

from django.contrib.auth import get_user_model
from ninja.errors import HttpError
from ninja.security import HttpBearer

from .tokens import decode_token


class LazyNinjaAccessToken(HttpBearer):
    """Authenticate requests using Lazy Ninja access JWTs."""

    def authenticate(self, request, token):
        payload = decode_token(token, "access")
        user_id = payload.get("sub")
        if not user_id:
            raise HttpError(401, "Invalid token.")
        try:
            return get_user_model().objects.get(id=user_id)
        except get_user_model().DoesNotExist as exc:
            raise HttpError(401, "User not found.") from exc
