"""Opt-in authorization policies for generated model routes."""

from typing import Any, Callable, Optional

from django.contrib.auth import get_user_model
from django.db.models import Model, QuerySet
from ninja.errors import HttpError


class DjangoModelPermissions:
    """Use Django's model permissions, including permissions granted by groups.

    The API authenticator must return a Django user. A resolver can adapt an
    authenticator that returns another value. Object-level decisions and
    queryset scoping can be added by subclassing this policy.
    """

    actions = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "delete": "delete",
    }

    def __init__(
        self,
        user_resolver: Optional[Callable[[Any], Any]] = None,
        check_object_permissions: bool = False,
    ):
        self.user_resolver = user_resolver
        self.check_object_permissions = check_object_permissions

    def resolve_user(self, request: Any) -> Any:
        user = self.user_resolver(request) if self.user_resolver else getattr(request, "auth", None)
        if not isinstance(user, get_user_model()) or not user.is_authenticated or not user.is_active:
            raise HttpError(401, "Authentication required.")
        return user

    def has_permission(self, request: Any, model: type[Model], action: str, obj: Model | None = None) -> bool:
        user = self.resolve_user(request)
        permission = f"{model._meta.app_label}.{self.actions[action]}_{model._meta.model_name}"
        # Django's default ModelBackend denies every object-permission query.
        # Enable object checks only with a compatible authentication backend.
        if obj is not None and self.check_object_permissions:
            return user.has_perm(permission, obj)
        return user.has_perm(permission)

    def scope_queryset(self, request: Any, model: type[Model], action: str, queryset: QuerySet) -> QuerySet:
        return queryset
