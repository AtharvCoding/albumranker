# myapp/views.py
from django.shortcuts import render
from . import spotify_utils
import math 
from django.utils.html import escapejs
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.urls import reverse
import json



def landing(request):
    return render(request, "myapp/landing.html")


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
    except Exception as e:
        error = str(e)

    return render(request, "myapp/album_detail.html", {"album": album, "tracks": tracks, "error": error})

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
        "est_total": est_total
    }

    return render(request, "myapp/rank.html", context)


@require_http_methods(["POST"])
def rank_submit(request, album_id):
    """
    Accepts final ordered track IDs + comparisons from client.
    Validates and stores in session, then returns redirect to result page.
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
    for tid in ordered_ids:
        if tid not in server_ids:
            return HttpResponseBadRequest(f"Invalid track ID: {tid}")

    # Store result in session (keyed by album)
    session_key = f"ranking_state_{album_id}"
    request.session[session_key] = {
        "album_id": album_id,
        "ordered_ids": ordered_ids,
        "comparisons": data.get("comparisons", []),
        "comparisons_count": data.get("comparisons_count", len(data.get("comparisons", []))),
        "completed": True,
    }
    request.session.modified = True

    redirect_url = reverse("myapp:rank_result", kwargs={"album_id": album_id})
    return JsonResponse({"redirect": redirect_url})


def rank_result(request, album_id):
    """
    Shows final ranked list if present in session.
    If not present, render a friendly 'no result yet' page with a CTA to start ranking.
    """
    session_key = f"ranking_state_{album_id}"
    state = request.session.get(session_key)

    # fetch album/tracks for context (used in both cases)
    try:
        album = spotify_utils.get_album(album_id)
        raw_tracks = spotify_utils.get_album_tracks(album_id)
    except Exception as e:
        return render(request, "myapp/error.html", {"message": f"Failed to fetch album: {e}"})

    if not state or not state.get("completed"):
        # No stored result -> show a friendly page with CTA
        context = {
            "album": album,
            "tracks_count": len(raw_tracks),
            "album_id": album_id,
        }
        return render(request, "myapp/rank_result_missing.html", context)

    # Normal path: build ordered tracks and render result
    track_map = {t["id"]: t for t in raw_tracks if t.get("id")}
    ordered_tracks = [track_map[i] for i in state["ordered_ids"] if i in track_map]

    context = {
        "album": album,
        "ordered_tracks": ordered_tracks,
        "comparisons_count": state.get("comparisons_count", 0)
    }
    return render(request, "myapp/rank_result.html", context)