import pytest
from django.test import Client

from lazy_ninja.builder import ExclusionConfig
from lazy_ninja.builder import DynamicAPI
from lazy_ninja.permissions import DjangoModelPermissions
from ninja import NinjaAPI
from tests.models import TestModel

@pytest.mark.django_db
def test_dynamic_api_registration(client):
    """Tests if all routes are registered correctly"""
    client = Client()
    url = "/api/test-models/"
    response = client.get(url)
    assert response.status_code == 200
    assert response.json() ==  {
        'count': 0,
        'items': []
    }


def make_model(app_label, name):
    return type(name, (), {"_meta": type("_meta", (), {"app_label": app_label})()})


def test_exclusion_config_default_system_apps_excluded():
    config = ExclusionConfig()
    auth_model = make_model("auth", "User")
    assert config.should_exclude_model(auth_model) is True


def test_exclusion_config_custom_rules():
    model_a = make_model("blog", "Post")
    model_b = make_model("blog", "Comment")
    config = ExclusionConfig(exclude={"blog": {"Comment"}})

    assert config.should_exclude_model(model_a) is False
    assert config.should_exclude_model(model_b) is True

    config = ExclusionConfig(exclude={"shop": True})
    shop_model = make_model("shop", "Order")
    assert config.should_exclude_model(shop_model) is True


def test_dynamic_api_passes_permission_policy_to_generated_routes(monkeypatch):
    from lazy_ninja import builder as builder_module

    policy = DjangoModelPermissions()
    dynamic = DynamicAPI(NinjaAPI(urls_namespace="builder-policy-test"), permission_policy=policy)
    monkeypatch.setattr(dynamic, "_get_existing_tables", lambda: [TestModel._meta.db_table])
    monkeypatch.setattr(builder_module.apps, "get_models", lambda: [TestModel])
    captured = {}
    monkeypatch.setattr(builder_module, "register_model_routes", lambda **kwargs: captured.update(kwargs))
    dynamic._register_all_models_sync()
    assert captured["permission_policy"] is policy
