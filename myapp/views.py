# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from . import spotify_utils
from .models import SavedAlbum, AlbumRanking
import math 
from django.utils.html import escapejs
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.db import transaction
import json



def landing(request):
    return render(request, "myapp/landing.html")


def signup(request):
    """Simple sign-up view that creates User and logs them in."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            next_url = request.GET.get('next', reverse('myapp:landing'))
            return redirect(next_url)
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    pass


def search_page(request):
    """
    GET parameter: q (query string). If provided, call spotify and return list of albums.
    """
    query = request.GET.get("q", "").strip()
    albums = []
    error = None
    if query:
        try:
            albums = spotify_utils.search_albums(query, limit=8)
        except Exception as e:
            error = str(e)
    context = {"query": query, "albums": albums, "error": error}
    return render(request, "myapp/search.html", context)


def album_detail(request, album_id):
    """
    Show album metadata + tracklist (with human-readable durations).
    """
    album = None
    tracks = []
    error = None
    saved = False
    try:
        album = spotify_utils.get_album(album_id)
        if album:
            raw_tracks = spotify_utils.get_album_tracks(album_id)

            # Ensure tracks are sorted by track_number
            raw_tracks.sort(key=lambda x: x.get("track_number") or 0)

            # Convert duration_ms -> "M:SS" and build simplified track dict
            for t in raw_tracks:
                ms = t.get("duration_ms") or 0
                total_seconds = ms // 1000
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                formatted = f"{minutes}:{str(seconds).zfill(2)}"
                tracks.append({
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "duration": formatted,
                    "track_number": t.get("track_number"),
                })
            
            # Check if album is saved for authenticated user
            if request.user.is_authenticated:
                saved = SavedAlbum.objects.filter(user=request.user, album_id=album_id).exists()
    except Exception as e:
        error = str(e)

    return render(request, "myapp/album_detail.html", {
        "album": album, 
        "tracks": tracks, 
        "error": error,
        "saved": saved,
        "album_id": album_id
    })

def rank(request, album_id):
    """
    GET /rank/<album_id>/
    - Fetch album metadata and tracks from spotify_utils
    - Format durations to M:SS
    - Render rank.html with album and tracks passed in context
    - NOTE: No session creation or server-side ranking here (client-driven)
    """

    try:
        album = spotify_utils.get_album(album_id)
        raw_tracks = spotify_utils.get_album_tracks(album_id)
    except Exception as e:
        return render(
            request,
            "myapp/error.html",
            {"message": f"Failed to load album details: {e}"}
        )

    # Sort and format track list
    raw_tracks.sort(key=lambda x: x.get("track_number") or 0)
    tracks = []
    for t in raw_tracks:
        ms = t.get("duration_ms") or 0
        total_seconds = ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        tracks.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "duration": f"{minutes}:{str(seconds).zfill(2)}",
            "track_number": t.get("track_number"),
        })

    # Estimate total comparisons for UI
    n = len(tracks)
    est_total = int(n * math.log2(max(2, n))) if n > 1 else 0

    # Safe JSON for embedding in template
    tracks_json = json.dumps(tracks).replace("</", "<\\/")  # escape </script> safety

    context = {
        "album": {
            "id": album.get("id"),
            "name": album.get("name"),
            "artist": (
                album.get("artist")
                or (album.get("artists")[0]["name"] if album.get("artists") else "Unknown Artist")
            ),
            "image": album.get("image"),
            "release_date": album.get("release_date", "")
        },
        "tracks": tracks,
        "tracks_json": tracks_json,  # safe JSON string for template
        "est_total": est_total,
        "user_authenticated": request.user.is_authenticated,
    }

    return render(request, "myapp/rank.html", context)


@require_http_methods(["POST"])
def rank_submit(request, album_id):
    """
    Accepts final ordered track IDs + comparisons from client.
    Validates and stores in session, then returns redirect to result page.
    Optionally saves to DB if user is authenticated and save_after_submit is True.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")

    ordered_ids = data.get("ordered_ids")
    if not isinstance(ordered_ids, list) or not ordered_ids:
        return HttpResponseBadRequest("Missing ordered_ids")

    # Get the official track list for the album
    try:
        raw_tracks = spotify_utils.get_album_tracks(album_id)
    except Exception as e:
        return HttpResponseBadRequest(f"Couldn't fetch album tracks: {e}")

    server_ids = {t.get("id") for t in raw_tracks if t.get("id")}
    # Validate all submitted IDs are from the album
    if len(ordered_ids) != len(server_ids):
        return HttpResponseBadRequest(f"Track count mismatch: expected {len(server_ids)}, got {len(ordered_ids)}")
    
    # Check for duplicates
    if len(ordered_ids) != len(set(ordered_ids)):
        return HttpResponseBadRequest("Duplicate track IDs found")
    
    for tid in ordered_ids:
        if tid not in server_ids:
            return HttpResponseBadRequest(f"Invalid track ID: {tid}")

    # Store result in session (keyed by album)
    session_key = f"ranking_state_{album_id}"
    comparisons = data.get("comparisons", [])
    comparisons_count = data.get("comparisons_count", len(comparisons))
    
    request.session[session_key] = {
        "album_id": album_id,
        "ordered_ids": ordered_ids,
        "comparisons": comparisons,
        "comparisons_count": comparisons_count,
        "completed": True,
    }
    request.session.modified = True

    # Optional: Save to DB if user is authenticated and save_after_submit is True
    ranking_id = None
    if request.user.is_authenticated and data.get("save_after_submit", False):
        try:
            with transaction.atomic():
                # Get or create SavedAlbum
                album_data = spotify_utils.get_album(album_id)
                saved_album, _ = SavedAlbum.objects.get_or_create(
                    user=request.user,
                    album_id=album_id,
                    defaults={
                        "album_name": album_data.get("name", ""),
                        "artist_name": album_data.get("artist", ""),
                        "cover_image": album_data.get("image", ""),
                    }
                )
                
                # Create AlbumRanking
                ranking = AlbumRanking.objects.create(
                    user=request.user,
                    album=saved_album,
                    spotify_album_id=album_id,
                    ordered_ids=ordered_ids,
                    comparisons=comparisons,
                    comparisons_count=comparisons_count,
                )
                ranking_id = ranking.id
        except Exception as e:
            # Log error but don't fail the request
            pass

    redirect_url = reverse("myapp:rank_result", kwargs={"album_id": album_id})
    return JsonResponse({"redirect": redirect_url, "ranking_id": ranking_id})


