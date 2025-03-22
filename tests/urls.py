from django.urls import path
from lazy_ninja.builder import DynamicAPI
from ninja import NinjaAPI

api = NinjaAPI()

dynamic_api = DynamicAPI(api, is_async=False)  
dynamic_api.register_all_models()

urlpatterns = [
    path('api/', api.urls),
]
