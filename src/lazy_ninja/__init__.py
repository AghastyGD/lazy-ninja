from typing import Type, Optional

from django.db.models import Model

from ninja import NinjaAPI
from ninja import Schema

from .base import BaseModelController
from .helpers import get_hook
from .registry import ModelRegistry, controller_for
from .routes import register_model_routes_internal
from .file_upload import FileUploadConfig

def register_model_routes(
    api: NinjaAPI,
    model: Type[Model],
    base_url: str,
    list_schema: Type[Schema],
    detail_schema: Type[Schema],
    create_schema: Optional[Type[Schema]] = None,
    update_schema: Optional[Type[Schema]] = None,
    pagination_strategy: Optional[str] = None,
    file_upload_config: Optional[FileUploadConfig] = None,
    use_multipart_create: bool = False,
    use_multipart_update: bool = False,
    is_async: bool = True
) -> None:
    """
    Main function to register CRUD routes for a Django model using Django Ninja.

    Args:
        api: NinjaAPI instance.
        model: Django model class.
        base_url: Base URL for the routes.
        list_schema: Schema for list responses.
        detail_schema: Schema for detail responses.
        create_schema: (Optional) Schema for create requests.
        update_schema: (Optional) Schema for update requests.
        pagination_strategy: (Optional) Strategy for pagination.
        file_upload_config: (Optional) Configuration for file uploads.
        use_multipart_create: Whether to use multipart/form-data for create endpoint.
        use_multipart_update: Whether to use multipart/form-data for update endpoint.
        is_async: Whether to use async routes (default: True).

    This function retrieves the registered controller for the model (if any)
    and passes its hooks to the internal route registration function.
    """
    ModelRegistry.discover_controllers()

    controller = ModelRegistry.get_controller(model.__name__)
    if not controller:
        controller = BaseModelController
    
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
        pagination_strategy=pagination_strategy,
        file_upload_config=file_upload_config,
        use_multipart_create=use_multipart_create,
        use_multipart_update=use_multipart_update,
        is_async=is_async
    )