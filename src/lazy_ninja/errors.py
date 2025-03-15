from typing import Dict, Any, Optional
import traceback
import logging

from django.db import DatabaseError
from django.core.exceptions import ValidationError as DjangoValidationError, ObjectDoesNotExist, SynchronousOnlyOperation
from django.http import JsonResponse

from ninja.errors import HttpError

logger = logging.getLogger(__name__)

class LazyNinjaError(Exception):
    """Base exception class for Lazy Ninja errors."""
    status_code = 500
    default_message = "An unexpected error occurred"

    def __init__(self, message: Optional[str] = None, status_code: Optional[int] = None):
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary for JSON response."""
        return {
            "error": {
                "status_code": self.status_code,
                "message": self.message,
                "type": self.__class__.__name__
            }
        }

class SynchronousOperationError(LazyNinjaError):
    """Exception raised when a synchronous operation is called from an async context."""
    status_code = 500
    default_message = "Synchronous operation called from async context - use sync_to_async"

class DatabaseOperationError(LazyNinjaError):
    """Exception raised when a database operation fails."""
    status_code = 500
    default_message = "Database operation failed"

class ValidationError(LazyNinjaError):
    """Exception raised when validation fails."""
    status_code = 400
    default_message = "Validation error"

class NotFoundError(LazyNinjaError):
    """Exception raised when a resource is not found."""
    status_code = 404
    default_message = "Resource not found"

class PermissionDeniedError(LazyNinjaError):
    """Exception raised when a user doesn't have permission for an operation."""
    status_code = 403
    default_message = "Permission denied"

class BadRequestError(LazyNinjaError):
    """Exception raised for malformed requests."""
    status_code = 400
    default_message = "Bad request"

class ConflictError(LazyNinjaError):
    """Exception raised when there's a conflict with the current state."""
    status_code = 409
    default_message = "Resource conflict"

def handle_exception(exc: Exception) -> JsonResponse:
    """
    Handle exceptions and return appropriate JSON responses.

    Args:
        exc: The exception to handle.

    Returns:
        A JsonResponse with appropriate status code and error details.
    """
    if isinstance(exc, ObjectDoesNotExist) or "matches the given query" in str(exc):
        error = NotFoundError(str(exc))
    
    elif isinstance(exc, PermissionError) or "permission" in str(exc).lower():
        error = PermissionDeniedError(str(exc))
    
    elif isinstance(exc, DjangoValidationError) or isinstance(exc, ValueError):
        error = ValidationError(str(exc))
    
    elif isinstance(exc, DatabaseError):
        error = DatabaseOperationError(str(exc))
    
    elif isinstance(exc, SynchronousOnlyOperation):
        error = SynchronousOperationError()
    
    elif isinstance(exc, HttpError):
        error = LazyNinjaError(str(exc), exc.status_code)
    
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

async def handle_exception_async(exc: Exception) -> JsonResponse:
    """
    Async version of handle_exception.

    Args:
        exc: The exception to handle.

    Returns:
        A JsonResponse with appropriate status code and error details.
    """
    return handle_exception(exc)