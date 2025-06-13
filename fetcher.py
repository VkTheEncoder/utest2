# utest2/fetcher.py

import logging
import requests
from config import API_BASE

# Make sure we never build URLs with “//”
BASE = API_BASE.rstrip("/")


def _split_episode_id(ep_id: str):
    """
    Split "slug?ep=123" → ("slug", {"ep": "123"})
    or just return (ep_id, {}) if there's no "?".
    """
    if "?" not in ep_id:
        return ep_id, {}
    slug, qs = ep_id.split("?", 1)
    params = dict(part.split("=",1) for part in qs.split("&") if "=" in part)
    return slug, params


def search_anime(query: str, page: int = 1):
    url = f"{BASE}/search"
    try:
        resp = requests.get(url, params={"q": query, "page": page}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("search_anime failed for %r: %s", query, e)
        return []

    data = resp.json().get("data", {}) or {}
    anime_list = data.get("animes", []) or []

    results = []
    for item in anime_list:
        if isinstance(item, str):
            slug = item
            title = slug.replace("-", " ").title()
            poster = ""
        elif isinstance(item, dict):
            slug   = item.get("id") or item.get("slug") or ""
            title  = item.get("name") or item.get("jname") or slug.replace("-", " ").title()
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
    slug = anime_id.strip()
    url  = f"{BASE}/anime/{slug}/episodes"

    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        logging.error("fetch_episodes request failed for %r: %s", anime_id, e)
        return []

    # fallback to ep=1 if there's no episode list
    if resp.status_code == 404:
        return [{"episodeId": f"{slug}?ep=1", "number": "1", "title": None}]

    try:
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_episodes status error for %r: %s", anime_id, e)
        return []

    full = resp.json()
    items = full.get("data", {}).get("episodes", []) or []
    episodes = []
    for it in items:
        if not isinstance(it, dict):
            continue
        num = str(it.get("number") or "").strip()
        eid = str(it.get("episodeId") or it.get("id") or "").strip()
        if not num or not eid:
            continue
        episodes.append({
            "episodeId": eid,
            "number":    num,
            "title":     it.get("title")
        })

    # sort by N
    try:
        episodes.sort(key=lambda e: int(e["number"]))
    except Exception:
        pass

    return episodes


def fetch_sources_and_referer(episode_id: str):
    slug, params = _split_episode_id(episode_id)
    url = f"{BASE}/episode/{slug}/sources"

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_sources_and_referer failed for %r: %s", episode_id, e)
        return [], ""

    payload = resp.json()
    blob    = payload.get("data", {}) or {}

    # Try the usual key, then common alternates, then top-level list
    sources = blob.get("sources") or blob.get("streams") or blob.get("videos")
    if not sources:
        if isinstance(blob, list):
            sources = blob
        else:
            # log the entire JSON so you can see what shape it really is
            logging.warning(
                "No ‘sources’ found for %s\nURL: %s\nJSON: %r",
                episode_id, resp.url, payload
            )
            sources = []

    referer = blob.get("referer", "")
    return sources, referer


def fetch_tracks(episode_id: str):
    slug, params = _split_episode_id(episode_id)
    url = f"{BASE}/episode/{slug}/tracks"

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("fetch_tracks failed for %r: %s", episode_id, e)
        return []

    payload = resp.json()
    tracks  = payload.get("data", []) or []
    return tracks
