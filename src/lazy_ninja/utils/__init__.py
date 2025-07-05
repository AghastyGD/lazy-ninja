"""
Utility modules for lazy-ninja.
"""

# Core utilities
from .base import (
    convert_foreign_keys,
    serialize_model_instance,
    get_field_value_safely,
    is_async_context,
    get_pydantic_type,
    # Async versions
    convert_foreign_keys_async,
    serialize_model_instance_async,
    get_all_objects_async,
    get_object_or_404_async,
)

# Schema generation
from .schema import generate_schema

# Component classes
from .hooks import SyncHookExecutor, AsyncHookExecutor
from .model import SyncModelUtils, AsyncModelUtils

# Legacy functions
from .legacy import handle_response_async, execute_hook_async

__all__ = [
    # Core functions
    'convert_foreign_keys',
    'serialize_model_instance', 
    'get_field_value_safely',
    'is_async_context',
    'get_pydantic_type',
    'generate_schema',
    
    # Async versions
    'convert_foreign_keys_async',
    'serialize_model_instance_async',
    'get_all_objects_async',
    'get_object_or_404_async',
    
    # Component classes
    'SyncHookExecutor',
    'AsyncHookExecutor', 
    'SyncModelUtils',
    'AsyncModelUtils',
    
    # Legacy (deprecated)
    'handle_response_async',
    'execute_hook_async',
]
