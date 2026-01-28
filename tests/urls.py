from django.urls import path
from lazy_ninja.auth import register_auth_routes
from lazy_ninja.builder import DynamicAPI
from ninja import NinjaAPI

api = NinjaAPI()
register_auth_routes(api)

dynamic_api = DynamicAPI(api, is_async=False)  
dynamic_api.register_all_models()

urlpatterns = [
    path('api/', api.urls),
]
