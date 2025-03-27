import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Set, Dict, List, Type

from django.db import connection
from django.apps import apps

from ninja import NinjaAPI, Schema

from . import register_model_routes
from .utils import generate_schema
from .helpers import to_kebab_case
from .pagination import get_pagination_strategy

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
        pagination_type: Optional[str] = None,
        is_async: bool = True
    ):
        """
        Initializes the DynamicAPI instance.

        Args:
            api: The NinjaAPI instance.
            is_async: Whether to use async routes (default: True).
            excluded_apps: Set of Django app labels to exclude (default: {"auth", "contenttypes", "admin", "sessions"}).
            schema_config: Dictionary mapping model names to schema configurations
                           (e.g., exclude fields and optional fields).
            custom_schemas: Dictionary mapping model names to custom Pydantic Schema classes for
                            list, detail, create, and update operations.  The dictionary should have the structure:
                            `{"ModelName": {"list": ListSchema, "detail": DetailSchema, "create": CreateSchema, "update": UpdateSchema}}`
                            If a schema is not provided for a specific operation, the default generated schema will be used.
            pagination_type: Type of pagination to use ('limit-offset' or 'page-number').
                           If None, uses NINJA_PAGINATION_CLASS from settings.
                           
        Pagination Configuration:
            The pagination can be configured in three ways (in order of precedence):
            1. pagination_type parameter in DynamicAPI
            2. NINJA_PAGINATION_CLASS in Django settings
            3. Default to LimitOffsetPagination (if no settings or parameter are provided)
            
            The page size is configured via NINJA_PAGINATION_PER_PAGE in settings.
        """
        self.api = api
        self.excluded_apps = excluded_apps or {"auth", "contenttypes", "admin", "sessions"}
        self.schema_config = schema_config or {}
        self.custom_schemas = custom_schemas or {}
        self.is_async = is_async
        self.pagination_strategy = get_pagination_strategy(pagination_type=pagination_type)
        self._already_registered = False
        
    @staticmethod
    def _get_existing_tables():
        with connection.cursor() as cursor:
            return connection.introspection.table_names(cursor)
    
    def _register_all_models_sync(self) -> None:
        existing_tables = self._get_existing_tables()
            
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
                update_schema = generate_schema(model, exclude=exclude_fields, optional_fields=optional_fields, update=True)

            register_model_routes(
                api=self.api,
                model=model,
                base_url=f"/{to_kebab_case(model_name)}",
                list_schema=list_schema,
                detail_schema=detail_schema,
                create_schema=create_schema,
                update_schema=update_schema,
                pagination_strategy=self.pagination_strategy,
                is_async=getattr(self, 'is_async', True)
            )
            
    def register_all_models(self) -> None:
        """
        Scans Django models and registers routes.

        Excludes models from specified apps.  Uses custom schemas if provided;
        otherwise, generates schemas based on schema_config or defaults.
        """
        if self._already_registered:
            return
        
        self._already_registered = True
        try:
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self._register_all_models_sync)
                future.result()
                
        except RuntimeError:
            self._register_all_models_sync()