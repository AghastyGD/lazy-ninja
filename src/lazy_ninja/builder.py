import asyncio
import inflect
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Set, Dict, List, Type, Union, Any

from django.db import connection
from django.apps import apps

from ninja import NinjaAPI, Schema

from .core import register_model_routes
from .utils import generate_schema
from .helpers import to_kebab_case
from .pagination import get_pagination_strategy
from .file_upload import FileUploadConfig, detect_file_fields

p = inflect.engine()

class ExclusionConfig:
    """
    Flexible configuration for excluding models from routes registration.
    
    Supports multiple ways of specifying exclusions with a unified approach.
    """
    def __init__(
        self,
        exclude: Optional[Dict[str, Union[bool, Set[str], Any]]] = None
    ):
        """
        Initialize exclusion configuration.
        
        Args:
            exclude: configuration for model/app exclusions:
                {
                    'app_name': True, # Exclude all models from this app
                    'app_name': {'ModelName1', 'ModelName2'}, # Exclude specific models from this app
                    'app_name': None, # No exclusions for this app
                }
        By default, the system apps are excluded: auth, contenttypes, admin, sessions
        """
        self.excluded = {
            'auth': True,
            'contenttypes': True,
            'admin': True,
            'sessions': True
        }
        
        if exclude:
            self.excluded.update(exclude)
            
    def should_exclude_model(self, model) -> bool:
        """
        Determine if a model should be excluded from route registration.
        
        Args:
            model: Django model to check for exclusion.
        
        Returns:
            bool: True if the model should be excluded, False otherwise.
        """
        app_label = model._meta.app_label
        model_name = model.__name__
        
        app_config = self.excluded.get(app_label)
        
        if app_config is True:
            return True
        
        if app_config is None:
            return False
        
        if isinstance(app_config, set):
            return model_name in app_config
        
        return False

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
        exclude: Optional[Dict[str, Union[bool, Set[str], Any]]] = None,
        schema_config: Optional[Dict[str, Dict[str, List[str]]]] = None,
        custom_schemas: Optional[Dict[str, Dict[str, Type[Schema]]]] = None,
        pagination_type: Optional[str] = None,
        file_fields: Optional[Dict[str, List[str]]] = None,
        auto_detect_files: bool = True,
        auto_multipart: bool = True,
        use_multipart: Optional[Dict[str, Dict[str, bool]]] = None,
        is_async: bool = True
    ):
        """
        Initializes the DynamicAPI instance.

        Args:
            api: The NinjaAPI instance.
            exclude: Configuration for model/app exclusions.
            schema_config: Dictionary mapping model names to schema configurations
                           (e.g., exclude fields and optional fields).
            custom_schemas: Dictionary mapping model names to custom Pydantic Schema classes for
                            list, detail, create, and update operations.  The dictionary should have the structure:
                            `{"ModelName": {"list": ListSchema, "detail": DetailSchema, "create": CreateSchema, "update": UpdateSchema}}`
                            If a schema is not provided for a specific operation, the default generated schema will be used.
            pagination_type: Type of pagination to use ('limit-offset' or 'page-number').
                           If None, uses NINJA_PAGINATION_CLASS from settings.
            file_fields: Dictionary mapping model names to lists of file field names
                         (e.g., {"Product": ["image", "document"]}).
            auto_detect_files: Whether to automatically detect file fields in models.
            auto_multipart: Whether to automatically use multipart for models with file fields.
            use_multipart: Dictionary specifying which models should use multipart/form-data
                           (e.g., {"Product": {"create": True, "update": True}}).
            is_async: Whether to use async routes (default: True).
               
        Pagination Configuration:
            The pagination can be configured in three ways (in order of precedence):
            1. pagination_type parameter in DynamicAPI
            2. NINJA_PAGINATION_CLASS in Django settings
            3. Default to LimitOffsetPagination (if no settings or parameter are provided)
            
            The page size is configured via NINJA_PAGINATION_PER_PAGE in settings.
        """
        self.api = api
        self.exclusion_config = ExclusionConfig(exclude=exclude)
        self.schema_config = schema_config or {}
        self.custom_schemas = custom_schemas or {}
        self.is_async = is_async
        self.pagination_strategy = get_pagination_strategy(pagination_type=pagination_type)
       
        self.file_fields = file_fields or {}
        self.use_multipart = use_multipart or {}
        self.auto_detect_files = auto_detect_files
        self.auto_multipart = auto_multipart
        self.file_upload_config = FileUploadConfig(
            file_fields=self.file_fields
        )
        
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

            if self.exclusion_config.should_exclude_model(model):
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

            detected_single_file_fields = []
            detected_multiple_file_fields = []
            
            if self.auto_detect_files:
                detected_single_file_fields, detected_multiple_file_fields = detect_file_fields(model)
                
            model_file_fields = list(set(self.file_fields.get(model_name, []) + detected_single_file_fields))
            
            if model_file_fields:
                self.file_upload_config.file_fields[model_name] = model_file_fields
                
            if detected_multiple_file_fields:
                existing = self.file_upload_config.multiple_file_fields.get(model_name, [])
                self.file_upload_config.multiple_file_fields[model_name] = list(set(existing + detected_multiple_file_fields))
            
            use_multipart_create = self.use_multipart.get(model_name, {}).get("create", False)
            use_multipart_update = self.use_multipart.get(model_name, {}).get("update", False)
        
            has_any_file_fields = bool(model_file_fields) or bool(detected_multiple_file_fields)
            if self.auto_multipart and has_any_file_fields:
                use_multipart_create = True
                use_multipart_update = True
                
            register_model_routes(
                api=self.api,
                model=model,
                base_url=f"/{p.plural(to_kebab_case(model_name))}",
                list_schema=list_schema,
                detail_schema=detail_schema,
                create_schema=create_schema,
                update_schema=update_schema,
                pagination_strategy=self.pagination_strategy,
                file_upload_config=self.file_upload_config if model_file_fields else None,
                use_multipart_create=use_multipart_create,
                use_multipart_update=use_multipart_update,
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
            
    def init(self) -> None:
        """
        Initializes the DynamicAPI.
        
        This method acts as the public initializer for the library. It internally calls
        register_all_models() to scan models and register their corresponding CRUD routes.
        """
        self.register_all_models()