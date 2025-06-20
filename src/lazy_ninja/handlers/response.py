from typing import Any, Type, Optional, Callable
from asgiref.sync import sync_to_async

from ninja import Schema

from ..utils import serialize_model_instance, serialize_model_instance_async


class BaseResponseHandler:
    """Base class for response handlers."""
    
    def _apply_custom_response(self, custom_response: Callable, request: Any, instance: Any) -> Any:
        """Apply custom response if provided."""
        if custom_response:
            return custom_response(request, instance)
        return None


class SyncResponseHandler(BaseResponseHandler):
    """Handles response formatting for sync routes."""
    
    def handle_response(
        self, 
        instance: Any, 
        schema: Type[Schema], 
        custom_response: Optional[Callable] = None, 
        request: Any = None
    ) -> Any:
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
        custom_result = self._apply_custom_response(custom_response, request, instance)
        if custom_result is not None:
            return custom_result
        
        serialized = serialize_model_instance(instance)
        return serialized


class AsyncResponseHandler(BaseResponseHandler):
    """Handles response formatting for async routes."""
    
    async def handle_response(
        self, 
        instance: Any, 
        schema: Type[Schema], 
        custom_response: Optional[Callable] = None, 
        request: Any = None
    ) -> Any:
        """
        Async version of handle_response that uses serialize_model_instance_async
        
        Args:
            instance: The instance to format
            schema: The schema to use for validation
            custom_response: Optional custom response handler
            request: Optional request object for custom response
            
        Returns:
            Formatted response
        """
        if custom_response:
            return await sync_to_async(custom_response)(request, instance)
        
        serialized = await serialize_model_instance_async(instance)
        return serialized