from __future__ import annotations
import argparse
from pathlib import Path
from . import client_generator, startproject

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lazy-ninja",
        description="🌀 Lazy Ninja CLI - tools for generating clients and projects.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd")
    
    gen = sub.add_parser("generate-client", help="Generate client code from OpenAPI schema")
    gen.add_argument("language", choices=list(client_generator.GENERATOR_CONFIG.keys()))
    gen.add_argument("--output", default="./client", help="Output dir or file")
    gen.add_argument("--settings", help="Django settings module (e.g. myproject.settings). Required unless --schema is provided.")
    gen.add_argument("--api-module", default="settings.api", help="Module path where `api = NinjaAPI()` is defined")
    gen.add_argument("--api-var", default="api", help="Name of the Ninja API variable in module (default: api)")
    gen.add_argument("--schema", type=Path, help="Path to pre-generated OpenAPI JSON (skip Django setup)")
    
    proj = sub.add_parser("init", help="Create a Django project scaffold preconfigured for Lazy Ninja")
    proj.add_argument("name", help="Project name")
    proj.add_argument("directory", nargs="?", default=None, help="Optional target directory (same semantics as django-admin)")
    proj.add_argument("--title", nargs="?", default=None, help="Optional API title")
    
    return parser

def main(argv: list[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    
    if args.cmd == "generate-client":
        if args.schema is None and not args.settings:
            parser.error("either --schema or --settings must be provided for generate-client")
        client_generator.handle_generate_client(args)
    elif args.cmd == "init":
        startproject.startproject_command(args.name, args.directory, args.title)
    else:
        parser.print_help()  