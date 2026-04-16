from pathlib import Path

import tomllib


ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_declares_dev_dependency_group() -> None:
    pyproject_path = ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert "dependency-groups" in data
    assert "dev" in data["dependency-groups"]
    assert any(dep.startswith("pytest") for dep in data["dependency-groups"]["dev"])


def test_pyproject_has_requires_python_for_uv_resolution() -> None:
    pyproject_path = ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert data["project"]["requires-python"] == ">=3.11"


def test_uv_lock_exists() -> None:
    assert (ROOT / "uv.lock").exists()


def test_uv_lock_has_python_requirement() -> None:
    lockfile = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert "requires-python" in lockfile


def test_uv_lock_tracks_project_and_dev_dependencies() -> None:
    lockfile = (ROOT / "uv.lock").read_text(encoding="utf-8")

    assert 'name = "lazy-ninja"' in lockfile
    assert "[package.dev-dependencies]" in lockfile
    assert 'name = "pytest"' in lockfile


def test_github_actions_uses_uv_flow() -> None:
    workflow = (ROOT / ".github" / "workflows" / "python-publish.yml").read_text(encoding="utf-8")

    assert "astral-sh/setup-uv@v6" in workflow
    assert "uv sync --group dev --all-extras --frozen" in workflow
    assert "uv run pytest" in workflow
    assert "uv build" in workflow
    assert "pip install -r requirements.dev.txt" not in workflow


def test_readme_documents_pip_and_uv_install_options() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "pip install lazy-ninja" in readme
    assert "uv add lazy-ninja" in readme


def test_legacy_requirements_files_do_not_self_reference_package_name() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    requirements_dev = (ROOT / "requirements.dev.txt").read_text(encoding="utf-8").splitlines()

    assert "-e ." in requirements
    assert "-e ." in requirements_dev
    assert "lazy-ninja" not in requirements
    assert "lazy-ninja" not in requirements_dev
