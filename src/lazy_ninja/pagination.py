from typing import Optional, Type
from abc import ABC, abstractmethod

from django.utils.module_loading import import_string

from ninja.conf import settings
from ninja.pagination import LimitOffsetPagination, PaginationBase, PageNumberPagination

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
        return LimitOffsetPagination
    
    def get_pagination_class_name(self) -> str:
        return "LimitOffsetPagination"

class PageNumberPaginationStrategy(BasePagination):
    """Page number based pagination strategy."""
    
    def get_paginator(self) -> Type[PaginationBase]:
        return PageNumberPagination
    
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
            return import_string(pagination_class)
        except ImportError:
            pass
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
        if default_class == PageNumberPagination:
            return PageNumberPaginationStrategy()
        return LimitOffsetPaginationStrategy()
        
    if pagination_type == "limit-offset":
        return LimitOffsetPaginationStrategy()
    elif pagination_type == "page-number":
        return PageNumberPaginationStrategy()
    else:
        raise ValueError(f"Unknown pagination type: {pagination_type}")