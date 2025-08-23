
from __future__ import annotations

import subprocess
import sys

import pytest

from lazy_ninja.cli import startproject as sp


def test_find_project_package_nested_layout(tmp_path):
    """
    layout:
    tmp/project_name/project_name/settings.py  -> should return tmp/project_name/project_name
    """
    root = tmp_path
    project_name = "myproj"
    p = root / project_name / project_name
    p.mkdir(parents=True)
    settings = p / "settings.py"
    settings.write_text("# settings")
    found = sp._find_project_package(root, project_name)
    assert found == p


def test_find_project_package_flat_layout(tmp_path):
    """
    layout:
    tmp/project_name/settings.py  -> should return tmp/project_name
    """
    root = tmp_path
    project_name = "myproj"
    p = root / project_name
    p.mkdir(parents=True)
    settings = p / "settings.py"
    settings.write_text("# settings")
    found = sp._find_project_package(root, project_name)
    assert found == p


def test_find_project_package_root_settings(tmp_path):
    """
    layout:
    tmp/settings.py -> should return tmp
    """
    root = tmp_path
    settings = root / "settings.py"
    settings.write_text("# settings")
    found = sp._find_project_package(root, "anyname")
    assert found == root


def test_find_project_package_multiple_matches_prefers_project_name(tmp_path):
    """
    Create two settings.py files; one whose parent matches project_name should be chosen.
    """
    root = tmp_path
    (root / "a").mkdir()
    (root / "a" / "settings.py").write_text("# a settings")
    (root / "myproj").mkdir()
    (root / "myproj" / "settings.py").write_text("# myproj settings")

    found = sp._find_project_package(root, "myproj")
    assert found.name == "myproj"


def test_find_project_package_no_matches_raises(tmp_path):
    with pytest.raises(RuntimeError):
        sp._find_project_package(tmp_path, "nonexistent")


def test_run_django_startproject_uses_django_admin_when_available(monkeypatch):
    calls = {}

    monkeypatch.setattr(sp.shutil, "which", lambda name: "/usr/bin/django-admin")

    def fake_run(cmd, check=False):
        calls["cmd"] = cmd
        calls["check"] = check
        class R: pass
        return R()

    monkeypatch.setattr(sp.subprocess, "run", fake_run)

    sp._run_django_startproject("myproj", "targetdir")
    assert calls["cmd"][0] == "django-admin"
    assert calls["cmd"][1] == "startproject"
    assert calls["cmd"][2] == "myproj"
    assert "targetdir" in calls["cmd"]


def test_run_django_startproject_falls_back_to_python_module(monkeypatch):
    calls = {}
    monkeypatch.setattr(sp.shutil, "which", lambda name: None)

    def fake_run(cmd, check=False):
        calls["cmd"] = cmd
        calls["check"] = check
        class R: pass
        return R()

    monkeypatch.setattr(sp.subprocess, "run", fake_run)

    sp._run_django_startproject("myproj", "targetdir")
    assert calls["cmd"][0] == sys.executable
    assert calls["cmd"][1] == "-m"
    assert calls["cmd"][2] == "django"
    assert "startproject" in calls["cmd"]


def test_scaffold_creates_api_and_appends_settings(tmp_path, capsys):
    root = tmp_path
    project_name = "myproj"
    pkg = root / project_name / project_name
    pkg.mkdir(parents=True)
    settings_file = pkg / "settings.py"
    settings_file.write_text("# base settings\n")

    sp._scaffold_lazy_ninja(root, project_name, title="My API Title")

    api = pkg / "api.py"
    assert api.exists()
    content = api.read_text()
    assert "NinjaAPI" in content
    assert "My API Title" in content

    settings_text = settings_file.read_text()
    assert "Lazy Ninja scaffold" in settings_text


def test_scaffold_skips_existing_api(tmp_path, capsys):
    root = tmp_path
    project_name = "myproj"
    pkg = root / project_name / project_name
    pkg.mkdir(parents=True)
    settings_file = pkg / "settings.py"
    settings_file.write_text("# settings\n")

    api_file = pkg / "api.py"
    api_file.write_text("# existing api\n")

    sp._scaffold_lazy_ninja(root, project_name, title=None)
    assert api_file.read_text() == "# existing api\n"


def test_startproject_command_handles_django_start_failure(monkeypatch):
    def raise_called(name, target=None):
        raise subprocess.CalledProcessError(returncode=3, cmd="failcmd")

    monkeypatch.setattr(sp, "_run_django_startproject", raise_called)

    with pytest.raises(SystemExit) as exc:
        sp.startproject_command("myproj", directory="targetdir", title=None)
    assert exc.value.code == 3


def test_startproject_command_scaffold_failure_prints_warning(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sp, "_run_django_startproject", lambda name, target=None: None)
    def raise_exc(root, name, title):
        raise RuntimeError("boom")
    monkeypatch.setattr(sp, "_scaffold_lazy_ninja", raise_exc)

    sp.startproject_command("myproj", directory=str(tmp_path), title="T")

    out = capsys.readouterr().out
    assert "Project created but failed to add Lazy Ninja scaffold" in out or "failed to add Lazy Ninja scaffold" in out
