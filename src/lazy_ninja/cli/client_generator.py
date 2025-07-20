import os
import sys
import subprocess
import argparse
import importlib
from pathlib import Path

GENERATOR_CONFIG = {
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
    

def main():
    parser = argparse.ArgumentParser(
        prog="lazy-ninja",
        description=(
        "🌀 Lazy Ninja CLI\n\n"
        "Generate client code and SDKs from your Django + Ninja API schema.\n\n"
        "Supports generating frontend clients (e.g., TypeScript for React) as well as backend SDKs\n"
        "for server-to-server communication or internal services.\n\n"
        "Example usage:\n"
        "  lazy-ninja generate-client typescript \\\n"
        "    --settings myproject.settings \\\n"
        "    --api-module myproject.api \\\n"
        "    --output ./client.ts"
    ),
        epilog="🐛 Report issues at: https://github.com/AghastyGD/lazy-ninja/issues",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    sub = parser.add_subparsers(dest="cmd")

    gen = sub.add_parser(
        "generate-client",
        help="Generate client code from OpenAPI schema",
        description=(
            "Generate client code from the OpenAPI schema exposed by your Django Ninja API.\n\n"
            "Supports multiple languages. You must provide your Django settings module and\n"
            "the path to the module where your `api = NinjaAPI()` instance is defined."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    gen.add_argument(
        "language",
        choices=list(GENERATOR_CONFIG.keys()),
        help="Target language for client code (e.g. typescript, python)"
    )
    gen.add_argument(
        "--settings",
        required=True,
        help="Django settings module (e.g. myproject.settings)"
    )
    gen.add_argument(
        "--api-module",
        default="settings.api",
        help="Module path where your `api = NinjaAPI()` is defined (default: settings.api)"
    )
    gen.add_argument(
        "--output",
        default="./client",
        help="Output file or folder (e.g. ./client.ts)"
    )

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    setup_django(args.settings)
    schema_file = Path(".lazy_ninja_openapi.json")
    dump_openapi(args.api_module, "api", schema_file)
    generate_client(schema_file, args.language, args.output)
    schema_file.unlink(missing_ok=True)
    
    
if __name__ == "__main__":
    main()
    

    