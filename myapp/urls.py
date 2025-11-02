# myapp/urls.py
from django.urls import path
from . import views

app_name = "myapp"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("search/", views.search_page, name="search"),
    path("album/<str:album_id>/", views.album_detail, name="album_detail"),
]