def rank_result(request, album_id):
    """
    Shows final ranked list. Checks DB first (if user authenticated), then session.
    If not present, render a friendly 'no result yet' page with a CTA to start ranking.
    """
    ordered_ids = None
    comparisons_count = 0
    saved = False
    
    # First, check for AlbumRanking in DB (if user is authenticated)
    if request.user.is_authenticated:
        ranking = AlbumRanking.objects.filter(
            user=request.user, 
            spotify_album_id=album_id
        ).order_by('-created_at').first()
        
        if ranking:
            ordered_ids = ranking.ordered_ids
            comparisons_count = ranking.comparisons_count
        
        # Check if album is saved
        saved = SavedAlbum.objects.filter(user=request.user, album_id=album_id).exists()
    
    # Fallback to session if no DB ranking found
    if not ordered_ids:
        session_key = f"ranking_state_{album_id}"
        state = request.session.get(session_key)
        if state and state.get("completed"):
            ordered_ids = state.get("ordered_ids")
            comparisons_count = state.get("comparisons_count", 0)

    # fetch album/tracks for context (used in all cases)
    try:
        album = spotify_utils.get_album(album_id)
        raw_tracks = spotify_utils.get_album_tracks(album_id)
    except Exception as e:
        return render(request, "myapp/error.html", {"message": f"Failed to fetch album: {e}"})

    if not ordered_ids:
        # No stored result -> show a friendly page with CTA
        context = {
            "album": album,
            "tracks_count": len(raw_tracks),
            "album_id": album_id,
            "saved": saved,
        }
        return render(request, "myapp/rank_result_missing.html", context)

    # Normal path: build ordered tracks and render result
    track_map = {t["id"]: t for t in raw_tracks if t.get("id")}
    ordered_tracks = []
    for tid in ordered_ids:
        if tid in track_map:
            track = track_map[tid].copy()
            # Format duration
            ms = track.get("duration_ms", 0)
            total_seconds = ms // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            track["duration_formatted"] = f"{minutes}:{str(seconds).zfill(2)}"
            ordered_tracks.append(track)

    context = {
        "album": album,
        "ordered_tracks": ordered_tracks,
        "comparisons_count": comparisons_count,
        "saved": saved,
        "album_id": album_id,
        "ordered_ids_json": json.dumps(ordered_ids),  # Pass for export functionality
    }
    return render(request, "myapp/rank_result.html", context)


