# utest2/fetcher.py

import logging
import requests
import time
from config import API_BASE

# Ensure we never build URLs with a trailing “//”
BASE = API_BASE.rstrip("/")


def search_anime(query: str, page: int = 1, retries: int = 3, timeout: int = 15):
    """
    Search for anime by name via the HiAnime API, with retry on timeout.
    Returns a list of dicts:
      [ { "id": slug,
          "name": title,
          "url":  "https://hianimez.to/watch/{slug}",
          "poster": poster_url_or_empty_string
        }, … ]
    Raises requests.Timeout if all retry attempts time out.
    """
    url = f"{BASE}/search"
    params = {"q": query, "page": page}

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            break
        except requests.Timeout as e:
            logging.warning(
                "search_anime timeout for %r (attempt %d/%d)",
                query, attempt, retries
            )
            if attempt < retries:
                # exponential back-off: 1s, 2s, 4s…
                time.sleep(2 ** (attempt - 1))
                continue
            else:
                logging.error(
                    "search_anime timed out after %d attempts for %r",
                    retries, query
                )
                # let the Timeout bubble up so your handler can reply with an error
                raise
        except requests.RequestException as e:
            logging.error("search_anime failed for %r: %s", query, e)
            return []

    full_json   = resp.json()
    data        = full_json.get("data", {}) or {}
    anime_list  = data.get("animes", []) or []

    results = []
    for item in anime_list:
        if isinstance(item, str):
            slug   = item
            title  = slug.replace("-", " ").title()
            poster = ""
        elif isinstance(item, dict):
            slug   = item.get("id") or item.get("slug") or ""
            title  = (
                item.get("name")
                or item.get("jname")
                or slug.replace("-", " ").title()
            )
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
    Given an anime slug, fetch /anime/{slug}/episodes and return a list of dicts:
      [ { "episodeId": "<slug>?ep=N", "number": "N", "title": … }, … ]
    Falls back to a single-episode if that endpoint 404s.
    """
    slug = anime_id.strip()
    url  = f"{BASE}/anime/{slug}/episodes"

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

    full_json     = resp.json()
    episodes_data = full_json.get("data", {}).get("episodes", []) or []
    episodes      = []

    for item in episodes_data:
        if not isinstance(item, dict):
            continue
        num = str(item.get("number") or "").strip()
        eid = str(item.get("episodeId") or item.get("id") or "").strip()
        if not num or not eid:
            continue

        episodes.append({
            "episodeId": eid,
            "number":    num,
            "title":     item.get("title")
        })

    try:
        episodes.sort(key=lambda e: int(e["number"]))
    except Exception:
        pass

    return episodes


def fetch_sources_and_referer(episode_id: str):
    """
    Hit the HiAnime‐style source endpoint:
      GET /episode/sources
      ?animeEpisodeId=<slug>?ep=N
      &server=hd-2
      &category=sub
    Returns: (list_of_source_dicts, referer_str)
    """
    url = f"{BASE}/episode/sources"
    params = {
        "animeEpisodeId": episode_id,
        "server":         "hd-2",
        "category":       "sub"
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_sources_and_referer failed for %r: %s", episode_id, e)
        return [], ""

    data    = resp.json().get("data", {}) or {}
    sources = data.get("sources", [])
    referer = data.get("referer", "")

    return sources, referer


def fetch_tracks(episode_id: str):
    """
    Pull subtitle tracks from the same /episode/sources endpoint.
    Returns list of track dicts.
    """
    url = f"{BASE}/episode/sources"
    params = {
        "animeEpisodeId": episode_id,
        "server":         "hd-2",
        "category":       "sub"
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_tracks failed for %r: %s", episode_id, e)
        return []

    data   = resp.json().get("data", {}) or {}
    tracks = data.get("tracks", []) or []
    return tracks
