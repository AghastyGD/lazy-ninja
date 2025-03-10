from http.client import HTTPException
from typing import Type, Callable, Optional, List, Any, Dict, Union

from django.shortcuts import get_object_or_404
from django.db.models import Model, QuerySet

from ninja import Router, Schema, NinjaAPI
from ninja.pagination import paginate

from .utils import convert_foreign_keys
from .pagination import BasePagination
from .helpers import execute_hook, handle_response, apply_filters

def register_model_routes_internal(
    api: NinjaAPI,
    model: Type[Model],
    base_url: str,
    list_schema: Type[Schema],
    detail_schema: Type[Schema],
    create_schema: Optional[Type[Schema]] = None,
    update_schema: Optional[Type[Schema]] = None,
    pre_list: Optional[Callable[[Any, Any], Any]] = None,
    before_create: Optional[Callable[[Any, Any, Type[Schema]], Any]] = None,
    after_create: Optional[Callable[[Any, Any], Any]] = None,
    before_update: Optional[Callable[[Any, Any, Type[Schema]], Any]] = None,
    after_update: Optional[Callable[[Any, Any], Any]] = None,
    before_delete: Optional[Callable[[Any, Any], None]] = None,
    after_delete: Optional[Callable[[Any], None]] = None,
    custom_response: Optional[Callable[[Any, Any], Any]] = None,
    search_field: Optional[str] = "name",
    pagination_strategy: Optional[BasePagination] = None
) -> None:
    """
    Internal function that registers CRUD routes for a Django model.

    Args:
        api: NinjaAPI instance
        model: Django model class
        base_url: Base URL for the routes
        list_schema: Schema for list responses
        detail_schema: Schema for detail responses
        create_schema: Schema for create requests
        update_schema: Schema for update requests
        pre_list/post_list: Hooks for list operation
        before_create/after_create: Hooks for create operation
        before_update/after_update: Hooks for update operation
        before_delete/after_delete: Hooks for delete operation
        custom_response: Hook for customizing response format
        search_field: Field to use for search
        pagination_strategy: Strategy for pagination
    """
    router = Router()
    model_name = model.__name__.lower()
    paginator_class = pagination_strategy.get_paginator() if pagination_strategy else None

    @router.get("/", response=List[list_schema], tags=[model.__name__], operation_id=f"list_{model_name}")
    @paginate(paginator_class)
    def list_items(request, q: Optional[str] = None, sort: Optional[str] = None,
                   order: Optional[str] = "asc", **kwargs: Any) -> Union[QuerySet, Any]:
        """List objects with optional filtering and sorting."""
        try:
            queryset = model.objects.all()
            queryset = execute_hook(pre_list, request, queryset) or queryset
            queryset = apply_filters(queryset, model, q, sort, order, search_field, kwargs)
            return queryset if not custom_response else custom_response(request, queryset)
        except Exception as e:
            return {"error": str(e)}

    @router.get("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"get_{model_name}")
    def get_item(request, item_id: int) -> Any:
        """Retrieve a single object by ID."""
        instance = get_object_or_404(model, id=item_id)
        return handle_response(instance, detail_schema, custom_response, request)

    if create_schema:
        @router.post("/", response=detail_schema, tags=[model.__name__], operation_id=f"create_{model_name}")
        def create_item(request, payload: create_schema) -> Any: # type: ignore
            """Create a new object."""
            payload = execute_hook(before_create, request, payload, create_schema) or payload
            data = convert_foreign_keys(model, payload.model_dump())
            instance = model.objects.create(**data)
            instance = execute_hook(after_create, request, instance) or instance
            return handle_response(instance, detail_schema, custom_response, request)

    if update_schema:
        @router.patch("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"update_{model_name}")
        def update_item(request, item_id: int, payload: update_schema) -> Any: # type: ignore
            """Update an existing object."""
            instance = get_object_or_404(model, id=item_id)
            payload = execute_hook(before_update, request, instance, payload, update_schema) or payload
            data = convert_foreign_keys(model, payload.model_dump(exclude_unset=True))
            
            for key, value in data.items():
                setattr(instance, key, value)
            instance.save()
            
            instance = execute_hook(after_update, request, instance) or instance
            return handle_response(instance, detail_schema, custom_response, request)

    @router.delete("/{item_id}", response={200: Dict[str, str]}, tags=[model.__name__], operation_id=f"delete_{model_name}")
    def delete_item(request, item_id: int) -> Dict[str, str]:
        """Delete an object."""
        instance = get_object_or_404(model, id=item_id)
        execute_hook(before_delete, request, instance)
        instance.delete()
        execute_hook(after_delete, instance)
        return {"message": f"{model.__name__} with ID {item_id} has been deleted."}

    api.add_router(base_url, router)