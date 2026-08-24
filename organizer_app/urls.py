from django.urls import path
from . import views

app_name = "organizer_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/scan/", views.api_scan, name="api_scan"),
    path("api/organize/", views.api_organize, name="api_organize"),
    path("api/undo/", views.api_undo, name="api_undo"),
    path("api/history/", views.api_history, name="api_history"),
    path("api/create-demo/", views.api_create_demo, name="api_create_demo"),
]
