import logging
import traceback

from django.http import JsonResponse
from django.core.exceptions import SynchronousOnlyOperation

from ..errors import LazyNinjaError, SynchronousOperationError

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware:
    """
    Middleware to handle exceptions and return JSON response.
    
    This middleware catches all exceptions raised during request processing
    and returns appropriate JSON responses with status codes.
    
    Usage:
        Add this middleware to your MIDDLEWARE setting in settings.py
        
        MIDDLEWARE = [
            # ... other middleware
            'lazy_ninja.middleware.ErrorHandlingMiddleware',
            # ... other middleware
        ]
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        """Handle synchronous requests."""
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            return self.handle_exception(exc)
        
    async def __acall__(self, request):
        """Handle asynchronous requests."""
        try:
            response = await self.get_response(request)
            return response
        except Exception as exc:
            return self.handle_exception(exc)
        
    def handle_exception(self, exc: Exception) -> JsonResponse:
        """
        Handle exceptions and return appropriate JSON responses.
        
        Args:
            exc: The exception to handle.
            
        Returns:
            A JsonResponse with appropriate status code and error details.
        """
        if isinstance(exc, SynchronousOnlyOperation):
            error = SynchronousOperationError()
        elif isinstance(exc, LazyNinjaError):
            error = exc
        else:
            logger.error(f"Unexpected error: {str(exc)}")
            logger.error(traceback.format_exc())
            error = LazyNinjaError(str(exc))
            
        return JsonResponse(
            error.to_dict(),
            status=error.status_code
        )