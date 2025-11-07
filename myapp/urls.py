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
    # Authentication
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    # My Music
    path("my-music/", views.my_music, name="my_music"),
    # API endpoints
    path("api/save-album/<str:album_id>/", views.save_album, name="save_album"),
    path("api/unsave-album/<str:album_id>/", views.unsave_album, name="unsave_album"),
    path("api/save-ranking/<str:album_id>/", views.save_ranking, name="save_ranking"),
]
