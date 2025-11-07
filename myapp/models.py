from django.db import models
from django.contrib.auth.models import User


class SavedAlbum(models.Model):
    """Album saved by a user to their collection."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_albums")
    album_id = models.CharField(max_length=255, db_index=True)
    album_name = models.CharField(max_length=255)
    artist_name = models.CharField(max_length=255)
    cover_image = models.URLField(blank=True, null=True)
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [['user', 'album_id']]
        ordering = ['-saved_at']
        indexes = [
            models.Index(fields=['user', 'album_id']),
        ]

    def __str__(self):
        return f"{self.album_name} by {self.artist_name} (saved by {self.user.username})"


class AlbumRanking(models.Model):
    """A ranking of tracks for an album."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    album = models.ForeignKey(SavedAlbum, on_delete=models.SET_NULL, null=True, blank=True, related_name='rankings')
    spotify_album_id = models.CharField(max_length=255, db_index=True)  # Duplicate for resilience
    ordered_ids = models.JSONField()  # List of track IDs in ranked order
    comparisons = models.JSONField(blank=True, default=list)  # Optional comparisons log
    comparisons_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['spotify_album_id', 'user', 'created_at']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"Ranking for {self.spotify_album_id} by {user_str} ({self.created_at})"
