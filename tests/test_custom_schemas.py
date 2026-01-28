from types import SimpleNamespace

import pytest
from ninja import Schema

from lazy_ninja.builder import DynamicAPI
from tests.models import TestModel
import lazy_ninja.builder as builder_module


class TestModelListSchema(Schema):
    __test__ = False
    id: int
    title: str


class TestModelDetailSchema(Schema):
    __test__ = False
    id: int
    title: str
    image: str | None


class TestModelCreateSchema(Schema):
    __test__ = False
    title: str
    image: str | None = None
    category: int


class TestModelUpdateSchema(Schema):
    __test__ = False
    title: str | None = None


@pytest.mark.django_db
def test_custom_schemas_are_used_in_registration(monkeypatch):
    captured = {}

    def fake_register_model_routes(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(builder_module, "register_model_routes", fake_register_model_routes)
    monkeypatch.setattr(builder_module.apps, "get_models", lambda: [TestModel])
    monkeypatch.setattr(
        DynamicAPI,
        "_get_existing_tables",
        lambda self: [TestModel._meta.db_table],
    )

    custom_schemas = {
        "TestModel": {
            "list": TestModelListSchema,
            "detail": TestModelDetailSchema,
            "create": TestModelCreateSchema,
            "update": TestModelUpdateSchema,
        }
    }

    dynamic_api = DynamicAPI(
        SimpleNamespace(),
        is_async=False,
        custom_schemas=custom_schemas,
    )
    dynamic_api.register_all_models()

    assert captured["list_schema"] is TestModelListSchema
    assert captured["detail_schema"] is TestModelDetailSchema
    assert captured["create_schema"] is TestModelCreateSchema
    assert captured["update_schema"] is TestModelUpdateSchema