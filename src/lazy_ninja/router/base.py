from abc import ABC, abstractmethod
from typing import Type, Optional, List, Any

from django.db.models import Model
from ninja import Router, Schema, NinjaAPI

from ..pagination import BasePagination
from ..file_upload import FileUploadConfig


class BaseModelRouter(ABC):
    """
    Base class for model routers that handles shared configuration and wiring.

    Subclasses implement the actual route registration logic for sync/async patterns.
    """

    def __init__(
        self,
        api: NinjaAPI,
        model: Type[Model],
        base_url: str,
        list_schema: Type[Schema],
        detail_schema: Type[Schema],
        create_schema: Optional[Type[Schema]] = None,
        update_schema: Optional[Type[Schema]] = None,
        pagination_strategy: Optional[BasePagination] = None,
        file_upload_config: Optional[FileUploadConfig] = None,
        use_multipart_create: bool = False,
        use_multipart_update: bool = False,
        controller: Optional[Any] = None,
        **hooks
    ):
        """
        Initialize the base router with shared configuration.

        Args:
            api: NinjaAPI instance
            model: Django model class
            base_url: Base URL for the routes
            list_schema: Schema for list responses
            detail_schema: Schema for detail responses
            create_schema: Schema for create requests
            update_schema: Schema for update requests
            pagination_strategy: Strategy for pagination
            file_upload_config: Configuration for file uploads
            use_multipart_create: Whether to use multipart for create
            use_multipart_update: Whether to use multipart for update
            controller:
            **hooks: Hook functions (before_create, pre_list, etc.)
        """
        self.api = api
        self.model = model
        self.base_url = base_url
        self.list_schema = list_schema
        self.detail_schema = detail_schema
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.pagination_strategy = pagination_strategy
        self.file_upload_config = file_upload_config
        self.use_multipart_create = use_multipart_create
        self.use_multipart_update = use_multipart_update
        self.controller = controller

        self.pre_list = hooks.get('pre_list')
        self.before_create = hooks.get('before_create')
        self.after_create = hooks.get('after_create')
        self.before_update = hooks.get('before_update')
        self.after_update = hooks.get('after_update')
        self.before_delete = hooks.get('before_delete')
        self.after_delete = hooks.get('after_delete')
        self.custom_response = hooks.get('custom_response')

        self.model_name = model.__name__.lower()
        self.paginator_class = pagination_strategy.get_paginator() if pagination_strategy else None

        self.router = Router()

    @abstractmethod
    def register_list_route(self) -> None:
        """Register the list route."""
        pass

    @abstractmethod
    def register_detail_route(self) -> None:
        """Register the detail route."""
        pass

    @abstractmethod
    def register_create_route(self) -> None:
        """Register the create route."""
        pass

    @abstractmethod
    def register_update_route(self) -> None:
        """Register the update route."""
        pass

    @abstractmethod
    def register_delete_route(self) -> None:
        """Register the delete route."""
        pass

    
    def finalize(self) -> None:
        """
        Register all routes and add the router to the API.

        This method orchestrates the route registration process.
        """
        self.register_list_route()
        self.register_detail_route()

        if self.create_schema:
            self.register_create_route()

        if self.update_schema:
            self.register_update_route()
        
        self.register_delete_route()

        self.api.add_router(self.base_url, self.router)

    def get_operation_id(self, operation: str) -> str:
        """Generate operation ID for OpenAPI"""
        return f'{operation}_{self.model_name}'
    
    def get_tags(self) -> List[str]:
        """Get tags for route grouping."""
        return [self.model.__name__]

    def get_expand_fields_from_request(self, request) -> List[str]:
        """Read the `expand` query parameter and return a list of fields to expand."""
        expand_param = getattr(request, "GET", {}).get("expand") if hasattr(request, "GET") else None
        if not expand_param:
            setattr(request, "_lazy_ninja_expand_fields", [])
            setattr(request, "_lazy_ninja_router", self)
            return []

        fields = []
        for field in expand_param.split(","):
            field = field.strip()
            if not field:
                continue
            base = field.split(".", 1)[0]
            if base not in fields:
                fields.append(base)
        setattr(request, "_lazy_ninja_expand_fields", fields)
        setattr(request, "_lazy_ninja_router", self)
        return fields

    def apply_expand_queryset_hints(self, queryset, expand_fields):
        """Apply select_related for expanded foreign keys to avoid N+1 queries."""
        from django.db import models
        fk_fields = []
        for field_name in expand_fields:
            try:
                field = self.model._meta.get_field(field_name)
            except Exception:
                continue

            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                fk_fields.append(field_name)

        if fk_fields:
            queryset = queryset.select_related(*fk_fields)

        return queryset
    
