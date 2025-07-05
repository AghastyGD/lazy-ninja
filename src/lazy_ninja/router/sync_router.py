from typing import List, Any, Dict, Optional, Union

from django.shortcuts import get_object_or_404
from django.db.models import QuerySet
from ninja import Form
from ninja.pagination import paginate

from .base import BaseModelRouter
from ..handlers.response import SyncResponseHandler
from ..handlers.file_handler import SyncFileHandler
from ..utils.hooks import SyncHookExecutor
from ..utils.model import SyncModelUtils
from ..helpers import QuerysetFilter
from ..errors import handle_exception


class SyncModelRouter(BaseModelRouter):
    """
    Sync implementation of model router.
    
    Handles all sync route registration and request processing.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_handler = SyncResponseHandler()
        self.file_handler = SyncFileHandler(self.file_upload_config)
        self.hook_executor = SyncHookExecutor()
        self.model_utils = SyncModelUtils()
        self.queryset_filter = QuerysetFilter(self.model)
    
    def register_list_route(self) -> None:
        """Register sync list route with pagination and filtering."""
        
        @self.router.get(
            "/", 
            response=List[self.list_schema], 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("list")
        )
        @paginate(self.paginator_class)
        def list_items(
            request, 
            q: Optional[str] = None, 
            sort: Optional[str] = None,
            order: Optional[str] = "asc", 
            **kwargs: Any
        ) -> Union[QuerySet, Any]:
            """List objects with optional filtering and sorting."""
            try:
                queryset = self.model.objects.all()
                
                if self.pre_list:
                    queryset = self.hook_executor.execute(self.pre_list, request, queryset) or queryset
                
                queryset = self.queryset_filter.apply_filters(queryset, q, sort, order, **kwargs)
                
                return queryset if not self.custom_response else self.custom_response(request, queryset)
            except Exception as e:
                return handle_exception(e)
    
    def register_detail_route(self) -> None:
        """Register sync detail route."""
        
        @self.router.get(
            "/{item_id}", 
            response=self.detail_schema, 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("get")
        )
        def get_item(request, item_id: int) -> Any:
            """Retrieve a single object by ID."""
            try:
                instance = get_object_or_404(self.model, id=item_id)
                return self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return handle_exception(e)
    
    def register_create_route(self) -> None:
        """Register sync create route."""
        if self.use_multipart_create:
            self._register_multipart_create_route()
        else:
            self._register_json_create_route()
    
    def _register_json_create_route(self) -> None:
        """Register JSON-based create route."""
        
        @self.router.post(
            "/", 
            response=self.detail_schema, 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("create")
        )
        def create_item(request, payload: self.create_schema) -> Any: # type: ignore
            """Create a new object."""
            try:
                if self.before_create:
                    payload = self.hook_executor.execute(
                        self.before_create, request, payload, self.create_schema
                    ) or payload
                
                data = self.model_utils.convert_foreign_keys(self.model, payload.model_dump())
                
                instance = self.model.objects.create(**data)
                
                if self.after_create:
                    instance = self.hook_executor.execute(
                        self.after_create, request, instance
                    ) or instance
                
                return self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return handle_exception(e)
    
    def _register_multipart_create_route(self) -> None:
        """Register multipart/form-data create route."""
        
        @self.router.post(
            "/", 
            response=self.detail_schema, 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("create")
        )
        def create_item(request, payload: self.create_schema = Form(...)) -> Any: # type: ignore
            """Create a new object with file upload support."""
            try:
                if self.before_create:
                    payload = self.hook_executor.execute(
                        self.before_create, request, payload, self.create_schema
                    ) or payload
                
                data, file_fields_map = self.file_handler.process_create_files(
                    request, payload, self.model
                )
                
                data = self.model_utils.convert_foreign_keys(self.model, data)
                
                instance = self.model.objects.create(**data)
                
                if file_fields_map:
                    self.file_handler.handle_file_relations(
                        instance, file_fields_map, self.model
                    )
                
                if self.after_create:
                    instance = self.hook_executor.execute(
                        self.after_create, request, instance
                    ) or instance
                
                return self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return handle_exception(e)
    
    def register_update_route(self) -> None:
        """Register sync update route."""
        if self.use_multipart_update:
            self._register_multipart_update_route()
        else:
            self._register_json_update_route()
    
    def _register_json_update_route(self) -> None:
        """Register JSON-based update route."""
        
        @self.router.patch(
            "/{item_id}", 
            response=self.detail_schema, 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("update")
        )
        def update_item(request, item_id: int, payload: self.update_schema) -> Any: # type: ignore
            """Update an existing object."""
            try:
                instance = get_object_or_404(self.model, id=item_id)
                
                if self.before_update:
                    payload = self.hook_executor.execute(
                        self.before_update, request, instance, payload, self.update_schema
                    ) or payload
                
                data = self.model_utils.convert_foreign_keys(
                    self.model, payload.model_dump(exclude_unset=True)
                )
                
                for key, value in data.items():
                    setattr(instance, key, value)
                instance.save()
                
                if self.after_update:
                    instance = self.hook_executor.execute(
                        self.after_update, request, instance
                    ) or instance
                
                return self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return handle_exception(e)
    
    def _register_multipart_update_route(self) -> None:
        """Register multipart/form-data update route."""
        
        @self.router.patch(
            "/{item_id}", 
            response=self.detail_schema, 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("update")
        )
        def update_item(request, item_id: int, payload: self.update_schema = Form(...)) -> Any: # type: ignore
            """Update an existing object with file upload support."""
            try:
                instance = get_object_or_404(self.model, id=item_id)
                
                if self.before_update:
                    payload = self.hook_executor.execute(
                        self.before_update, request, instance, payload, self.update_schema
                    ) or payload
                
                data, file_fields_map = self.file_handler.process_update_files(
                    request, payload, self.model
                )
                
                data = self.model_utils.convert_foreign_keys(self.model, data)
                
                for key, value in data.items():
                    setattr(instance, key, value)
                instance.save()
                
                if file_fields_map:
                    self.file_handler.handle_file_relations(
                        instance, file_fields_map, self.model
                    )
                
                if self.after_update:
                    instance = self.hook_executor.execute(
                        self.after_update, request, instance
                    ) or instance
                
                return self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return handle_exception(e)
    
    def register_delete_route(self) -> None:
        """Register sync delete route."""
        
        @self.router.delete(
            "/{item_id}", 
            response={200: Dict[str, str]}, 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("delete")
        )
        def delete_item(request, item_id: int) -> Dict[str, str]:
            """Delete an object."""
            try:
                instance = get_object_or_404(self.model, id=item_id)
                
                if self.before_delete:
                    self.hook_executor.execute(self.before_delete, request, instance)
                
                instance.delete()
                
                if self.after_delete:
                    self.hook_executor.execute(self.after_delete, instance)
                
                return {"message": f"{self.model.__name__} with ID {item_id} has been deleted."}
            except Exception as e:
                return handle_exception(e)