import os
import sys
import subprocess
import argparse
import importlib
from pathlib import Path

GENERATOR_CONFIG = {
    "javascript": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "javascript",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "typescript-types": {
        "cmd": ["npx", "openapi-typescript", "{schema}", "--output", "{out}"],
        "ext": "ts",
    },
    "dart": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "dart-dio",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "python": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "python",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "typescript-axios": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "typescript-axios",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "typescript-fetch": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "typescript-fetch",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "java": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "java",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "kotlin": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "kotlin",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "go": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "go",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "csharp": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "csharp",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "ruby": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "ruby",
            "-o", "{out_dir}"
        ],
        "ext": None
    },
    "swift5": {
        "cmd": [
            "openapi-generator-cli", "generate",
            "-i", "{schema}",
            "-g", "swift5",
            "-o", "{out_dir}"
        ],
        "ext": None
    }
}


def setup_django(settings_module: str):
    sys.path.insert(0, os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    
    import django
    django.setup()
    

def dump_openapi(api_module: str, api_var: str, out_file: Path):
    from django.test import RequestFactory
    from ninja.openapi.views import openapi_json
    
    mod = importlib.import_module(api_module)
    api = getattr(mod, api_var)
    
    req = RequestFactory().get("/api/openapi.json")
    resp = openapi_json(req, api)
    out_file.write_bytes(resp.content)
    

def generate_client(schema_path: Path, language: str, output: str):
    cfg = GENERATOR_CONFIG.get(language)

    cmd = [p.format(schema=str(schema_path), out=output, out_dir=output) for p in cfg["cmd"]]
    print(f"[LazyNinja] ▶ Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print(f"[LazyNinja] ❌ Generator failed.")
        sys.exit(proc.returncode)
    print(f"[LazyNinja] ✅ Client ({language}) generated at {output}")
    
def handle_generate_client(args):
    """
    args: namespace from argparse with attributes:
      - language, output, settings, api_module, schema (optional), api_var
    """
    schema_file = Path(args.schema) if getattr(args, "schema", None) else Path(".lazy_ninja_openapi.json")

    if getattr(args, "schema", None):
        if not schema_file.exists():
            print(f"[LazyNinja] ❌ Schema file not found: {schema_file}")
            sys.exit(1)
    else:
        try:
            setup_django(args.settings)
        except Exception as e:
            print("[LazyNinja] ❌ Failed to setup Django. Make sure your settings are importable.")
            print("Error:", e)
            sys.exit(1)

        try:
            dump_openapi(args.api_module, args.api_var, schema_file)
        except ModuleNotFoundError as e:
            print("[LazyNinja] ❌ Failed to import module while dumping OpenAPI schema.")
            print("Missing module:", e.name)
            print("Consider generating a schema file with your project dependencies installed, then pass --schema path/to/schema.json")
            sys.exit(1)
        except Exception as e:
            print("[LazyNinja] ❌ Failed to generate schema.")
            print("Error:", e)
            sys.exit(1)

    try:
        generate_client(schema_file, args.language, args.output)
    finally:
        if not getattr(args, "schema", None) and schema_file.exists():
            schema_file.unlink(missing_ok=True)