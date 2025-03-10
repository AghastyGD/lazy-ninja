from typing import Type, Optional

from django.db.models import Model

from ninja import NinjaAPI
from ninja import Schema

from .base import BaseModelController
from .helpers import get_hook
from .registry import ModelRegistry, controller_for
from .routes import register_model_routes_internal

def register_model_routes(
    api: NinjaAPI,
    model: Type[Model],
    base_url: str,
    list_schema: Type[Schema],
    detail_schema: Type[Schema],
    create_schema: Optional[Type[Schema]] = None,
    update_schema: Optional[Type[Schema]] = None,
    search_field: Optional[str] = "name",
    pagination_strategy: Optional[str] = None
) -> None:
    """
    Main function to register CRUD routes for a Django model using Django Ninja.

    Parameters:
      - api: Instance of NinjaAPI.
      - model: The Django model class.
      - base_url: Base URL for the resource endpoints.
      - list_schema: Pydantic schema for listing objects.
      - detail_schema: Pydantic schema for retrieving object details.
      - create_schema: (Optional) Pydantic schema for creating an object.
      - update_schema: (Optional) Pydantic schema for updating an object.
      - search_field: Field name used for search queries (default is "name").

    This function retrieves the registered controller for the model (if any)
    and passes its hooks to the internal route registration function.
    """
    # Retrieve the custom controller for the model; use BaseModelController if none is registered.
    ModelRegistry.discover_controllers()

    controller = ModelRegistry.get_controller(model.__name__)
    if not controller:
        controller = BaseModelController
    
    # Call the internal function that sets up the router and registers all endpoints.
    register_model_routes_internal(
        api=api,
        model=model,
        base_url=base_url,
        list_schema=list_schema,
        detail_schema=detail_schema,
        create_schema=create_schema,
        update_schema=update_schema,
        pre_list=get_hook(controller, 'pre_list'),
        before_create=get_hook(controller, 'before_create'),
        after_create=get_hook(controller, 'after_create'),
        before_update=get_hook(controller, 'before_update'),
        after_update=get_hook(controller, 'after_update'),
        before_delete=get_hook(controller, 'before_delete'),
        after_delete=get_hook(controller, 'after_delete'),
        custom_response=get_hook(controller, 'custom_response'),
        search_field=search_field,
        pagination_strategy=pagination_strategy
    )