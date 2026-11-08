#!/usr/bin/env python3
"""Matching TMDB per i film in sala a Matera.

Non usa il primo risultato della search né gli id Trakt (spesso sbagliati).
Preferisce uscite recenti / teatrali IT, poi locandina IT e imdb_id da external_ids.
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
STOPWORDS = {
    "the",
    "el",
    "la",
    "lo",
    "il",
    "gli",
    "le",
    "i",
    "un",
    "una",
    "uno",
    "a",
    "an",
    "di",
    "del",
    "della",
    "dei",
    "delle",
    "of",
}


class MissingTmdbCredentials(RuntimeError):
    """Sollevato quando manca TMDB_ACCESS_TOKEN e TMDB_API_KEY."""


def get_tmdb_access_token() -> str:
    return (os.getenv("TMDB_ACCESS_TOKEN") or os.getenv("TMDB_API_READ_TOKEN") or "").strip()


def get_tmdb_api_key() -> str:
    return (os.getenv("TMDB_API_KEY") or "").strip()


def _require_tmdb_auth() -> Tuple[Optional[str], Optional[str]]:
    token = get_tmdb_access_token()
    key = get_tmdb_api_key()
    if not token and not key:
        raise MissingTmdbCredentials(
            "TMDB_ACCESS_TOKEN (Bearer) o TMDB_API_KEY non impostata."
        )
    return token or None, key or None


def _tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    token, key = _require_tmdb_auth()
    query = dict(params or {})
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif key:
        query["api_key"] = key
    response = requests.get(f"{TMDB_API_URL}{path}", params=query, headers=headers, timeout=20)
    if not response.ok:
        print(f"  TMDB {path} → HTTP {response.status_code}")
        return None
    return response.json()


def normalize_film_title(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("&", " e ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [t for t in text.split() if t not in STOPWORDS and (len(t) > 1 or t.isdigit())]
    return " ".join(tokens).strip()


def _token_set(value: str) -> set:
    norm = normalize_film_title(value)
    return set(norm.split()) if norm else set()


def jaccard(a: str, b: str) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return 1.0 if normalize_film_title(a) == normalize_film_title(b) and normalize_film_title(a) else 0.0
    inter = len(sa & sb)
    return inter / (len(sa) + len(sb) - inter)


def title_similarity(query: str, title: str, original_title: str = "") -> float:
    q = normalize_film_title(query)
    t = normalize_film_title(title)
    o = normalize_film_title(original_title)
    if q and (q == t or (o and q == o)):
        return 1.0
    scores = [jaccard(query, title)]
    if original_title:
        scores.append(jaccard(query, original_title))
    return max(scores)


def recency_score(release_date: Optional[str], now: Optional[datetime] = None) -> float:
    if not release_date:
        return 0.15
    try:
        d = datetime.strptime(release_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.15
    now = now or datetime.now(timezone.utc)
    days = (now - d).total_seconds() / 86400
    if -90 <= days <= 540:
        return 1.0
    if 540 < days <= 900:
        return 0.45
    if -180 <= days < -90:
        return 0.6
    return 0.08


def score_candidate(query: str, movie: Dict[str, Any], now: Optional[datetime] = None) -> float:
    sim = title_similarity(query, movie.get("title") or "", movie.get("original_title") or "")
    recency = recency_score(movie.get("release_date"), now)
    pop = min(1.0, math.log10((movie.get("popularity") or 1) + 1) / 2.5)
    return sim * 0.62 + recency * 0.28 + pop * 0.1


def _search_movies(query: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"query": query, "language": "it-IT", "include_adult": "false"}
    if year:
        params["year"] = year
        params["primary_release_year"] = year
    data = _tmdb_get("/search/movie", params)
    results = (data or {}).get("results") or []
    return [m for m in results if m.get("id")]


def _pick_poster_url(posters: List[Dict[str, Any]], fallback_path: Optional[str] = None) -> Optional[str]:
    def lang_rank(iso: Optional[str]) -> int:
        if iso == "it":
            return 0
        if iso == "en":
            return 1
        if iso is None:
            return 2
        return 3

    ranked = sorted(
        posters or [],
        key=lambda p: (lang_rank(p.get("iso_639_1")), -(p.get("vote_average") or 0)),
    )
    path = (ranked[0].get("file_path") if ranked else None) or fallback_path
    if not path:
        return None
    return f"{TMDB_IMAGE_BASE}{path}"


def _has_recent_italy_theatrical(movie_id: int, now: Optional[datetime] = None) -> bool:
    data = _tmdb_get(f"/movie/{movie_id}/release_dates")
    results = (data or {}).get("results") or []
    it = next((r for r in results if r.get("iso_3166_1") == "IT"), None)
    if not it:
        return False
    now = now or datetime.now(timezone.utc)
    for rd in it.get("release_dates") or []:
        if rd.get("type") not in (None, 3):
            continue
        raw = rd.get("release_date") or ""
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        days = (now - d).total_seconds() / 86400
        if -90 <= days <= 540:
            return True
    return False


def resolve_tmdb_film(title: str) -> Optional[Dict[str, Any]]:
    """Risolve un titolo in sala → tmdb, imdb, poster, voto."""
    query = str(title or "").strip()
    if not query:
        return None

    now = datetime.now(timezone.utc)
    year = now.year
    seen = set()
    candidates: List[Dict[str, Any]] = []
    for y in (year, year - 1, None):
        for movie in _search_movies(query, y):
            mid = movie["id"]
            if mid in seen:
                continue
            seen.add(mid)
            candidates.append(movie)

    if not candidates:
        return None

    ranked = sorted(
        ((score_candidate(query, m, now), m) for m in candidates),
        key=lambda x: x[0],
        reverse=True,
    )
    best_score, best = ranked[0]
    if best_score < 0.42:
        return None

    if len(ranked) > 1:
        second_score, second = ranked[1]
        if best_score - second_score < 0.08:
            if _has_recent_italy_theatrical(second["id"], now) and not _has_recent_italy_theatrical(
                best["id"], now
            ):
                best_score, best = second_score, second

    details = _tmdb_get(
        f"/movie/{best['id']}",
        {
            "language": "it-IT",
            "append_to_response": "images,external_ids",
            "include_image_language": "it,en,null",
        },
    ) or {}

    imdb_id = ((details.get("external_ids") or {}).get("imdb_id") or "").strip() or None
    posters = (details.get("images") or {}).get("posters") or []
    poster_url = _pick_poster_url(posters, details.get("poster_path") or best.get("poster_path"))
    rating = details.get("vote_average")
    voto = float(rating) if isinstance(rating, (int, float)) and rating > 0 else None

    return {
        "tmdb": int(best["id"]),
        "title": details.get("title") or best.get("title") or query,
        "original_title": details.get("original_title") or best.get("original_title"),
        "imdb": imdb_id,
        "imdb_url": f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else None,
        "poster_url": poster_url,
        "voto_tmdb": voto,
        "tmdb_match_score": round(best_score, 4),
    }


def enrich_films_from_tmdb(cinemas: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Arricchisce in place ogni film con tmdb/imdb/poster/voto. Cache per titolo."""
    _require_tmdb_auth()
    cache: Dict[str, Optional[Dict[str, Any]]] = {}
    matched = 0
    total = 0

    for cinema in cinemas:
        for film in cinema.get("film", []):
            title = (film.get("titolo") or "").strip()
            if not title:
                continue
            total += 1
            if title not in cache:
                try:
                    cache[title] = resolve_tmdb_film(title)
                except MissingTmdbCredentials:
                    raise
                except Exception as exc:
                    print(f"  TMDB match fallito per «{title}»: {exc}")
                    cache[title] = None
            match = cache[title]
            if not match:
                continue
            matched += 1
            film["tmdb"] = match["tmdb"]
            film["imdb"] = match.get("imdb")
            film["imdb_url"] = match.get("imdb_url")
            film["poster_url"] = match.get("poster_url")
            film["tmdb_match_score"] = match.get("tmdb_match_score")
            if match.get("voto_tmdb") is not None:
                film["voto_tmdb"] = match["voto_tmdb"]

    print(f"  TMDB: matchati {matched}/{total} titoli unici={len(cache)}")
    return {title: info for title, info in cache.items() if info}


def enrich_tmdb_ratings(cinemas: List[Dict[str, Any]], search_missing: bool = True) -> None:
    """Compat: ora fa matching TMDB completo (id, IMDb, poster, voto), non solo il rating."""
    if not search_missing:
        # Solo voto se l'id c'è già — comunque ricalcoliamo via resolve per coerenza.
        pass
    enrich_films_from_tmdb(cinemas)


# Alias usati dai test / script vecchi
def search_tmdb_movie_id(title: str, api_key: str = "", year: Optional[int] = None) -> Optional[int]:
    match = resolve_tmdb_film(title)
    return match["tmdb"] if match else None
