import asyncio
import asyncio
import uuid
from types import SimpleNamespace

import pytest
from asgiref.sync import sync_to_async
from django.db import models
from ninja import Schema

from lazy_ninja.helpers import (
    to_kebab_case,
    parse_model_id,
    get_hook,
    execute_hook,
    handle_response,
    parse_query_param,
    apply_filters,
    apply_filters_async,
)

from tests.models import TestModel

@pytest.mark.parametrize("input_str,expected", [
    ("PostComments", "post-comments"),
    ("UserProfile", "user-profile"),
    ("APIKey", "api-key"),
    ("snake_case", "snake-case"),
    ("SCREAMING_SNAKE_CASE", "screaming-snake-case"),
    ("camelCase", "camel-case"),
    ("PascalCase", "pascal-case"),
    ("simpleword", "simpleword"),
    ("TwoWords", "two-words"),
    ("ManyManyWords", "many-many-words"),
    ("ABC", "abc"),
    ("XMLHttpRequest", "xml-http-request"),
])
def test_to_kebab_case(input_str, expected):
    """Test to_kebab_case function with various input formats"""
    result = to_kebab_case(input_str)
    assert result == expected


def test_parse_model_id_with_auto_field_returns_int():
    assert parse_model_id(TestModel, "123") == 123


def test_parse_model_id_preserves_non_numeric_strings():
    assert parse_model_id(TestModel, "abc-123") == "abc-123"


def test_parse_model_id_with_uuid_field_returns_original_value():
    class StubModel:
        class _Meta:
            pk = models.UUIDField(primary_key=True)

        _meta = _Meta()

    item_id = str(uuid.uuid4())
    assert parse_model_id(StubModel, item_id) == item_id


def test_get_hook_returns_defined_method():
    class Controller:
        def before_create(self, request, payload, schema):
            return payload

    controller = Controller()
    hook = get_hook(controller, "before_create")
    assert hook is not None
    assert hook(None, "value", None) == "value"


def test_get_hook_respects_default_hook_attribute():
    class Controller:
        def before_create(self, request, payload, schema):
            return payload

    Controller.before_create.__is_default_hook__ = True
    controller = Controller()
    hook = get_hook(controller, "before_create")
    result = execute_hook(hook, {"payload": True})
    assert result == {"payload": True}


def test_execute_hook_runs_custom_callable():
    calls = {}

    def custom_hook(value):
        calls["value"] = value
        return value.upper()

    result = execute_hook(custom_hook, "payload")
    assert result == "PAYLOAD"
    assert calls["value"] == "payload"


def test_execute_hook_returns_first_argument_for_default_hook():
    def default_hook(value):
        return "should not run"

    default_hook.__is_default_hook__ = True

    assert execute_hook(default_hook, {"key": "value"}) == {"key": "value"}


def test_handle_response_uses_custom_response():
    instance = SimpleNamespace(name="Example")

    def custom_response(request, payload):
        return {"custom": payload.name.upper()}

    result = handle_response(instance, SimpleNamespace, custom_response)
    assert result == {"custom": "EXAMPLE"}


def test_handle_response_validates_with_schema():
    class SampleSchema(Schema):
        name: str

    instance = SimpleNamespace(name="Sample")
    result = handle_response(instance, SampleSchema, None)
    assert isinstance(result, SampleSchema)
    assert result.model_dump() == {"name": "Sample"}


def test_parse_query_param_supports_multiple_operators():
    assert parse_query_param("published=true") == {"published": True}
    assert parse_query_param("count=5") == {"count": 5}
    assert parse_query_param("title=Hello") == {"title__icontains": "Hello"}
    assert parse_query_param("views>10") == {"views__gt": 10}
    assert parse_query_param("score<20") == {"score__lt": 20}
    assert parse_query_param("invalid") == {}


@pytest.mark.django_db
def test_apply_filters_filters_and_sorts_results(create_test_model, create_test_category):
    category = create_test_category(name="Filters")
    other_category = create_test_category(name="Other")
    create_test_model(title="Alpha", category=category)
    create_test_model(title="Beta", category=other_category)

    queryset = TestModel.objects.all()
    filtered = apply_filters(
        queryset,
        TestModel,
        q="title=Alpha",
        sort="title",
        order="asc",
        kwargs={"category": category, "nonexistent": "ignored"},
    )

    titles = [obj.title for obj in filtered]
    assert titles == ["Alpha"]

    sorted_qs = apply_filters(
        TestModel.objects.all(),
        TestModel,
        q=None,
        sort="title",
        order="desc",
        kwargs={},
    )
    assert [obj.title for obj in sorted_qs] == ["Beta", "Alpha"]


@pytest.mark.django_db(transaction=True)
def test_apply_filters_async_matches_sync_behavior(create_test_model, create_test_category):
    category = create_test_category(name="Async")
    create_test_model(title="Gamma", category=category)
    create_test_model(title="Delta", category=category)

    async def run():
        qs = await sync_to_async(lambda: TestModel.objects.all())()

        result = await apply_filters_async(
            qs,
            TestModel,
            q="title=Gamma",
            sort="title",
            order="asc",
            kwargs={"category": category.id},
        )
        return [item.title for item in result]

    titles = asyncio.run(run())
    assert titles == ["Gamma"]
