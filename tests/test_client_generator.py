from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
import importlib

import lazy_ninja.cli.client_generator as cg


# -------------------------
# Helpers
# -------------------------
def make_args(**kwargs) -> SimpleNamespace:
    """Return a SimpleNamespace suitable for handle_generate_client."""
    defaults = {
        "language": "python",
        "output": "out",
        "settings": None,
        "api_module": "settings.api",
        "api_var": "api",
        "schema": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_generate_client_builds_correct_command_and_calls_subprocess(tmp_path, monkeypatch, capsys):
    schema = tmp_path / "schema.json"
    schema.write_text("{}")

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        class R:
            returncode = 0
        return R()

    monkeypatch.setattr(cg.subprocess, "run", fake_run)

    cg.generate_client(schema, "python", "my-output")

    assert captured["cmd"][0:4] == ["openapi-generator-cli", "generate", "-i", str(schema)]
    assert "-g" in captured["cmd"]
    assert "python" in captured["cmd"]
    assert "-o" in captured["cmd"]
    
    out = capsys.readouterr().out
    assert "Client (python) generated at my-output" in out


def test_generate_client_subprocess_failure_raises_systemexit(monkeypatch, tmp_path, capsys):
    schema = tmp_path / "schema.json"
    schema.write_text("{}")

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 7
        return R()

    monkeypatch.setattr(cg.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        cg.generate_client(schema, "python", "outdir")
    assert exc.value.code == 7
    out = capsys.readouterr().out
    assert "Generator failed" in out


def test_generate_client_invalid_language_raises(monkeypatch, tmp_path):
    schema = tmp_path / "schema.json"
    schema.write_text("{}")
    with pytest.raises(TypeError):
        cg.generate_client(schema, "not-a-language", "outdir")


def test_handle_generate_client_schema_missing_exits(tmp_path, capsys):
    args = make_args(schema=str(tmp_path / "nope.json"))
    with pytest.raises(SystemExit) as exc:
        cg.handle_generate_client(args)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Schema file not found" in out


def test_handle_generate_client_with_provided_schema_calls_generate_client(monkeypatch, tmp_path):
    schema = tmp_path / "schema.json"
    schema.write_text("{}")

    called = {}

    def fake_generate_client(schema_path, language, output):
        called["args"] = (schema_path, language, output)

    monkeypatch.setattr(cg, "generate_client", fake_generate_client)

    args = make_args(schema=str(schema), language="python", output="dest")

    cg.handle_generate_client(args)

    assert "args" in called
    schema_path, language, output = called["args"]
    assert schema_path == Path(schema)
    assert language == "python"
    assert output == "dest"
   
    assert schema.exists()


def test_handle_generate_client_no_schema_success(monkeypatch, tmp_path):
    oldcwd = Path.cwd()
    try:
        os.chdir(tmp_path)

        monkeypatch.setattr(cg, "setup_django", lambda s: None)

        def fake_dump_openapi(api_module, api_var, out_file: Path):
            out_file.write_bytes(b'{"openapi":"3.0.0"}')

        monkeypatch.setattr(cg, "dump_openapi", fake_dump_openapi)

        called = {}
        def fake_generate_client(schema_path, language, output):
            called["called_with"] = (schema_path, language, output)

        monkeypatch.setattr(cg, "generate_client", fake_generate_client)

        args = make_args(schema=None, settings="myproj.settings", api_module="m.api", api_var="api", language="python", output="outdir")

        cg.handle_generate_client(args)

        assert "called_with" in called
        schema_path, language, output = called["called_with"]
        assert schema_path == Path(".lazy_ninja_openapi.json")
        assert language == "python"
        assert output == "outdir"

        assert not Path(".lazy_ninja_openapi.json").exists()
    finally:
        os.chdir(oldcwd)


def test_handle_generate_client_setup_django_failure(monkeypatch, capsys):
    def boom(settings):
        raise RuntimeError("cannot import settings")
    monkeypatch.setattr(cg, "setup_django", boom)

    args = make_args(schema=None, settings="broken.settings")
    with pytest.raises(SystemExit) as exc:
        cg.handle_generate_client(args)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Failed to setup Django" in out


def test_handle_generate_client_dump_module_not_found(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cg, "setup_django", lambda s: None)

    def raise_modu(api_module, api_var, out_file):
        raise ModuleNotFoundError("missingmod")
    monkeypatch.setattr(cg, "dump_openapi", raise_modu)

    args = make_args(schema=None, settings="some.settings", api_module="m.api", api_var="api")
    with pytest.raises(SystemExit) as exc:
        cg.handle_generate_client(args)
    assert exc.value.code == 1
    out = capsys.readouterr().out

    assert "Missing module" in out


def test_handle_generate_client_dump_other_exception(monkeypatch, capsys):
    monkeypatch.setattr(cg, "setup_django", lambda s: None)

    def raise_other(api_module, api_var, out_file):
        raise RuntimeError("boom")
    monkeypatch.setattr(cg, "dump_openapi", raise_other)

    args = make_args(schema=None, settings="some.settings", api_module="m.api", api_var="api")
    with pytest.raises(SystemExit) as exc:
        cg.handle_generate_client(args)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Failed to generate schema" in out


from types import ModuleType

def test_setup_django_calls_django_setup(monkeypatch, tmp_path):
    """
    Ensure setup_django imports `django` and calls django.setup(),
    and that DJANGO_SETTINGS_MODULE is set.
    """
    calls = {"setup": False}
    fake_django = ModuleType("django")
    def fake_setup():
        calls["setup"] = True
    fake_django.setup = fake_setup

    monkeypatch.setitem(sys.modules, "django", fake_django)

    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)

    cg.setup_django("myproject.settings")

    assert os.environ.get("DJANGO_SETTINGS_MODULE") == "myproject.settings"
    assert calls["setup"] is True


def test_dump_openapi_writes_file(monkeypatch, tmp_path):
    """
    Simulate the full dump_openapi flow by injecting fake modules:
      - django.test.RequestFactory
      - ninja.openapi.views.openapi_json
      - importlib.import_module returning a module that contains the api var
    The function should write bytes to the out_file.
    """
    fake_mod = SimpleNamespace()
    fake_api_obj = object()
    setattr(fake_mod, "api", fake_api_obj)
    
    monkeypatch.setattr(importlib, "import_module", lambda name: fake_mod)

    class FakeRequestFactory:
        def __init__(self):
            pass
        def get(self, path):
            return "fake-request"

    fake_django_test = ModuleType("django.test")
    fake_django_test.RequestFactory = FakeRequestFactory
    monkeypatch.setitem(sys.modules, "django.test", fake_django_test)

    class FakeResp:
        def __init__(self, b):
            self.content = b

    def fake_openapi_json(req, api):
        return FakeResp(b'{"openapi":"3.0.0"}')

    ninja = ModuleType("ninja")
    ninja_openapi = ModuleType("ninja.openapi")
    ninja_views = ModuleType("ninja.openapi.views")
    ninja_views.openapi_json = fake_openapi_json

    monkeypatch.setitem(sys.modules, "ninja", ninja)
    monkeypatch.setitem(sys.modules, "ninja.openapi", ninja_openapi)
    monkeypatch.setitem(sys.modules, "ninja.openapi.views", ninja_views)

    out_file = tmp_path / "out.json"
    cg.dump_openapi("some.module", "api", out_file)

    assert out_file.exists()
    assert out_file.read_bytes() == b'{"openapi":"3.0.0"}'