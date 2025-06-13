# fetcher.py

import logging
import requests
from config import API_BASE

# Ensure no trailing slash so we never get “//” in our URLs
BASE = API_BASE.rstrip('/')

def _extract_id(raw_id):
    """
    Turn a Mongo-style ObjectId dict into its string, or else just str(raw_id).
    """
    if isinstance(raw_id, dict):
        for key in ("$oid", "id", "value"):
            if key in raw_id:
                return raw_id[key]
        return str(raw_id)
    return str(raw_id)

def _normalize_list_of_lists(raw):
    """
    Normalize search results shaped as [[id,name,poster,...], …]
    or list of dicts, into list of dicts with keys "id","name","poster".
    """
    out = []
    for item in raw:
        if isinstance(item, list) and len(item) >= 2:
            id_, name, *rest = item
            out.append({
                "id":     _extract_id(id_),
                "name":   name,
                "poster": rest[0] if rest else ""
            })
        elif isinstance(item, dict):
            item_id = _extract_id(item.get("id") or item.get("_id"))
            out.append({
                **item,
                "id":     item_id,
                "poster": item.get("poster", "")
            })
    return out

def search_anime(query: str, page: int = 1):
    """
    Search for anime by query string, returning a list of dicts
    with keys: id, name, poster.
    """
    url = f"{BASE}/search"
    try:
        resp = requests.get(url, params={"q": query, "page": page})
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("search_anime failed for query %r: %s", query, e)
        return []

    data = resp.json().get("data", [])
    raw  = list(data.values()) if isinstance(data, dict) else data
    return _normalize_list_of_lists(raw)

def fetch_episodes(anime_id: str):
    """
    Fetch /anime/<anime_id>/episodes and normalize to a list of
    dicts with keys: episodeId, number, title.
    """
    url = f"{BASE}/anime/{anime_id}/episodes"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_episodes failed for anime_id %r: %s", anime_id, e)
        return []

    raw = resp.json().get("data", []) or []
    episodes = []

    # Case A: dict mapping raw_id → info (info may be dict or primitive)
    if isinstance(raw, dict):
        for raw_id, info in raw.items():
            if isinstance(info, dict):
                number = info.get("number")
                title  = info.get("title")
            else:
                number = info
                title  = None
            episodes.append({
                "episodeId": _extract_id(raw_id),
                "number":    number,
                "title":     title,
            })

    # Case B: list of various shapes
    elif isinstance(raw, list):
        for item in raw:
            # B1: simple list of strings/ints
            if isinstance(item, (str, int)):
                episodes.append({
                    "episodeId": _extract_id(item),
                    "number":    None,
                    "title":     None,
                })

            # B2: nested list [ raw_id, number, title, … ]
            elif isinstance(item, list) and len(item) >= 3:
                raw_id, number, title = item[0], item[1], item[2]
                episodes.append({
                    "episodeId": _extract_id(raw_id),
                    "number":    number,
                    "title":     title,
                })

            # B3: list of dicts [{ episodeId, number, title, … }, …]
            elif isinstance(item, dict):
                raw_id = item.get("episodeId") or item.get("id") or item.get("_id")
                episodes.append({
                    "episodeId": _extract_id(raw_id),
                    "number":    item.get("number"),
                    "title":     item.get("title"),
                })

            else:
                logging.warning("Skipping unknown episode format: %r", item)

    else:
        logging.warning("Unexpected type for episodes data: %s", type(raw))

    return episodes

def fetch_sources_and_referer(episode_id: str):
    """
    Fetch video sources + referer for an episode.
    Returns: (sources_list, referer_str)
    """
    url = f"{BASE}/episode/{episode_id}/sources"
    resp = requests.get(url)
    resp.raise_for_status()
    blob = resp.json().get("data", {}) or {}
    return blob.get("sources", []), blob.get("referer", "")

def fetch_tracks(episode_id: str):
    """
    Fetch subtitle tracks for an episode.
    Returns list of track dicts.
    """
    url = f"{BASE}/episode/{episode_id}/tracks"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data or []
