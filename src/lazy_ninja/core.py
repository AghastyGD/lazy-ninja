from typing import Any, Optional, Type

from django.db.models import Model
from ninja import NinjaAPI
from pydantic import BaseModel

from .base import BaseModelController
from .helpers import get_hook
from .registry import ModelRegistry, controller_for
from .routes import register_model_routes_internal
from .file_upload import FileUploadConfig

def register_model_routes(
    api: NinjaAPI,
    model: Type[Model],
    base_url: str,
    list_schema: Type[BaseModel],
    detail_schema: Type[BaseModel],
    create_schema: Optional[Type[BaseModel]] = None,
    update_schema: Optional[Type[BaseModel]] = None,
    pagination_strategy: Optional[Any] = None,
    file_upload_config: Optional[FileUploadConfig] = None,
    use_multipart_create: bool = False,
    use_multipart_update: bool = False,
    is_async: bool = True,
) -> None:
    """Register CRUD routes for a Django model using Django Ninja.

    This function retrieves the registered controller for the model (if any)
    and passes its hooks to the internal route registration function.

    Args:
        api: NinjaAPI instance
        model: Django model class
        base_url: Base URL for the routes (e.g., "/users")
        list_schema: Pydantic schema for list responses
        detail_schema: Pydantic schema for detail responses
        create_schema: Optional Pydantic schema for create requests
        update_schema: Optional Pydantic schema for update requests
        pagination_strategy: Optional pagination strategy instance
        file_upload_config: Optional configuration for file uploads
        use_multipart_create: Whether to use multipart/form-data for create
        use_multipart_update: Whether to use multipart/form-data for update
        is_async: Whether to use async routes (default: True)
    
    Example:
        >>> from myapp.models import User
        >>> UserSchema = generate_schema(User)
        >>> register_model_routes(
        ...     api=api,
        ...     model=User,
        ...     base_url="/users",
        ...     list_schema=UserSchema,
        ...     detail_schema=UserSchema,
        ... )
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