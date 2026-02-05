"""Auth package for lazy_ninja."""

from .base import register_auth_routes
from .security import LazyNinjaAccessToken

__all__ = ["register_auth_routes", "LazyNinjaAccessToken"]
