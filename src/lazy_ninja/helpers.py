import re
from typing import Any, Callable, Optional, Type, Dict
from asgiref.sync import sync_to_async

from django.db.models import QuerySet, Model
from django.core.exceptions import FieldDoesNotExist

from ninja import Schema

def get_hook(controller: Optional[Any], hook_name: str) -> Optional[Callable]:
    """
    Safely get a hook method from a controller.
    
    Args:
        controller: The controller instance or None
        hook_name: Name of the hook method to get
        
    Returns:
        The hook method if it exists, None otherwise
    """
    return getattr(controller, hook_name, None) if controller else None

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

def parse_query_param(q: str) -> Dict[str, Any]:
    """
    Parse a query parameter `q` in the format 'field=value' or 'field:value'
    and return a dictionary for use in filter()
    
    Examples:
    - "published=false" -> {"published": False}
    - "published:false" -> {"published": False}
    - "title=test" -> {"title__icontains": "test"}
    - "views>10" -> {"views__gt": 10}
    """
    filter_dict = {}
    
    if not q:
        return filter_dict
    
    operators = ['=', ':', '>', '<', '>=', '<=']
    operator_found = None
    field_name = None
    value = None
    
    for op in operators:
        if op in q:
            field_name, value = q.split(op, 1)
            operator_found = op
            break
    
    if not operator_found:
        return {}
    
    value = value.strip()
    
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    
    elif value.isdigit():
        value = int(value)
    
    if operator_found in ['=', ':']:
        if isinstance(value, str) and not (isinstance(value, bool)):
            filter_dict[f"{field_name}__icontains"] = value
        else:
            filter_dict[field_name] = value
    elif operator_found == '>':
        filter_dict[f"{field_name}__gt"] = value
    elif operator_found == '<':
        filter_dict[f"{field_name}__lt"] = value
    elif operator_found == '>=':
        filter_dict[f"{field_name}__gte"] = value
    elif operator_found == '<=':
        filter_dict[f"{field_name}__lte"] = value
    
    return filter_dict

def apply_filters(
    queryset: QuerySet,
    model: Type[Model],
    q: Optional[str],
    sort: Optional[str],
    order: str,
    kwargs: Dict[str, Any]
) -> QuerySet:
    """
    Apply filters and sorting to a queryset.
    
    Args:
        queryset: The base queryset to filter
        model: The Django model class
        q: Search query string or field=value expression
        sort: Field to sort by
        order: Sort order ('asc' or 'desc')
        kwargs: Additional filter parameters
        
    Returns:
        Filtered and sorted queryset
    """
    if q:
        filter_dict = parse_query_param(q)
        
        if filter_dict:
            queryset = queryset.filter(**filter_dict)

    if kwargs:
        valid_kwargs = {}
        for key, value in kwargs.items():
            try:
                field = model._meta.get_field(key)
                valid_kwargs[key] = value
            except FieldDoesNotExist:
                continue
        
        if valid_kwargs:
            queryset = queryset.filter(**valid_kwargs)
    
    if sort:
        try:
            model._meta.get_field(sort)
            sort_field = f"-{sort}" if order.lower() == "desc" else sort
            queryset = queryset.order_by(sort_field)
        except FieldDoesNotExist:
            pass
            
    return queryset

async def apply_filters_async(queryset, model, q, sort, order, kwargs):
    """
    Asynchronous version for applying filters to a queryset
    """
    if q:
        filter_dict = await sync_to_async(parse_query_param)(q)
        
        if filter_dict:
            queryset = await sync_to_async(lambda qs, kw: qs.filter(**kw))(queryset, filter_dict)
    
    if kwargs:
        valid_kwargs = {}
        for key, value in kwargs.items():
            try:
                field = model._meta.get_field(key)
                valid_kwargs[key] = value
            except FieldDoesNotExist:
                continue
        
        if valid_kwargs:
            queryset = await sync_to_async(lambda qs, kw: qs.filter(**kw))(queryset, valid_kwargs)
    
    if sort:
        try:
            await sync_to_async(lambda m, s: m._meta.get_field(s))(model, sort)
            
            sort_field = f"-{sort}" if order.lower() == "desc" else sort
            queryset = await sync_to_async(lambda qs, sf: qs.order_by(sf))(queryset, sort_field)
        except Exception:
            pass
    
    return await sync_to_async(list)(queryset)

def to_kebab_case(name: str) -> str:
    """
    Convert a string from CamelCase, PascalCase, snake_case, or SCREAMING_SNAKE_CASE to kebab-case

    Args:
        name: String to convert

    Returns:
        Kebab-case string

    Examples:
        >>> to_kebab_case('CamelCase')
        'camel-case'
        >>> to_kebab_case('PascalCase')
        'pascal-case'
        >>> to_kebab_case('snake_case')
        'snake-case'
        >>> to_kebab_case('SCREAMING_SNAKE_CASE')
        'screaming-snake-case'
        >>> to_kebab_case('XMLHttpRequest')
        'xml-http-request'
    """
    # Handle acronyms first (e.g., XML, API)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
    
    # Convert to lowercase and handle existing underscores
    return s2.lower().replace('_', '-').replace('--', '-')