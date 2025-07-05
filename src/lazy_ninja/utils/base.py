"""
Core utility functions for lazy-ninja.
These are the fundamental building blocks used throughout the library.
"""
import asyncio
from typing import Type, Any, Dict
from decimal import Decimal
from asgiref.sync import sync_to_async

from django.db import models
from django.shortcuts import get_object_or_404


def convert_foreign_keys(model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts integer values for ForeignKey fields in `data` to the corresponding model instances.
    
    Args:
        model: Django model class
        data: Dictionary with field data
        
    Returns:
        Dictionary with ForeignKey integers converted to model instances
    """
    for field in model._meta.fields:
        if isinstance(field, models.ForeignKey) and field.name in data:
            fk_value = data[field.name]
            if isinstance(fk_value, int):
                data[field.name] = field.related_model.objects.get(pk=fk_value)
    return data


def get_field_value_safely(obj: models.Model, field: models.Field) -> Any:
    """
    Get field value without triggering database queries.
    For ForeignKey fields, returns the ID directly.
    
    Args:
        obj: Django model instance
        field: Django model field
        
    Returns:
        Field value or None if not accessible
    """
    if isinstance(field, models.ForeignKey):
        attname = field.attname
        if hasattr(obj, attname):
            return getattr(obj, attname)
        return None
    
    # For non-ForeignKey fields, get the value directly
    try:
        value = getattr(obj, field.name)
        return value
    except Exception:
        return None


def serialize_model_instance(obj: models.Model) -> Dict[str, Any]:
    """
    Serializes a Django model instance into a dictionary with simple types.
    Avoids triggering database queries for related fields.
    
    Args:
        obj: Django model instance
        
    Returns:
        Dictionary with serialized field values
    """
    data = {}
    for field in obj._meta.fields:
        try:
            value = get_field_value_safely(obj, field)
            
            if value is None:
                data[field.name] = None
            elif isinstance(field, (models.DateField, models.DateTimeField)):
                data[field.name] = value.isoformat() if value else None
            elif isinstance(field, (models.ImageField, models.FileField)):
                data[field.name] = value.url if hasattr(value, 'url') else str(value)
            elif hasattr(value, 'pk'):
                data[field.name] = value.pk
            else:
                data[field.name] = value
        except Exception:
            data[field.name] = None
    return data


def is_async_context() -> bool:
    """
    Check if we're in an async context by inspecting the call stack.
    
    Returns:
        True if in async context, False otherwise
    """
    try:
        return asyncio.get_event_loop().is_running()
    except RuntimeError:
        return False


def get_pydantic_type(field: models.Field) -> Type:
    """
    Map a Django model field to an equivalent Python type for Pydantic validation.
    
    Args:
        field: Django model field
        
    Returns:
        Python type for Pydantic
    """
    if isinstance(field, models.AutoField):
        return int
    elif isinstance(field, (models.CharField, models.TextField)):
        return str
    elif isinstance(field, models.IntegerField):
        return int
    elif isinstance(field, models.DecimalField):
        return Decimal
    elif isinstance(field, models.FloatField):
        return float
    elif isinstance(field, models.BooleanField):
        return bool
    elif isinstance(field, (models.DateField, models.DateTimeField)):
        return str
    elif isinstance(field, (models.ImageField, models.FileField)):
        return str
    elif isinstance(field, models.ForeignKey):
        return int
    else:
        return str


# Async versions of core functions
convert_foreign_keys_async = sync_to_async(convert_foreign_keys)
serialize_model_instance_async = sync_to_async(serialize_model_instance)
get_all_objects_async = sync_to_async(lambda m: m.objects.all())
get_object_or_404_async = sync_to_async(get_object_or_404)