@login_required
@require_http_methods(["POST"])
def save_album(request, album_id):
    """
    POST /api/save-album/<str:album_id>/
    Create or update SavedAlbum for request.user.
    If ordered_ids present, create an AlbumRanking tied to that SavedAlbum.
    """
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    
    # Try to get album from Spotify, fallback to posted metadata
    album_data = None
    try:
        album_data = spotify_utils.get_album(album_id)
    except Exception:
        # Use posted metadata as fallback
        album_data = {
            "name": data.get("album_name", ""),
            "artist": data.get("artist_name", ""),
            "image": data.get("cover_image", ""),
        }
    
    if not album_data:
        return HttpResponseBadRequest("Could not fetch album data")
    
    try:
        with transaction.atomic():
            # Create or update SavedAlbum
            saved_album, created = SavedAlbum.objects.get_or_create(
                user=request.user,
                album_id=album_id,
                defaults={
                    "album_name": album_data.get("name", ""),
                    "artist_name": album_data.get("artist", ""),
                    "cover_image": album_data.get("image", ""),
                }
            )
            
            # Update if it already existed
            if not created:
                saved_album.album_name = album_data.get("name", saved_album.album_name)
                saved_album.artist_name = album_data.get("artist", saved_album.artist_name)
                saved_album.cover_image = album_data.get("image", saved_album.cover_image)
                saved_album.save()
            
            ranking_id = None
            # If ordered_ids present, create an AlbumRanking
            ordered_ids = data.get("ordered_ids")
            if ordered_ids:
                # Validate ordered_ids
                try:
                    raw_tracks = spotify_utils.get_album_tracks(album_id)
                    server_ids = {t.get("id") for t in raw_tracks if t.get("id")}
                    
                    if len(ordered_ids) != len(server_ids):
                        return HttpResponseBadRequest(f"Track count mismatch")
                    if len(ordered_ids) != len(set(ordered_ids)):
                        return HttpResponseBadRequest("Duplicate track IDs found")
                    for tid in ordered_ids:
                        if tid not in server_ids:
                            return HttpResponseBadRequest(f"Invalid track ID: {tid}")
                except Exception as e:
                    return HttpResponseBadRequest(f"Could not validate tracks: {e}")
                
                # Create AlbumRanking
                ranking = AlbumRanking.objects.create(
                    user=request.user,
                    album=saved_album,
                    spotify_album_id=album_id,
                    ordered_ids=ordered_ids,
                    comparisons=data.get("comparisons", []),
                    comparisons_count=data.get("comparisons_count", 0),
                )
                ranking_id = ranking.id
            
            return JsonResponse({
                "success": True,
                "created": created,
                "saved_album_id": saved_album.id,
                "ranking_id": ranking_id,
            })
    except Exception as e:
        return HttpResponseBadRequest(f"Error saving album: {str(e)}")


@login_required
@require_http_methods(["POST"])
def unsave_album(request, album_id):
    """
    POST /api/unsave-album/<str:album_id>/
    Delete SavedAlbum (and optionally associated AlbumRanking entries).
    """
    try:
        saved_album = SavedAlbum.objects.get(user=request.user, album_id=album_id)
        # Optionally delete associated rankings
        AlbumRanking.objects.filter(user=request.user, spotify_album_id=album_id).delete()
        saved_album.delete()
        return JsonResponse({"success": True})
    except SavedAlbum.DoesNotExist:
        return HttpResponseNotFound("Album not found in saved albums")


@login_required
@require_http_methods(["POST"])
def save_ranking(request, album_id):
    """
    POST /api/save-ranking/<str:album_id>/
    Save ordered_ids and comparisons to AlbumRanking, optionally create/link SavedAlbum if not exists.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")
    
    ordered_ids = data.get("ordered_ids")
    if not isinstance(ordered_ids, list) or not ordered_ids:
        return HttpResponseBadRequest("Missing ordered_ids")
    
    # Validate ordered_ids
    try:
        raw_tracks = spotify_utils.get_album_tracks(album_id)
        server_ids = {t.get("id") for t in raw_tracks if t.get("id")}
        
        if len(ordered_ids) != len(server_ids):
            return HttpResponseBadRequest(f"Track count mismatch")
        if len(ordered_ids) != len(set(ordered_ids)):
            return HttpResponseBadRequest("Duplicate track IDs found")
        for tid in ordered_ids:
            if tid not in server_ids:
                return HttpResponseBadRequest(f"Invalid track ID: {tid}")
    except Exception as e:
        return HttpResponseBadRequest(f"Could not validate tracks: {e}")
    
    try:
        with transaction.atomic():
            # Get or create SavedAlbum
            album_data = spotify_utils.get_album(album_id)
            saved_album, _ = SavedAlbum.objects.get_or_create(
                user=request.user,
                album_id=album_id,
                defaults={
                    "album_name": album_data.get("name", ""),
                    "artist_name": album_data.get("artist", ""),
                    "cover_image": album_data.get("image", ""),
                }
            )
            
            # Create AlbumRanking
            ranking = AlbumRanking.objects.create(
                user=request.user,
                album=saved_album,
                spotify_album_id=album_id,
                ordered_ids=ordered_ids,
                comparisons=data.get("comparisons", []),
                comparisons_count=data.get("comparisons_count", 0),
            )
            
            return JsonResponse({
                "success": True,
                "ranking_id": ranking.id,
            })
    except Exception as e:
        return HttpResponseBadRequest(f"Error saving ranking: {str(e)}")


@login_required
def my_music(request):
    """
    GET /my-music/
    Renders myapp/my_music.html listing user's SavedAlbums with most recent AlbumRanking preview.
    """
    saved_albums = SavedAlbum.objects.filter(user=request.user).select_related().prefetch_related()
    
    # Get most recent ranking for each album
    albums_with_rankings = []
    for saved_album in saved_albums:
        latest_ranking = AlbumRanking.objects.filter(
            user=request.user,
            spotify_album_id=saved_album.album_id
        ).order_by('-created_at').first()
        
        albums_with_rankings.append({
            "saved_album": saved_album,
            "latest_ranking": latest_ranking,
        })
    
    context = {
        "albums_with_rankings": albums_with_rankings,
    }
    return render(request, "myapp/my_music.html", context)