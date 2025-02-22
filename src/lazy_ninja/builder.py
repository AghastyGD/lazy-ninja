from django.apps import apps
from ninja import NinjaAPI, Schema
from typing import Optional, Set, Dict, List, Type
from .utils import generate_schema
from . import register_model_routes
from django.db import connection

class DynamicAPI:
    """
    Dynamically registers CRUD routes for Django models using Django Ninja.

    This class scans installed Django models (excluding those from specified apps)
    and automatically creates/uses Pydantic schemas for listing, detailing,
    creating, and updating models. It registers these routes with Ninja.
    """

    def __init__(
        self,
        api: NinjaAPI,
        excluded_apps: Optional[Set[str]] = None,
        schema_config: Optional[Dict[str, Dict[str, List[str]]]] = None,
        custom_schemas: Optional[Dict[str, Dict[str, Type[Schema]]]] = None,
    ):
        """
        Initializes the DynamicAPI instance.

        Args:
            api: The NinjaAPI instance.
            excluded_apps: Set of Django app labels to exclude (default: {"auth", "contenttypes", "admin", "sessions"}).
            schema_config: Dictionary mapping model names to schema configurations
                           (e.g., exclude fields and optional fields).
            custom_schemas: Dictionary mapping model names to custom Pydantic Schema classes for
                            list, detail, create, and update operations.  The dictionary should have the structure:
                            `{"ModelName": {"list": ListSchema, "detail": DetailSchema, "create": CreateSchema, "update": UpdateSchema}}`
                            If a schema is not provided for a specific operation, the default generated schema will be used.
        """
        self.api = api
        self.excluded_apps = excluded_apps or {"auth", "contenttypes", "admin", "sessions"}
        self.schema_config = schema_config or {}
        self.custom_schemas = custom_schemas or {}

    def register_all_models(self) -> None:
        """
        Scans Django models and registers routes.

        Excludes models from specified apps.  Uses custom schemas if provided;
        otherwise, generates schemas based on schema_config or defaults.
        """
        
        with connection.cursor() as cursor:
            existing_tables = connection.introspection.table_names(cursor)
            
        for model in apps.get_models():
            app_label = model._meta.app_label
            model_name = model.__name__

            if app_label in self.excluded_apps:
                continue
            
            if model._meta.db_table not in existing_tables:
                continue

            custom_schema = self.custom_schemas.get(model_name)

            if custom_schema:
                list_schema = custom_schema.get("list") or generate_schema(model)  # Fallback to generated
                detail_schema = custom_schema.get("detail") or generate_schema(model) # Fallback to generated
                create_schema = custom_schema.get("create") # No fallback, required for create
                update_schema = custom_schema.get("update") # No fallback, required for update

            else:
                model_config = self.schema_config.get(model_name, {})
                exclude_fields = model_config.get("exclude", [
                    "id", 
                    "created_at", 
                    "updated_at", 
                    "deleted_at"
                ])
                
                optional_fields = model_config.get("optional_fields", [])

                list_schema = generate_schema(model)
                detail_schema = generate_schema(model)
                create_schema = generate_schema(model, exclude=exclude_fields, optional_fields=optional_fields)
                update_schema = generate_schema(model, exclude=exclude_fields, optional_fields=optional_fields)

            register_model_routes(
                api=self.api,
                model=model,
                base_url=f"/{model.__name__.lower()}",
                list_schema=list_schema,
                detail_schema=detail_schema,
                create_schema=create_schema,
                update_schema=update_schema,
            )