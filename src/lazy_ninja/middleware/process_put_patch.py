from asgiref.sync import sync_to_async, iscoroutinefunction

from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

class ProcessPutPatchMiddleware(MiddlewareMixin):
    """
    Middleware to handle PUT/PATCH requests as POST for form data processing
    Works for both synchronous and asynchronous request handlers
    """
    
    def _core_processing(self, request: HttpRequest) -> None:
        if request.method in ("PUT", "PATCH") and request.content_type != "application/json":
            original_method = request.method
            request.method = "POST"
            request.META["REQUEST_METHOD"] = "POST"
            
            request._load_post_and_files()
            
            request.method = original_method
            request.META["REQUEST_METHOD"] = original_method

    def __call__(self, request: HttpRequest):
        if iscoroutinefunction(self.get_response):
            async def async_handler(request):
                await sync_to_async(self._core_processing)(request)
                response = await self.get_response(request)
                return response
            return async_handler(request)
        else:
            self._core_processing(request)
            response = self.get_response(request)
            return response