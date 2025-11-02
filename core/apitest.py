
import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables from .env (project root)
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in .env")

# Simple in-memory token cache
_token_cache = {"token": None, "expires_at": 0.0}


def get_app_token():
    """
    Return a valid Spotify Client Credentials token.
    Caches token until expiry to avoid repeated requests.
    """
    # return cached token if still valid for at least 10s
    if _token_cache["token"] and _token_cache["expires_at"] - time.time() > 10:
        return _token_cache["token"]

    url = "https://accounts.spotify.com/api/token"
    data = {"grant_type": "client_credentials"}

    # requests can pass HTTP Basic auth with (client_id, client_secret)
    resp = requests.post(url, data=data, auth=(CLIENT_ID, CLIENT_SECRET), timeout=10)
    resp.raise_for_status()
    j = resp.json()
    token = j.get("access_token")
    expires_in = j.get("expires_in", 3600)  # seconds
    if not token:
        raise RuntimeError("Failed to fetch Spotify token: %s" % j)

    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + float(expires_in)
    return token


def search_album_by_title_and_artist(album_title, artist_name, limit=1):
    """
    Search Spotify for an album using album title + artist name.
    Returns the first album dict (Spotify API object) or None.
    """
    token = get_app_token()
    headers = {"Authorization": f"Bearer {token}"}
    q = f"album:{album_title} artist:{artist_name}"
    url = "https://api.spotify.com/v1/search"
    params = {"q": q, "type": "album", "limit": limit}

    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("albums", {}).get("items", [])
    return items[0] if items else None


def get_album_tracks(album_id):
    """
    Given a Spotify album ID, return a list of simplified track dicts:
    {id, name, duration_ms, track_number}
    Handles Spotify pagination (requests up to 50 tracks per page).
    """
    token = get_app_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    tracks = []
    params = {"limit": 50, "offset": 0}

    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        for t in items:
            tracks.append({
                "id": t.get("id"),
                "name": t.get("name"),
                "duration_ms": t.get("duration_ms"),
                "track_number": t.get("track_number"),
            })
        # pagination: if 'next' is present, Spotify will include next url, otherwise break
        if not data.get("next"):
            break
        params["offset"] += params["limit"]
    return tracks


def format_duration(ms):
    """
    Convert milliseconds to M:SS string (e.g., 3:42).
    """
    if ms is None:
        return "?:??"
    total_seconds = int(ms) // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{str(seconds).zfill(2)}"


def pretty_print_album_and_tracks(album_title, artist_name):
    """
    High-level helper: search album, print key album info and the tracklist (with durations).
    """
    alb = search_album_by_title_and_artist(album_title, artist_name)
    if not alb:
        print(f"\n❌ No album found for: '{album_title}' — '{artist_name}'")
        return

    print("\nAlbum found:")
    print(f"  Title       : {alb.get('name')}")
    print(f"  Artist      : {alb['artists'][0]['name']}")
    images = alb.get("images", [])
    if images:
        print(f"  Cover (best): {images[0]['url']}")
    print(f"  Release date: {alb.get('release_date')}")
    print(f"  Total tracks: {alb.get('total_tracks')}\n")

    tracks = get_album_tracks(alb.get("id"))
    if not tracks:
        print("No tracks found for this album.")
        return

    print("Tracklist:")
    for i, t in enumerate(tracks, start=1):
        dur = format_duration(t.get("duration_ms"))
        print(f" {i:2}. {t.get('name')} — {dur}")


if __name__ == "__main__":
    try:
        artist = input("Enter artist name: ").strip()
        album = input("Enter album name: ").strip()
        if not artist or not album:
            print("Please provide both artist and album names.")
        else:
            pretty_print_album_and_tracks(album, artist)
    except requests.HTTPError as e:
        print("HTTP error while calling Spotify API:", e)
        try:
            print("Response content:", e.response.json())
        except Exception:
            pass
    except Exception as ex:
        print("Error:", ex)
