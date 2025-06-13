# utest2/fetcher.py

import logging
import requests
from config import API_BASE

# Strip any trailing “/” so we never get “//” in our URLs
BASE = API_BASE.rstrip("/")


def search_anime(query: str, page: int = 1):
    """
    Search for anime by name via the HiAnime API.
    Returns a list of dicts:
      [ { "id": slug,
          "name": human‐readable title,
          "url": "https://hianimez.to/watch/{slug}",
          "poster": poster_url_or_empty_string
        }, … ]
    """
    url = f"{BASE}/search"
    params = {"q": query, "page": page}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("search_anime failed for %r: %s", query, e)
        return []

    full_json = resp.json()
    logger_data = full_json.get("data", {})
    anime_list = logger_data.get("animes", []) or []

    results = []
    for item in anime_list:
        # sometimes hianime returns a bare slug string
        if isinstance(item, str):
            slug = item
            title = slug.replace("-", " ").title()
            poster = ""
        elif isinstance(item, dict):
            slug   = item.get("id", "") or item.get("slug", "")
            title  = item.get("name") or item.get("jname") or slug.replace("-", " ").title()
            poster = item.get("poster") or item.get("image") or ""
        else:
            continue

        if not slug:
            continue

        anime_url = f"https://hianimez.to/watch/{slug}"
        results.append({
            "id":     slug,
            "name":   title,
            "url":    anime_url,
            "poster": poster
        })

    return results


def fetch_episodes(anime_id: str):
    """
    Given an anime slug (e.g. "raven-of-the-inner-palace-18168"), fetch
    /anime/{slug}/episodes and return a list of dicts:
      [ { "episodeId": "<slug>?ep=N",
          "number":    "N",
          "title":     <subtitle or None>
        }, … ]
    Falls back to a single episode if the list endpoint 404s.
    """
    slug       = anime_id.strip()
    ep_list_url = f"{BASE}/anime/{slug}/episodes"

    try:
        resp = requests.get(ep_list_url, timeout=10)
    except requests.RequestException as e:
        logging.error("fetch_episodes request failed for %r: %s", anime_id, e)
        return []

    # single‐episode fallback
    if resp.status_code == 404:
        return [{"episodeId": f"{slug}?ep=1", "number": "1", "title": None}]

    try:
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_episodes status error for %r: %s", anime_id, e)
        return []

    full_json     = resp.json()
    episodes_data = full_json.get("data", {}).get("episodes", []) or []
    episodes      = []

    for item in episodes_data:
        # each item is expected to be a dict with keys "number" and "episodeId"
        if not isinstance(item, dict):
            continue

        ep_num = str(item.get("number") or "").strip()
        ep_id  = str(item.get("episodeId") or item.get("id") or "").strip()
        if not ep_num or not ep_id:
            continue

        episodes.append({
            "episodeId": ep_id,
            "number":    ep_num,
            "title":     item.get("title")    # may be None
        })

    # Sort by numeric episode number just to be safe
    try:
        episodes.sort(key=lambda e: int(e["number"]))
    except Exception:
        pass

    return episodes


def fetch_sources_and_referer(episode_id: str):
    """
    Fetch /episode/{episode_id}/sources
    Returns a tuple (sources_list, referer_str)
    """
    url = f"{BASE}/episode/{episode_id}/sources"
    resp = requests.get(url)
    resp.raise_for_status()
    blob = resp.json().get("data", {}) or {}
    return blob.get("sources", []), blob.get("referer", "")


def fetch_tracks(episode_id: str):
    """
    Fetch /episode/{episode_id}/tracks
    Returns list of subtitle track dicts.
    """
    url = f"{BASE}/episode/{episode_id}/tracks"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json().get("data", []) or []
