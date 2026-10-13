"""Integration URLs for opt-in authorization and relationship tests."""

from django.urls import path
from ninja import NinjaAPI
from ninja.security import django_auth

from lazy_ninja.core import register_model_routes
from lazy_ninja.permissions import DjangoModelPermissions
from lazy_ninja.pagination import get_pagination_strategy
from lazy_ninja.utils import generate_schema
from tests.models import TestModel


class ScopedPermissions(DjangoModelPermissions):
    def scope_queryset(self, request, model, action, queryset):
        return queryset.exclude(title="hidden")

    def has_permission(self, request, model, action, obj=None):
        return super().has_permission(request, model, action, obj) and (
            obj is None or obj.title != "protected"
        )


def make_api(is_async, namespace, policy):
    api = NinjaAPI(auth=django_auth, urls_namespace=namespace)
    register_model_routes(
        api=api,
        model=TestModel,
        base_url="/test-models",
        list_schema=generate_schema(TestModel),
        detail_schema=generate_schema(TestModel),
        create_schema=generate_schema(TestModel, exclude=["id"], write=True),
        update_schema=generate_schema(TestModel, exclude=["id"], update=True, write=True),
        pagination_strategy=get_pagination_strategy(),
        permission_policy=policy,
        is_async=is_async,
    )
    return api


sync_api = make_api(False, "test-permissions-sync", ScopedPermissions())
async_api = make_api(True, "test-permissions-async", ScopedPermissions())
open_api = make_api(False, "test-permissions-open", None)

urlpatterns = [
    path("sync/", sync_api.urls),
    path("async/", async_api.urls),
    path("open/", open_api.urls),
]
