import pytest
from django.test import Client

from lazy_ninja.builder import ExclusionConfig

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
