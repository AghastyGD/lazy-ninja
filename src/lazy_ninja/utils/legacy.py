"""
Legacy async helper functions for backward compatibility.
These will be deprecated in future versions.
"""
import warnings
from asgiref.sync import sync_to_async

from ..helpers import execute_hook
from .base import (
    convert_foreign_keys_async,
    serialize_model_instance_async,
    get_all_objects_async,
    get_object_or_404_async
)


def handle_response_async(instance, schema, custom_response, request):
    """
    Async version of handle_response that uses serialize_model_instance_async.
    
    DEPRECATED: Use AsyncResponseHandler instead.
    """
    warnings.warn(
        "handle_response_async is deprecated. Use AsyncResponseHandler instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    async def _handle():
        if custom_response:
            return await sync_to_async(custom_response)(request, instance)
        
        serialized = await serialize_model_instance_async(instance)
        return serialized
    
    return _handle()


# Legacy async hook executor
execute_hook_async = sync_to_async(execute_hook)


# Export legacy functions for backward compatibility
__all__ = [
    'convert_foreign_keys_async',
    'get_all_objects_async', 
    'get_object_or_404_async',
    'execute_hook_async',
    'serialize_model_instance_async',
    'handle_response_async'
]
