# myapp/urls.py
from django.urls import path
from . import views

app_name = "myapp"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("search/", views.search_page, name="search"),
    path("album/<str:album_id>/", views.album_detail, name="album_detail"),
    path("rank/<str:album_id>/", views.rank, name="rank"),
    path("rank/<str:album_id>/submit/", views.rank_submit, name="rank_submit"),
    path("rank/<str:album_id>/result/", views.rank_result, name="rank_result"),
]
