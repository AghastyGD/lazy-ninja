from types import SimpleNamespace

from ninja import Schema

from lazy_ninja.core import register_model_routes
from lazy_ninja.base import BaseModelController
from lazy_ninja.registry import ModelRegistry


class ListSchema(Schema):
    id: int


class DetailSchema(Schema):
    id: int


class CreateSchema(Schema):
    id: int


class UpdateSchema(Schema):
    id: int | None = None


def _call_register_model_routes(monkeypatch, controller):
    captured = {}

    def fake_register(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(ModelRegistry, "discover_controllers", lambda: None)
    monkeypatch.setattr(ModelRegistry, "get_controller", lambda name: controller)

    from lazy_ninja import core as core_module

    monkeypatch.setattr(core_module, "register_model_routes_internal", fake_register)

    register_model_routes(
        api=SimpleNamespace(),
        model=SimpleNamespace(__name__="Widget", _meta=None),
        base_url="/widgets",
        list_schema=ListSchema,
        detail_schema=DetailSchema,
        create_schema=CreateSchema,
        update_schema=UpdateSchema,
        pagination_strategy=None,
    )

    return captured


def test_register_model_routes_uses_custom_controller_hooks(monkeypatch):
    class CustomController(BaseModelController):
        @classmethod
        def before_create(cls, request, payload, schema):
            return payload

    captured = _call_register_model_routes(monkeypatch, CustomController)
    assert captured["before_create"].__func__ is CustomController.before_create.__func__
    assert captured["after_create"].__func__ is BaseModelController.after_create.__func__


def test_register_model_routes_fallback_to_default_hooks(monkeypatch):
    captured = _call_register_model_routes(monkeypatch, None)
    assert captured["before_create"].__func__ is BaseModelController.before_create.__func__
    assert captured["after_delete"].__func__ is BaseModelController.after_delete.__func__
