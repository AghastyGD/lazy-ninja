from ninja import NinjaAPI
from .base import BaseModelController
from .registry import ModelRegistry
from .routes import register_model_routes_internal
from typing import Type, Optional
from ninja import Schema
from django.db.models import Model

def register_model_routes(
    api: NinjaAPI,
    model: Type[Model],
    base_url: str,
    list_schema: Type[Schema],
    detail_schema: Type[Schema],
    create_schema: Optional[Type[Schema]] = None,
    update_schema: Optional[Type[Schema]] = None,
    search_field: Optional[str] = "name"
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
        before_create=controller.before_create,
        after_create=controller.after_create,
        before_update=controller.before_update,
        after_update=controller.after_update,
        before_delete=controller.before_delete,
        after_delete=controller.after_delete,
        pre_list=controller.pre_list,
        post_list=controller.post_list,
        custom_response=controller.custom_response,
        search_field=search_field
    )
# __all__ = ['register_model_routes']