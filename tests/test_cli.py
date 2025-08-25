from __future__ import annotations

import contextlib
import io

import pytest

from lazy_ninja.cli import main as main_mod
from lazy_ninja.cli import client_generator, startproject


def test_build_parser_accepts_valid_generate_client_args():
    parser = main_mod.build_parser()
    language = next(iter(client_generator.GENERATOR_CONFIG.keys()))
    args = parser.parse_args(["generate-client", language, "--settings", "myproj.settings"])
    assert args.cmd == "generate-client"
    assert args.language == language
    assert args.settings == "myproj.settings"


def test_build_parser_rejects_invalid_language():
    parser = main_mod.build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["generate-client", "not-a-language", "--settings", "s"])
    assert exc.value.code == 2


def test_main_generate_client_requires_schema_or_settings_and_errors(monkeypatch):
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        with pytest.raises(SystemExit) as exc:
            main_mod.main(["generate-client", "python"]) 
    assert exc.value.code == 2 or exc.value.code == 1
    assert "either --schema or --settings must be provided" in buf.getvalue()


def test_main_generate_client_calls_handle_generate_client(monkeypatch):
    called = {}

    def fake_handle(args):
        called["args"] = args

    monkeypatch.setattr(client_generator, "handle_generate_client", fake_handle)

    language = next(iter(client_generator.GENERATOR_CONFIG.keys()))
    main_mod.main(["generate-client", language, "--settings", "myproj.settings", "--output", "dest"])

    assert "args" in called
    assert called["args"].settings == "myproj.settings"
    assert called["args"].language == language
    assert called["args"].output == "dest"


def test_main_startproject_invokes_startproject_command(monkeypatch):
    called = {}

    def fake_startproject(name, directory, title):
        called["called_with"] = (name, directory, title)

    monkeypatch.setattr(startproject, "startproject_command", fake_startproject)
    main_mod.main(["init", "myproj", "target_dir", "--title", "API Title"])

    assert "called_with" in called
    assert called["called_with"] == ("myproj", "target_dir", "API Title")


def test_main_prints_help_when_no_args(capfd):
    main_mod.main([])
    out, err = capfd.readouterr()
    assert "Lazy Ninja CLI" in out or "Generate client code" in out
