from __future__ import annotations
import subprocess
from pathlib import Path
import textwrap
import shutil
import sys

def _find_project_package(project_root: Path, project_name: str) -> Path:
    """
    Find the Django project package directory based on the project name.
    This searches for the settings.py file in common project structures.
    project_root: directory that contains the created project package (where package folder lives)
    project_name: name of the Django project (used to locate settings.py)
    Returns the directory containing settings.py.
    """
    project_root = project_root.resolve()
    
    p = project_root / project_name / project_name / "settings.py"
    if p.exists():
        return p.parent

    p = project_root / project_name / "settings.py"
    if p.exists():
        return p.parent

    p = project_root / "settings.py"
    if p.exists():
        return project_root

    matches = list(project_root.rglob("settings.py"))
    if not matches:
        raise RuntimeError(
            f"Could not locate Django project package under {project_root}. "
            "Expected to find a directory containing settings.py (e.g. project_name/settings.py)."
        )

    for m in matches:
        if m.parent.name == project_name:
            return m.parent

    return matches[0].parent

def _run_django_startproject(name: str, target: str | None = None):
    """
    Run `django-admin startproject <name> [<target>]`.
    Falls back to `python -m django startproject` if `django-admin` is not in PATH.
    """
    if shutil.which("django-admin"):
        cmd = ["django-admin", "startproject", name]
        if target:
            cmd.append(target)
    else:
        print("[lazy-ninja] 'django-admin' not found on PATH, using 'python -m django startproject' fallback.")
        cmd = [sys.executable, "-m", "django", "startproject", name]
        if target:
            cmd.append(target)

    subprocess.run(cmd, check=True)


def _scaffold_lazy_ninja(project_root: Path, project_name: str, title: str | None = None):
    """
    Create api.py inside the project package and append instructions to settings.py.

    project_root: directory that contains the created project package (where package folder lives)
    """
    pkg_dir = _find_project_package(project_root, project_name) 
    
    print("outer_dir candidate:", project_root / project_name)
    print("package_dir (found):", pkg_dir)
    print("api target:", pkg_dir / "api.py")
    print("setings file:", pkg_dir / "settings.py")
    
    if not pkg_dir.exists():
        raise RuntimeError(f"Project package not found at expected location: {pkg_dir}")

    api_py = pkg_dir / "api.py"
    
    if api_py.exists():
        print(f"[lazy-ninja] ⚠️ api.py already exists at {api_py}, skipping creation.")
    else:
        api_content = textwrap.dedent(f"""\
            from ninja import NinjaAPI
            from lazy_ninja.builder import DynamicAPI

            # API title: {title or project_name}
            api = NinjaAPI(title="{title or project_name}")

            auto_api = DynamicAPI(
                api,
                is_async=True,
            )

            auto_api.init()
        """)
        api_py.write_text(api_content, encoding="utf-8")
        print(f"[lazy-ninja] ✅ Wrote {api_py}")
        
    settings_file = pkg_dir / "settings.py"
    
    if settings_file.exists():
        with settings_file.open("a", encoding="utf-8") as f:
            f.write("\n\n# === Lazy Ninja scaffold ===\n")
            f.write("# A sample NinjaAPI has been created in api.py\n")
            f.write("# To expose it, add something like the following to your project's urls.py:\n")
            f.write("#\n")
            f.write(f"#   from django.urls import path, include\n")
            f.write(f"#   from {project_name}.api import api as ninja_api\n")
            f.write("#\n")
            f.write("#   urlpatterns = [\n")
            f.write("#       path('api/', ninja_api.urls),\n")
            f.write("#       # ... other patterns\n")
            f.write("#   ]\n")
            f.write("#\n# Install django-ninja (pip install django-ninja) and follow the README for more examples.\n")


def startproject_command(name: str, directory: str | None = None, title: str | None = None):
    """
    Create a Django project and always add a minimal Lazy Ninja scaffold (api.py + settings note).
    """
    try:
        _run_django_startproject(name, directory)
    except subprocess.CalledProcessError as e:
        print(f"[lazy-ninja] ❌ django startproject failed: {e}")
        sys.exit(e.returncode)

    project_root = Path(directory).resolve() if directory else Path(".").resolve()

    try:
        _scaffold_lazy_ninja(project_root, name, title)
        print(f"[lazy-ninja] ✅ Project '{name}' created with Lazy Ninja scaffold at {project_root / name}")
    except Exception as e:
        print(f"[lazy-ninja] ⚠️ Project created but failed to add Lazy Ninja scaffold: {e}")
        print("You can manually add api.py as shown in the README.")
