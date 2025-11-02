# myapp/spotify_utils.py
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()  # ensure .env at project root is loaded

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in .env")

_token_cache = {"token": None, "expires_at": 0.0}


def get_app_token():
    """Return a valid Spotify Client Credentials token (cached)."""
    if _token_cache["token"] and _token_cache["expires_at"] - time.time() > 10:
        return _token_cache["token"]

    url = "https://accounts.spotify.com/api/token"
    data = {"grant_type": "client_credentials"}
    resp = requests.post(url, data=data, auth=(CLIENT_ID, CLIENT_SECRET), timeout=10)
    resp.raise_for_status()
    j = resp.json()
    token = j.get("access_token")
    expires_in = j.get("expires_in", 3600)
    if not token:
        raise RuntimeError(f"Failed to fetch Spotify token: {j}")
    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + float(expires_in)
    return token


def search_albums(query, limit=8):
    """
    Search Spotify albums using a free-form query. Returns a list of simplified album dicts.
    Each dict: {id, name, artist, image, release_date, total_tracks}
    """
    token = get_app_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.spotify.com/v1/search"
    params = {"q": query, "type": "album", "limit": limit}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("albums", {}).get("items", [])
    results = []
    for it in items:
        results.append({
            "id": it.get("id"),
            "name": it.get("name"),
            "artist": it["artists"][0]["name"] if it.get("artists") else "",
            "image": (it.get("images") or [{}])[0].get("url", ""),
            "release_date": it.get("release_date"),
            "total_tracks": it.get("total_tracks"),
        })
    return results


def get_album(album_id):
    """
    Get album metadata by Spotify album id.
    Returns simplified album dict (same structure as above) or None.
    """
    token = get_app_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/albums/{album_id}"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    it = resp.json()
    return {
        "id": it.get("id"),
        "name": it.get("name"),
        "artist": it["artists"][0]["name"] if it.get("artists") else "",
        "image": (it.get("images") or [{}])[0].get("url", ""),
        "release_date": it.get("release_date"),
        "total_tracks": it.get("total_tracks"),
    }


def get_album_tracks(album_id):
    """
    Return list of tracks for album_id. Each track: {id, name, duration_ms, track_number}
    """
    token = get_app_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    params = {"limit": 50, "offset": 0}
    tracks = []
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
        if not data.get("next"):
            break
        params["offset"] += params["limit"]
    return tracks
