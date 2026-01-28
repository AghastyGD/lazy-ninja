"""Route registration facade delegating to sync/async model routers."""
from typing import Type, Optional, Callable, Any

from django.db.models import Model

from ninja import NinjaAPI, Schema
from pydantic import BaseModel

from .router.base import BaseModelRouter
from .router.async_router import AsyncModelRouter
from .router.sync_router import SyncModelRouter
from .pagination import BasePagination
from .file_upload import FileUploadConfig


def register_model_routes_internal(
    api: NinjaAPI,
    model: Type[Model],
    base_url: str,
    list_schema: Type[BaseModel],
    detail_schema: Type[BaseModel],
    create_schema: Optional[Type[BaseModel]] = None,
    update_schema: Optional[Type[BaseModel]] = None,
    pre_list: Optional[Callable[[Any, Any], Any]] = None,
    before_create: Optional[Callable[[Any, Any, Type[Schema]], Any]] = None,
    after_create: Optional[Callable[[Any, Any], Any]] = None,
    before_update: Optional[Callable[[Any, Any, Type[Schema]], Any]] = None,
    after_update: Optional[Callable[[Any, Any], Any]] = None,
    before_delete: Optional[Callable[[Any, Any], None]] = None,
    after_delete: Optional[Callable[[Any], None]] = None,
    custom_response: Optional[Callable[[Any, Any], Any]] = None,
    pagination_strategy: Optional[BasePagination] = None,
    file_upload_config: Optional[FileUploadConfig] = None,
    use_multipart_create: bool = False,
    use_multipart_update: bool = False,
    is_async: bool = True,
) -> None:
    """Register CRUD routes for a Django model using the appropriate router implementation."""

    router_cls: Type[BaseModelRouter]
    router_cls = AsyncModelRouter if is_async else SyncModelRouter

    router = router_cls(
        api=api,
        model=model,
        base_url=base_url,
        list_schema=list_schema,
        detail_schema=detail_schema,
        create_schema=create_schema,
        update_schema=update_schema,
        pagination_strategy=pagination_strategy,
        file_upload_config=file_upload_config,
        use_multipart_create=use_multipart_create,
        use_multipart_update=use_multipart_update,
        pre_list=pre_list,
        before_create=before_create,
        after_create=after_create,
        before_update=before_update,
        after_update=after_update,
        before_delete=before_delete,
        after_delete=after_delete,
        custom_response=custom_response,
    )

    router.finalize()
