from django.urls import path
from .views import home, remove_bg_api

urlpatterns = [
    path('', home, name='home'),
    path('api/remove-bg/', remove_bg_api),
]