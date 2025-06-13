# utest2/fetcher.py

import logging
import requests
from config import API_BASE

# Strip any trailing “/” so we never get “//” in our URLs
BASE = API_BASE.rstrip("/")


def _split_episode_id(ep_id: str):
    """
    Split an episode_id like "slug?ep=123" into
    ("slug", {"ep": "123"}). If there's no "?", returns (ep_id, {}).
    """
    if "?" not in ep_id:
        return ep_id, {}
    slug, qs = ep_id.split("?", 1)
    params = {}
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            params[k] = v
    return slug, params


def search_anime(query: str, page: int = 1):
    """
    Search for anime by name via the HiAnime API.
    Returns a list of dicts:
      [ { "id": slug,
          "name": title,
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
    data = full_json.get("data", {}) or {}
    anime_list = data.get("animes", []) or []

    results = []
    for item in anime_list:
        if isinstance(item, str):
            slug = item
            title = slug.replace("-", " ").title()
            poster = ""
        elif isinstance(item, dict):
            slug = item.get("id") or item.get("slug") or ""
            title = item.get("name") or item.get("jname") or slug.replace("-", " ").title()
            poster = item.get("poster") or item.get("image") or ""
        else:
            continue

        if not slug:
            continue

        results.append({
            "id":     slug,
            "name":   title,
            "url":    f"https://hianimez.to/watch/{slug}",
            "poster": poster
        })

    return results


def fetch_episodes(anime_id: str):
    """
    Given an anime slug, fetch /anime/{slug}/episodes and return:
      [ { "episodeId": "<slug>?ep=N", "number": "N", "title": <subtitle or None> }, … ]
    Falls back to a single-episode if the list endpoint 404s.
    """
    slug = anime_id.strip()
    url = f"{BASE}/anime/{slug}/episodes"

    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        logging.error("fetch_episodes request failed for %r: %s", anime_id, e)
        return []

    if resp.status_code == 404:
        return [{"episodeId": f"{slug}?ep=1", "number": "1", "title": None}]

    try:
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_episodes status error for %r: %s", anime_id, e)
        return []

    full_json = resp.json()
    episodes_data = full_json.get("data", {}).get("episodes", []) or []
    episodes = []

    for item in episodes_data:
        if not isinstance(item, dict):
            continue

        ep_num = str(item.get("number") or "").strip()
        ep_id = str(item.get("episodeId") or item.get("id") or "").strip()
        if not ep_num or not ep_id:
            continue

        episodes.append({
            "episodeId": ep_id,
            "number":    ep_num,
            "title":     item.get("title")
        })

    # Sort numerically just in case
    try:
        episodes.sort(key=lambda e: int(e["number"]))
    except Exception:
        pass

    return episodes


def fetch_sources_and_referer(episode_id: str):
    """
    Fetch /episode/{slug}/sources?ep=N by splitting off the "?ep=" part.
    Returns (sources_list, referer_str).
    """
    slug, params = _split_episode_id(episode_id)
    url = f"{BASE}/episode/{slug}/sources"

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_sources_and_referer failed for %r: %s", episode_id, e)
        return [], ""

    blob = resp.json().get("data", {}) or {}
    return blob.get("sources", []), blob.get("referer", "")


def fetch_tracks(episode_id: str):
    """
    Fetch /episode/{slug}/tracks?ep=N by splitting off the "?ep=" part.
    Returns list of subtitle track dicts.
    """
    slug, params = _split_episode_id(episode_id)
    url = f"{BASE}/episode/{slug}/tracks"

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_tracks failed for %r: %s", episode_id, e)
        return []

    return resp.json().get("data", []) or []
