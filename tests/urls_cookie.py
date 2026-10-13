from django.urls import path
from ninja import NinjaAPI

from lazy_ninja.builder import DynamicAPI


api = NinjaAPI(urls_namespace="cookie-auth-tests")
DynamicAPI(api, auth=True, is_async=False, exclude={"tests": True}).init()


@api.post("/protected")
def protected(request):
    return {"user": request.auth.pk}


urlpatterns = [path("api/", api.urls)]
