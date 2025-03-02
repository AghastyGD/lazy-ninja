from typing import Type, Callable, Optional, List, Any, Dict

from django.shortcuts import get_object_or_404
from django.db.models import Model
from django.db import models
from django.core.exceptions import FieldDoesNotExist, ValidationError, FieldError

from ninja import Router, Schema, NinjaAPI
from ninja.pagination import paginate, LimitOffsetPagination

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
    @paginate(LimitOffsetPagination)
    def list_items(request, q: Optional[str] = None, sort: Optional[str] = None,
                   order: Optional[str]= "asc",
                   **kwargs: Any):
        """
        Endpoint to list objects of the model.
        Supports filtering, sorting and pagination via query parameters.
        """
        qs = model.objects.all()
        if q and search_field and hasattr(model, search_field):
            qs = qs.filter(**{f"{search_field}__icontains": q})
            
        # Dynamic filters (kwargs)
        filter_kwargs = {}
        for field_name, field_value in kwargs.items():
            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            if isinstance(field, (models.IntegerField, models.AutoField)):
                try:
                    filter_kwargs[field_name] = int(field_value)
                except ValueError as exc:
                    raise ValidationError(f"Invalid value for integer field '{field_name}'") from exc
        
            elif isinstance(field, models.BooleanField):
                if field_value.lower() == "true":
                    filter_kwargs[field_name] = True
                elif field.value.lower() == "false":
                    filter_kwargs[field_name] = False
                else:
                    raise ValidationError(f"Invalid value for boolean field '{field_name}'")
            else:
                filter_kwargs[field_name] = field_value
        if filter_kwargs:
            qs = qs.filter(**filter_kwargs)
        
        # Ordering
        if sort:
            try:
                model._meta.get_field(sort)
            except FieldError:
                raise ValidationError(f"Invalid field for sorting: {sort}")
            
            if order.lower() == "desc":
                sort_field = f"-{sort}"
            else:
                sort_field = sort
            qs = qs.order_by(sort_field)
            
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
                    
            data = convert_foreign_keys(model, data)
            
            instance = model.objects.create(**data)
            if after_create and not getattr(after_create, "__is_default_hook__", False):
                instance = after_create(request, instance)
            return detail_schema.model_validate(instance.__dict__) if custom_response is None else custom_response(request, instance)

    if update_schema:
        @router.patch("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"update_{model_name}")
        def update_item(request, item_id: int, payload: update_schema):  # type: ignore  
            """
            Endpoint to update an existing object by its ID.
            Executes the before_update hook to adjust the payload if needed.
            """
            instance = get_object_or_404(model, id=item_id)
            # Call before_update hook if defined and not the default one.
            if before_update and not getattr(before_update, "__is_default_hook__", False):
                payload = before_update(request, instance, payload, update_schema)

            data = payload.model_dump(exclude_unset=True)

            data = convert_foreign_keys(model, data)

            for key, value in data.items():
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
    
  
