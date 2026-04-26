from django.urls import path, include

urlpatterns = [
    path("", include("route.urls")),
]
