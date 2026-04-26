from django.urls import path
from .views import RouteView, health_check

urlpatterns = [
    path("route/", RouteView.as_view(), name="route"),
    path("health/", health_check, name="health"),
]
