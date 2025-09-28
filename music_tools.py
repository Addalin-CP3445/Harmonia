# music_tools.py
from typing import Any, List, Dict
import os, logging, requests
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException

load_dotenv()
logger = logging.getLogger("harmonia.spotify")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# Map our buckets to search queries for artists/tracks
MOOD_QUERIES = {
    "focus":    {"artist_q": "lofi beats",    "track_q": "lofi focus"},
    "energize": {"artist_q": "workout hits",  "track_q": "energetic dance"},
    "calm":     {"artist_q": "ambient chill", "track_q": "calm ambient"},
}

def _client() -> Spotify:
    sess = requests.Session()
    sess.trust_env = False  # ignore OS/corporate proxies
    cid = os.getenv("SPOTIFY_CLIENT_ID")
    sec = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not cid or not sec:
        raise RuntimeError("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not set")
    auth = SpotifyClientCredentials(client_id=cid, client_secret=sec, requests_session=sess)
    sp = Spotify(
        auth_manager=auth,
        requests_session=sess,
        requests_timeout=15,
        retries=3,
        status_forcelist=(429, 500, 502, 503, 504),
    )
    return sp

def _pack_tracks(items) -> List[Dict[str, Any]]:
    out = []
    for t in items or []:
        out.append({
            "title": t.get("name"),
            "artists": ", ".join(a.get("name") for a in t.get("artists", [])),
            "album": (t.get("album") or {}).get("name"),
            "preview_url": t.get("preview_url"),
            "spotify_url": (t.get("external_urls") or {}).get("spotify"),
            "album_image": ((t.get("album") or {}).get("images") or [{"url": None}])[0]["url"],
        })
    return out

def _find_seed_artists(sp: Spotify, bucket: str, n: int = 3) -> List[str]:
    q = MOOD_QUERIES.get(bucket, MOOD_QUERIES["focus"])["artist_q"]
    res = sp.search(q=q, type="artist", limit=10)
    items = (res.get("artists") or {}).get("items") or []
    ids = [a["id"] for a in items if a.get("id")]
    return ids[:max(1, min(n, 5))]  # 1..5

def _top_tracks_for_artists(sp: Spotify, artist_ids: List[str], limit_per_artist: int = 5) -> List[Dict[str, Any]]:
    tracks = []
    for aid in artist_ids[:5]:
        # Use a common market to ensure playable previews
        res = sp.artist_top_tracks(aid, country="US")
        items = res.get("tracks", [])[:limit_per_artist]
        tracks.extend(items)
        if len(tracks) >= 20:
            break
    return tracks

def _search_tracks(sp: Spotify, bucket: str, limit: int) -> List[Dict[str, Any]]:
    q = MOOD_QUERIES.get(bucket, MOOD_QUERIES["focus"])["track_q"]
    res = sp.search(q=q, type="track", limit=limit)
    return (res.get("tracks") or {}).get("items", [])

def recommend_tracks(
    bucket: str,          # <-- change callsite: pass preset.bucket instead of seed_genres
    energy: float,        # kept for future when recommendations work
    valence: float,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    sp = _client()
    logger.info("Recs for bucket=%s (energy=%.2f valence=%.2f)", bucket, energy, valence)

    # ---------- Try #1: /recommendations with seed_artists ----------
    try:
        artist_ids = _find_seed_artists(sp, bucket, n=3)
        if artist_ids:
            rec = sp.recommendations(seed_artists=artist_ids, limit=limit)
            items = rec.get("tracks", [])
            if items:
                return _pack_tracks(items)
            logger.warning("No tracks from /recommendations with seed_artists.")
        else:
            logger.warning("No seed artists found via search.")
    except SpotifyException as e:
        logger.warning("Recommendations 404/err: %s", e)

    # ---------- Try #2: Artist top-tracks ----------
    try:
        if not locals().get("artist_ids"):
            artist_ids = _find_seed_artists(sp, bucket, n=3)
        top_items = _top_tracks_for_artists(sp, artist_ids, limit_per_artist=10)
        if top_items:
            return _pack_tracks(top_items[:limit])
        logger.warning("No top-tracks found for seed artists.")
    except SpotifyException as e:
        logger.warning("Top-tracks err: %s", e)

    # ---------- Try #3: Plain track search ----------
    try:
        items = _search_tracks(sp, bucket, limit=limit)
        if items:
            return _pack_tracks(items)
        logger.error("Track search returned empty.")
    except SpotifyException as e:
        logger.error("Search err: %s", e)

    return []
