from typing import Any, Callable, Optional, Type, Dict

from django.db.models import QuerySet, Model
from django.core.exceptions import FieldDoesNotExist

from ninja import Schema

def execute_hook(hook: Optional[Callable], *args, **kwargs) -> Any:
    """
    Safely execute a hook function if it exists and is not a default hook.
    
    Args:
        hook: The hook function to execute
        *args: Positional arguments to pass to the hook
        **kwargs: Keyword arguments to pass to the hook
        
    Returns:
        The result of the hook execution or the first argument if no hook
    """
    if hook and not getattr(hook, "__is_default_hook__", False):
        return hook(*args, **kwargs)
    return args[0] if args else None

def handle_response(instance: Any, schema: Type[Schema], custom_response: Optional[Callable], request: Any = None) -> Any:
    """
    Handle the response formatting based on custom_response or schema validation.
    
    Args:
        instance: The instance to format
        schema: The schema to use for validation
        custom_response: Optional custom response handler
        request: Optional request object for custom response
        
    Returns:
        Formatted response
    """
    if custom_response:
        return custom_response(request, instance)
    return schema.model_validate(instance.__dict__)


def apply_filters(
    queryset: QuerySet,
    model: Type[Model],
    q: Optional[str],
    sort: Optional[str],
    order: str,
    search_field: Optional[str],
    kwargs: Dict[str, Any]
) -> QuerySet:
    """
    Apply filters and sorting to a queryset.
    
    Args:
        queryset: The base queryset to filter
        model: The Django model class
        q: Search query string
        sort: Field to sort by
        order: Sort order ('asc' or 'desc')
        search_field: Field to use for search
        kwargs: Additional filter parameters
        
    Returns:
        Filtered and sorted queryset
    """
    if q and search_field:
        queryset = queryset.filter(**{f"{search_field}__icontains": q})
    
    if kwargs:
        queryset = queryset.filter(**kwargs)
        
    if sort:
        try:
            model._meta.get_field(sort)
            sort_field = f"-{sort}" if order.lower() == "desc" else sort
            queryset = queryset.order_by(sort_field)
        except FieldDoesNotExist:
            pass
            
    return queryset 
