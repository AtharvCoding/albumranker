# myapp/views.py
from django.shortcuts import render
from . import spotify_utils

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
