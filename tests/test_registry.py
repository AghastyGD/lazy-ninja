import sys

from django.apps import apps

from lazy_ninja.registry import ModelRegistry, controller_for


def reset_registry(monkeypatch):
    monkeypatch.setattr(ModelRegistry, "_controllers", {})
    monkeypatch.setattr(ModelRegistry, "_discovered", True)


def test_register_and_get_controller(monkeypatch):
    reset_registry(monkeypatch)

    class DummyController:
        pass

    ModelRegistry.register_controller("TestModel", DummyController)
    assert ModelRegistry.get_controller("TestModel") is DummyController
    assert ModelRegistry.get_controller("unknown") is None


def test_controller_for_decorator_registers(monkeypatch):
    reset_registry(monkeypatch)

    @controller_for("Widget")
    class WidgetController:
        pass

    assert ModelRegistry.get_controller("Widget") is WidgetController


def test_discover_controllers_imports_modules(tmp_path, monkeypatch):
    reset_registry(monkeypatch)
    monkeypatch.setattr(ModelRegistry, "_discovered", False)

    package_dir = tmp_path / "sample_app"
    controllers_dir = package_dir / "controllers"
    controllers_dir.mkdir(parents=True)

    (package_dir / "__init__.py").write_text("")
    (controllers_dir / "__init__.py").write_text("")
    (controllers_dir / "widgets.py").write_text("registered = True\n")

    monkeypatch.syspath_prepend(str(tmp_path))

    class StubAppConfig:
        name = "sample_app"
        path = str(package_dir)

    monkeypatch.setattr(apps, "get_app_configs", lambda: [StubAppConfig])

    try:
        ModelRegistry.discover_controllers()
        assert ModelRegistry._discovered is True
        assert "sample_app.controllers.widgets" in sys.modules
    finally:
        sys.modules.pop("sample_app", None)
        sys.modules.pop("sample_app.controllers", None)
        sys.modules.pop("sample_app.controllers.widgets", None)
