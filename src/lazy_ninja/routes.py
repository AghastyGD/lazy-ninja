from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from typing import Type, Callable, Optional, List, Any, Dict
from django.db.models import Model
from ninja import NinjaAPI
from .utils import convert_foreign_keys

def register_model_routes_internal(
    api: NinjaAPI,
    model: Type[Model],
    base_url: str,
    list_schema: Type[Schema],
    detail_schema: Type[Schema],
    create_schema: Optional[Type[Schema]] = None,
    update_schema: Optional[Type[Schema]] = None,
    pre_list: Optional[Callable[[Any, Any], Any]] = None,
    post_list: Optional[Callable[[Any, List[Any]], List[Any]]] = None,
    before_create: Optional[Callable[[Any, Any, Type[Schema]], Any]] = None,
    after_create: Optional[Callable[[Any, Any], Any]] = None,
    before_update: Optional[Callable[[Any, Any, Type[Schema]], Any]] = None,
    after_update: Optional[Callable[[Any, Any], Any]] = None,
    before_delete: Optional[Callable[[Any, Any], None]] = None,
    after_delete: Optional[Callable[[Any], None]] = None,
    custom_response: Optional[Callable[[Any, Any], Any]] = None,
    search_field: Optional[str] = "name",
) -> None:
    """
    Internal function that registers CRUD routes for a Django model.

    It creates endpoints for listing, retrieving, creating, updating, and deleting objects,
    and wires in hook functions for custom behavior.
    """
    router = Router()
    model_name = model.__name__.lower()

    @router.get("/", response=List[list_schema], tags=[model.__name__], operation_id=f"list_{model_name}",)
    def list_items(request, q: Optional[str] = None):
        """
        Endpoint to list objects of the model.
        Optionally filters the queryset based on a search query.
        """
        qs = model.objects.all()
        if q and search_field and hasattr(model, search_field):
            qs = qs.filter(**{f"{search_field}__icontains": q})
        if pre_list:
            qs = pre_list(request, qs)
        results = list(qs)
        if post_list:
            results = post_list(request, results)
        return [list_schema.model_validate(obj.__dict__) for obj in results] if custom_response is None else custom_response(request, results)

    @router.get("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"get_{model_name}")
    def get_item(request, item_id: int):
        """
        Endpoint to retrieve the details of a single object by its ID.
        """
        instance = get_object_or_404(model, id=item_id)
        return detail_schema.model_validate(instance.__dict__) if custom_response is None else custom_response(request, instance)

    if create_schema:
        @router.post("/", response=detail_schema, tags=[model.__name__], operation_id=f"create_{model_name}")
        def create_item(request, payload: create_schema):  # type: ignore
            """
            Endpoint to create a new object.
            Executes the before_create hook to modify the payload if needed.
            """
            if before_create and not getattr(before_create, "__is_default_hook__", False):
                payload = before_create(request, payload, create_schema)
            data = payload.model_dump()
                    
            data = convert_foreign_keys(model, data)  # Convert FK integers to model instances
            
            instance = model.objects.create(**data)
            if after_create and not getattr(after_create, "__is_default_hook__", False):
                instance = after_create(request, instance)
            return detail_schema.model_validate(instance.__dict__) if custom_response is None else custom_response(request, instance)

    if update_schema:
        @router.put("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"update_{model_name}")
        def update_item(request, item_id: int, payload: update_schema):  # type: ignore  
            """
            Endpoint to update an existing object by its ID.
            Executes the before_update hook to adjust the payload if needed.
            """
            instance = get_object_or_404(model, id=item_id)
            # Call before_update hook if defined and not the default one.
            if before_update and not getattr(before_update, "__is_default_hook__", False):
                payload = before_update(request, instance, payload, update_schema)
            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(instance, key, value)
            instance.save()
            if after_update and not getattr(after_update, "__is_default_hook__", False):
                instance = after_update(request, instance)
            return detail_schema.model_validate(instance.__dict__) if custom_response is None else custom_response(request, instance)

    @router.delete("/{item_id}", response={200: Dict[str, str]}, tags=[model.__name__], operation_id=f"delete_{model_name}")
    def delete_item(request, item_id: int):
        """
        Endpoint to delete an object by its ID.
        Executes the before_delete and after_delete hooks if defined.
        """
        instance = get_object_or_404(model, id=item_id)
        if before_delete and not getattr(before_delete, "__is_default_hook__", False):
            before_delete(request, instance)
        instance.delete()
        if after_delete and not getattr(after_delete, "__is_default_hook__", False):
            after_delete(instance)
        return {"message": f"{model.__name__} with ID {item_id} has been deleted."}

    # Add the configured router to the main NinjaAPI instance under the specified base URL.
    api.add_router(base_url, router)
    
  
