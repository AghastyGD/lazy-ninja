from typing import Optional, Type
from abc import ABC, abstractmethod

from django.utils.module_loading import import_string

from ninja.conf import settings
from ninja.pagination import LimitOffsetPagination, PaginationBase, PageNumberPagination


class ExpandablePaginationMixin:
    """Adds support for serializing expanded relations after pagination."""

    def _expand_items(self, items, request):
        router = getattr(request, "_lazy_ninja_router", None)
        expand_fields = getattr(request, "_lazy_ninja_expand_fields", None)

        if not router or not expand_fields:
            return list(items)

        serialized = []
        for item in items:
            if isinstance(item, dict):
                serialized.append(item)
            else:
                serialized.append(
                    router.model_utils.serialize_model_instance(
                        item, expand=expand_fields
                    )
                )

        return serialized

    def paginate_queryset(self, queryset, pagination, **params):  # type: ignore[override]
        result = super().paginate_queryset(queryset, pagination, **params)
        request = params.get("request")
        if request:
            result[self.items_attribute] = self._expand_items(
                result[self.items_attribute], request
            )
        return result

    async def apaginate_queryset(self, queryset, pagination, **params):  # type: ignore[override]
        result = await super().apaginate_queryset(queryset, pagination, **params)  # type: ignore[misc]
        request = params.get("request")
        if request:
            result[self.items_attribute] = self._expand_items(
                result[self.items_attribute], request
            )
        return result


class ExpandableLimitOffsetPagination(ExpandablePaginationMixin, LimitOffsetPagination):
    """Limit offset pagination with expand support."""


class ExpandablePageNumberPagination(ExpandablePaginationMixin, PageNumberPagination):
    """Page number pagination with expand support."""

class BasePagination(ABC):
    """Base class for pagination strategies."""
    
    @abstractmethod
    def get_paginator(self) -> Type[PaginationBase]:
        """Get the Django Ninja paginator class."""
        pass

    @abstractmethod
    def get_pagination_class_name(self) -> str:
        """Get the name of the pagination class for schema generation."""
        pass

class LimitOffsetPaginationStrategy(BasePagination):
    """Limit-offset based pagination strategy."""
    
    def get_paginator(self) -> Type[PaginationBase]:
        return ExpandableLimitOffsetPagination
    
    def get_pagination_class_name(self) -> str:
        return "LimitOffsetPagination"

class PageNumberPaginationStrategy(BasePagination):
    """Page number based pagination strategy."""
    
    def get_paginator(self) -> Type[PaginationBase]:
        return ExpandablePageNumberPagination
    
    def get_pagination_class_name(self) -> str:
        return "PageNumberPagination"

def get_default_pagination_class() -> Type[PaginationBase]:
    """
    Get the default pagination class from Django Ninja settings.
    
    Returns:
        The configured pagination class or LimitOffsetPagination as fallback
    """
    pagination_class = getattr(settings, "PAGINATION_CLASS", None)
    if pagination_class:
        try:
            base = import_string(pagination_class)
        except ImportError:
            pass
        else:
            if issubclass(base, LimitOffsetPagination):
                class CustomExpandable(ExpandablePaginationMixin, base):
                    pass

                return CustomExpandable
            if issubclass(base, PageNumberPagination):
                class CustomExpandable(ExpandablePaginationMixin, base):
                    pass

                return CustomExpandable
            return base
    return LimitOffsetPagination
    
def get_pagination_strategy(pagination_type: Optional[str] = None) -> BasePagination:
    """
    Factory function to get the appropriate pagination strategy.
    
    Args:
        pagination_type: Either 'limit-offset', 'page-number', or None to use Django settings
        
    Returns:
        A pagination strategy instance
        
    Note:
        Pagination configuration priority:
        1. pagination_type parameter if provided
        2. NINJA_PAGINATION_CLASS from Django settings
        3. LimitOffsetPagination as fallback
        
        To configure the page size, set NINJA_PAGINATION_PER_PAGE in your Django settings.
        Example:
            NINJA_PAGINATION_PER_PAGE = 20  # Sets default page size to 20
    """
    if pagination_type is None:
        # Use Django Ninja's default pagination class
        default_class = get_default_pagination_class()
        if issubclass(default_class, PageNumberPagination):
            return PageNumberPaginationStrategy()
        return LimitOffsetPaginationStrategy()
        
    if pagination_type == "limit-offset":
        return LimitOffsetPaginationStrategy()
    elif pagination_type == "page-number":
        return PageNumberPaginationStrategy()
    else:
        raise ValueError(f"Unknown pagination type: {pagination_type}")
