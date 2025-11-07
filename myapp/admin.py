from django.contrib import admin
from .models import SavedAlbum, AlbumRanking


@admin.register(SavedAlbum)
class SavedAlbumAdmin(admin.ModelAdmin):
    list_display = ['album_name', 'artist_name', 'user', 'saved_at']
    list_filter = ['saved_at']
    search_fields = ['album_name', 'artist_name', 'user__username', 'album_id']
    readonly_fields = ['saved_at']


@admin.register(AlbumRanking)
class AlbumRankingAdmin(admin.ModelAdmin):
    list_display = ['spotify_album_id', 'user', 'comparisons_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['spotify_album_id', 'user__username']
    readonly_fields = ['created_at']
