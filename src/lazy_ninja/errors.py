from typing import Dict, Any, Optional
import traceback
import logging
from django.conf import settings

from django.db import DatabaseError
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
    ObjectDoesNotExist,
    SynchronousOnlyOperation,
)
from django.http import JsonResponse
from ninja.errors import HttpError
from colorama import Fore, Style, init

init(autoreset=True) 
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
        return {
            "error": {
                "status_code": self.status_code,
                "message": self.message,
                "type": self.__class__.__name__,
            }
        }

class SynchronousOperationError(LazyNinjaError):
    status_code = 500
    default_message = "Synchronous operation called from async context - use sync_to_async"

class DatabaseOperationError(LazyNinjaError):
    status_code = 500
    default_message = "Database operation failed"

class ValidationError(LazyNinjaError):
    status_code = 400
    default_message = "Validation error"

class NotFoundError(LazyNinjaError):
    status_code = 404
    default_message = "Resource not found"

class PermissionDeniedError(LazyNinjaError):
    status_code = 403
    default_message = "Permission denied"

class BadRequestError(LazyNinjaError):
    status_code = 400
    default_message = "Bad request"

class ConflictError(LazyNinjaError):
    status_code = 409
    default_message = "Resource conflict"

def handle_exception(exc: Exception) -> JsonResponse:
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
        error = LazyNinjaError(str(exc))

    print(
        f"{Fore.RED + Style.BRIGHT}[LazyNinja ❌] {error.__class__.__name__}: "
        f"{Fore.YELLOW}{error.message}"
    )
    
    if getattr(settings, "DEBUG", False):
        print(Fore.LIGHTBLACK_EX + traceback.format_exc())

    return JsonResponse(error.to_dict(), status=error.status_code)


async def handle_exception_async(exc: Exception) -> JsonResponse:
    return handle_exception(exc)