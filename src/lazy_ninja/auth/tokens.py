"""JWT token helpers and stateful blacklist logic."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import jwt
from django.core.cache import cache
from jwt import ExpiredSignatureError, PyJWTError
from ninja.errors import HttpError

from .config import (
    get_jwt_secret,
    get_jwt_algorithm,
    get_jwt_issuer,
    get_jwt_audience,
    get_blacklist_prefix,
    is_stateful,
)


def generate_token(user: Any, *, expires_in: int, token_type: str) -> str:
    """Generate JWT token for user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),  # type: ignore[attr-defined]
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "iss": get_jwt_issuer(),
        "aud": get_jwt_audience(),
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=get_jwt_algorithm())


def decode_raw_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[get_jwt_algorithm()],
            issuer=get_jwt_issuer(),
            audience=get_jwt_audience(),
        )
    except ExpiredSignatureError as exc:
        raise HttpError(401, "Expired token.") from exc
    except PyJWTError as exc:
        raise HttpError(401, "Invalid token.") from exc

    return payload


def validate_token_payload(payload: Dict[str, Any], expected_type: str) -> None:
    if payload.get("type") != expected_type:
        raise HttpError(401, "Invalid token type.")

    if is_stateful():
        jti = payload.get("jti")
        if not jti:
            raise HttpError(401, "Missing token identifier.")
        if is_token_blacklisted(str(jti)):
            raise HttpError(401, "Token revoked.")


def decode_token(token: str, expected_type: str) -> Dict[str, Any]:
    payload = decode_raw_token(token)
    validate_token_payload(payload, expected_type)
    return payload


def get_token_ttl(payload: Dict[str, Any]) -> int:
    exp = payload.get("exp")
    try:
        ttl = int(exp) - int(datetime.now(timezone.utc).timestamp()) # type: ignore
        return max(ttl, 0)
    except (TypeError, ValueError):
        return 0


def blacklist_key(jti: str) -> str:
    return f"{get_blacklist_prefix()}:{get_jwt_issuer()}:{get_jwt_audience()}:{jti}"


def is_token_blacklisted(jti: str) -> bool:
    return bool(cache.get(blacklist_key(jti)))


def blacklist_token_payload(payload: Dict[str, Any]) -> None:
    if not is_stateful():
        return
    jti = payload.get("jti")
    if not jti:
        return
    ttl = get_token_ttl(payload)
    if ttl <= 0:
        return
    cache.set(blacklist_key(str(jti)), True, timeout=ttl)
