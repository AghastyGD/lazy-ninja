import json
from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from ninja.testing import TestAsyncClient
from ninja.errors import HttpError

from lazy_ninja.permissions import DjangoModelPermissions
from lazy_ninja.utils import generate_schema
from lazy_ninja.utils.model import SyncModelUtils
from tests.async_support import run_async

from tests.models import Category, Detail, Tag, TaggedModel, TestModel


def call(client, method, url, payload=None):
    if isinstance(client, TestAsyncClient):
        user = getattr(client, "current_user", AnonymousUser())
        if user.is_authenticated:
            user = get_user_model().objects.get(pk=user.pk)
        kwargs = {"user": user}
        if payload is not None:
            kwargs["json"] = payload
        return run_async(getattr(client, method)(url, **kwargs))
    kwargs = {"data": json.dumps(payload), "content_type": "application/json"} if payload is not None else {}
    result = getattr(client, method)(url, **kwargs)
    return result


def login(client, user):
    if isinstance(client, TestAsyncClient):
        client.current_user = get_user_model().objects.get(pk=user.pk)
    else:
        client.force_login(user)


def logout(client):
    if isinstance(client, TestAsyncClient):
        client.current_user = AnonymousUser()
    else:
        client.logout()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("prefix", ["sync", "async"])
def test_model_permissions_and_scope(prefix):
    with override_settings(ROOT_URLCONF="tests.urls_permissions"):
        if prefix == "async":
            from tests.urls_permissions import ScopedPermissions, make_api
            client = TestAsyncClient(make_api(True, f"test-rbac-{uuid4().hex}", ScopedPermissions()))
        else:
            client = Client()
        base = "/test-models/" if prefix == "async" else "/sync/test-models/"
        category = Category.objects.create(name="category")
        visible = TestModel.objects.create(title="visible", category=category)
        hidden = TestModel.objects.create(title="hidden", category=category)
        protected = TestModel.objects.create(title="protected", category=category)

        assert call(client, "get", base).status_code == 401
        user = get_user_model().objects.create_user(username=f"{prefix}-user", password="pw")
        login(client, user)
        assert call(client, "get", base).status_code == 403
        assert call(client, "post", base, {"title": "new", "category": category.pk}).status_code == 403
        assert TestModel.objects.count() == 3

        group = Group.objects.create(name=f"{prefix}-readers")
        group.permissions.add(Permission.objects.get(content_type__app_label="tests", codename="view_testmodel"))
        user.groups.add(group)
        response = call(client, "get", base)
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert call(client, "get", f"{base}{hidden.pk}").status_code == 404
        assert call(client, "get", f"{base}{protected.pk}").status_code == 403
        assert call(client, "get", f"{base}{visible.pk}").status_code == 200
        assert call(client, "patch", f"{base}{visible.pk}", {"title": "changed"}).status_code == 403
        assert call(client, "delete", f"{base}{visible.pk}").status_code == 403

        user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="tests",
            codename__in=["add_testmodel", "change_testmodel", "delete_testmodel"],
        ))
        # A new request gets a newly resolved user in real authentication flows.
        logout(client)
        login(client, user)
        assert call(client, "post", base, {"title": "new", "category": category.pk}).status_code == 200
        assert call(client, "patch", f"{base}{visible.pk}", {"title": "changed"}).status_code == 200
        assert call(client, "delete", f"{base}{visible.pk}").status_code == 200
        assert call(client, "patch", f"{base}{protected.pk}", {"title": "changed"}).status_code == 403
        assert TestModel.objects.get(pk=protected.pk).title == "protected"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("prefix", ["sync", "async"])
def test_many_to_many_and_one_to_one(prefix):
    with override_settings(ROOT_URLCONF="tests.urls_permissions"):
        if prefix == "async":
            from tests.urls_permissions import ScopedPermissions, make_api
            client = TestAsyncClient(make_api(True, f"test-relations-{uuid4().hex}", ScopedPermissions()))
        else:
            client = Client()
        base = "/open/test-models/" if prefix == "sync" else "/test-models/"
        user = get_user_model().objects.create_user(username="relations", password="pw", is_superuser=True)
        login(client, user)
        category = Category.objects.create(name="category")
        detail = Detail.objects.create(label="detail")
        first = Tag.objects.create(name="first")
        second = Tag.objects.create(name="second")
        response = call(client, "post", base, {
            "title": "related", "category": category.pk, "detail": detail.pk,
            "tags": [first.pk, second.pk],
        })
        assert response.status_code == 200, response.content
        pk = response.json()["id"]
        assert set(response.json()["tags"]) == {first.pk, second.pk}
        assert response.json()["detail"] == detail.pk
        assert set(call(client, "get", f"{base}{pk}").json()["tags"]) == {first.pk, second.pk}

        response = call(client, "patch", f"{base}{pk}", {"tags": [second.pk]})
        assert response.status_code == 200, response.content
        assert list(TestModel.objects.get(pk=pk).tags.values_list("pk", flat=True)) == [second.pk]
        response = call(client, "patch", f"{base}{pk}", {"tags": [999999], "title": "bad"})
        assert response.status_code == 400
        assert TestModel.objects.get(pk=pk).title == "related"
        assert call(client, "patch", f"{base}{pk}", {"tags": []}).status_code == 200
        assert not TestModel.objects.get(pk=pk).tags.exists()


@pytest.mark.django_db
def test_custom_through_relationship_is_read_only():
    tag = Tag.objects.create(name="tag")
    assert "tags" in generate_schema(TaggedModel).model_fields
    assert "tags" not in generate_schema(TaggedModel, write=True).model_fields
    with pytest.raises(ValidationError):
        SyncModelUtils().create_instance(TaggedModel, title="item", tags=[tag.pk])
    assert not TaggedModel.objects.exists()


@pytest.mark.django_db
def test_list_prefetches_many_to_many_rows():
    with override_settings(ROOT_URLCONF="tests.urls_permissions"):
        client = Client()
        user = get_user_model().objects.create_user(username="prefetch", password="pw")
        client.force_login(user)
        category = Category.objects.create(name="category")
        tag = Tag.objects.create(name="tag")
        for index in range(3):
            item = TestModel.objects.create(title=str(index), category=category)
            item.tags.add(tag)

        with CaptureQueriesContext(connection) as three_queries:
            assert call(client, "get", "/open/test-models/").status_code == 200
        for index in range(3, 6):
            item = TestModel.objects.create(title=str(index), category=category)
            item.tags.add(tag)
        with CaptureQueriesContext(connection) as six_queries:
            assert call(client, "get", "/open/test-models/").status_code == 200
        assert len(six_queries) == len(three_queries)


@pytest.mark.django_db
def test_django_policy_supports_user_resolver_and_object_backend():
    user = get_user_model().objects.create_user(username="resolver", password="pw")
    user.has_perm = Mock(return_value=True)
    instance = TestModel(title="unsaved")
    request = SimpleNamespace(auth="external-identity")
    policy = DjangoModelPermissions(
        user_resolver=lambda request: user,
        check_object_permissions=True,
    )
    assert policy.has_permission(request, TestModel, "retrieve", instance)
    user.has_perm.assert_called_once_with("tests.view_testmodel", instance)


def test_django_policy_rejects_missing_identity():
    with pytest.raises(HttpError) as error:
        DjangoModelPermissions().has_permission(SimpleNamespace(auth=None), TestModel, "list")
    assert error.value.status_code == 401
