from typing import List, Any, Dict, Optional
from asgiref.sync import sync_to_async

from ninja import Form
from ninja.pagination import paginate

from .base import BaseModelRouter
from ..handlers.response import AsyncResponseHandler
from ..handlers.file_handler import AsyncFileHandler
from ..utils.hooks import AsyncHookExecutor
from ..utils.model import AsyncModelUtils
from ..helpers import QuerysetFilter
from ..errors import handle_exception_async


class AsyncModelRouter(BaseModelRouter):
    """
    Async implementation of model router.

    Handles all async routes registration and request processing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_handler = AsyncResponseHandler()
        self.file_handler = AsyncFileHandler(self.file_upload_config)
        self.hook_executor = AsyncHookExecutor()
        self.model_utils = AsyncModelUtils()
        self.queryset_filter = QuerysetFilter(self.model)

    def register_list_route(self) -> None:
        """Register async list route with pagination and filtering."""

        @self.router.get(
            "/",
            response=List[self.list_schema],
            tags=self.get_tags(),
            operation_id=self.get_operation_id("list")
        )
        @paginate(self.paginator_class)
        async def list_items(
            request,
            q: Optional[str] = None,
            sort: Optional[str] = None,
            order: Optional[str] = "asc",
            **kwargs: Any
        ) -> List[Any]:
            """List objects with optional filtering and sorting."""
            try:
                all_items = await self.model_utils.get_all_objects(self.model)

                if self.pre_list:
                    hook_result = await self.hook_executor.execute(self.pre_list, request, all_items)
                    if hook_result is not None:
                        all_items = hook_result
                
                if q or sort or kwargs:
                    all_items = await self.queryset_filter.apply_filters_async(
                        all_items, q, sort, order, **kwargs
                    )
                else:
                    all_items = await sync_to_async(list)(all_items)

                serialized_items = []
                for item in all_items:
                    serialized = await self.model_utils.serialize_model_instance(item)
                    serialized_items.append(serialized)

                if self.custom_response:
                    return await sync_to_async(self.custom_response)(request, serialized_items)
                
                return serialized_items
            except Exception as e:
                return await handle_exception_async(e)
            
    def register_detail_route(self) -> None:
        """Register async detail route."""

        @self.router.get(
            "/{item_id}",
            response=self.detail_schema,
            tags=self.get_tags(),
            operation_id=self.get_operation_id("get")
        )
        async def get_item(request, item_id: int) -> Any:
            """Retrieve a single object by ID."""
            try:
                instance = await self.model_utils.get_object_or_404(self.model, id=item_id)
                return await self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return await handle_exception_async(e)
            
    def register_create_route(self) -> None:
        """Register async create route."""
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
        async def create_item(request, payload: self.create_schema) -> Any: # type: ignore
            """Create a new object."""
            try:
                if self.before_create:
                    payload = await self.hook_executor.execute(
                        self.before_create, request, payload, self.create_schema
                    ) or payload

                data = await self.model_utils.convert_foreign_keys(self.model, payload.model_dump())

                instance = await self.model_utils.create_instance(self.model, **data)

                if self.after_create:
                    instance = await self.hook_executor.execute(
                        self.after_create, request, instance
                    ) or instance

                return await self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return await handle_exception_async(e)
            
    def _register_multipart_create_route(self) -> None:
        """Register multipart/form-data create route"""

        @self.router.post(
            "/",
            response=self.detail_schema,
            tags=self.get_tags(),
            operation_id=self.get_operation_id("create")
        )
        async def create_item(request, payload: self.create_schema = Form(...)) -> Any: # type: ignore
            """Create a new object with file upload support."""
            try:
                if self.before_create:
                    payload = await self.hook_executor.execute(
                        self.before_create, request, payload, self.create_schema
                    ) or payload

                data, file_fields_map = await self.file_handler.process_create_files(
                    request, payload, self.model
                )

                data = await self.model_utils.convert_foreign_keys(self.model, data)

                instance = await self.model_utils.create_instance(self.model, **data)

                if file_fields_map:
                    await self.file_handler.handle_file_relations(
                        instance, file_fields_map, self.model
                    )

                if self.after_create:
                    instance = await self.hook_executor.execute(
                        self.after_create, request, instance
                    ) or instance

                return await self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return await handle_exception_async(e)
    
    def register_update_route(self) -> None:
        """Register async update route."""
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
        async def update_item(request, item_id: int, payload: self.update_schema) -> Any: # type: ignore
            """Update an existing object"""
            try:
                instance = await self.model_utils.get_object_or_404(self.model, id=item_id)

                if self.before_update:
                    payload = await self.hook_executor.execute(
                        self.before_update, request, instance, payload, self.update_schema
                    ) or payload

                data = await self.model_utils.convert_foreign_keys(
                    self.model, payload.model_dump(exclude_unset=True)
                )

                await self.model_utils.update_instance(instance, data)

                if self.after_update:
                    instance = await self.hook_executor.execute(
                        self.after_update, request, instance
                    ) or instance

                return await self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return await handle_exception_async(e)
            
    def _register_multipart_update_route(self) -> None:
        """Register multipart/form-data update route."""
        
        @self.router.patch(
            "/{item_id}", 
            response=self.detail_schema, 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("update")
        )
        async def update_item(request, item_id: int, payload: self.update_schema = Form(...)) -> Any: # type: ignore
            """Update an existing object with file upload support."""
            try:
                instance = await self.model_utils.get_object_or_404(self.model, id=item_id)
                
                if self.before_update:
                    payload = await self.hook_executor.execute(
                        self.before_update, request, instance, payload, self.update_schema
                    ) or payload
                
                data, file_fields_map = await self.file_handler.process_update_files(
                    request, payload, self.model
                )
                
                data = await self.model_utils.convert_foreign_keys(self.model, data)
                
                await self.model_utils.update_instance(instance, data)
                
                if file_fields_map:
                    await self.file_handler.handle_file_relations(
                        instance, file_fields_map, self.model
                    )
                
                if self.after_update:
                    instance = await self.hook_executor.execute(
                        self.after_update, request, instance
                    ) or instance
                
                return await self.response_handler.handle_response(
                    instance, self.detail_schema, self.custom_response, request
                )
            except Exception as e:
                return await handle_exception_async(e)
    
    def register_delete_route(self) -> None:
        """Register async delete route."""
        
        @self.router.delete(
            "/{item_id}", 
            response={200: Dict[str, str]}, 
            tags=self.get_tags(), 
            operation_id=self.get_operation_id("delete")
        )
        async def delete_item(request, item_id: int) -> Dict[str, str]:
            """Delete an object."""
            try:
                instance = await self.model_utils.get_object_or_404(self.model, id=item_id)
                
                if self.before_delete:
                    await self.hook_executor.execute(self.before_delete, request, instance)
                
                await self.model_utils.delete_instance(instance)
                
                if self.after_delete:
                    await self.hook_executor.execute(self.after_delete, instance)
                
                return {"message": f"{self.model.__name__} with ID {item_id} has been deleted"}
            except Exception as e:
                return await handle_exception_async(e)


            