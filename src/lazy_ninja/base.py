from abc import ABC
from typing import Any

class BaseModelController(ABC):
    """
    Base controller class for a Django model.
    This class provides default hook methods that can be overridden for custom logic
    before and after CRUD operations.
    """
    
    @classmethod
    def before_create(cls, request: Any, payload: Any, create_schema: Any) -> Any:
        """Hook executed before creating a new object."""
        return payload
    before_create.__is_default_hook__ = True
    
    @classmethod
    def after_create(cls, request: Any, instance: Any) -> Any:
        """Hook executed after creating a new object."""
        return instance
    after_create.__is_default_hook__ = True
    
    @classmethod
    def before_update(cls, request: Any, instance: Any, payload: Any, update_schema: Any) -> Any:
        """Hook executed before updating an object."""
        return payload
    before_update.__is_default_hook__ = True
    
    @classmethod
    def after_update(cls, request: Any, instance: Any) -> Any:
        """Hook executed after updating an object."""
        return instance
    after_update.__is_default_hook__ = True
    
    @classmethod
    def before_delete(cls, request: Any, instance: Any) -> None:
        """Hook executed before deleting an object."""
        pass
    before_delete.__is_default_hook__ = True
    
    @classmethod
    def after_delete(cls, instance: Any) -> None:
        """Hook executed after deleting an object."""
        pass
    after_delete.__is_default_hook__ = True
    
    @classmethod
    def pre_list(cls, request: Any, queryset: Any) -> Any:
        """
        Hook to modify the queryset before listing objects.
        Useful for filtering or ordering results.
        """
        return queryset
    pre_list.__is_default_hook__ = True
    
    @classmethod
    def post_list(cls, request: Any, results: list) -> list:
        """
        Hook to process the results after listing objects.
        This can be used for data transformation or additional processing.
        """
        return results
    post_list.__is_default_hook__ = True
    
    @classmethod
    def custom_response(cls, request: Any, data: Any) -> Any:
        """
        Hook to customize the response data.
        Return data as-is by default.
        """
        return data
    custom_response.__is_default_hook__ = True
