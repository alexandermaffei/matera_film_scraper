#!/usr/bin/env python3
"""Utilities to enrich scraped films with Trakt metadata."""

from __future__ import annotations

from typing import Dict, Any, List, Tuple

from trakt_search import search_movie, TraktError


class MissingTraktCredentials(RuntimeError):
    """Raised when the Trakt client ID is not configured."""


def enrich_with_trakt(cinemas: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Enrich the scraped programmazione with Trakt data.

    Args:
        cinemas: list of cinema dicts as produced by ``scrape_cinema``

    Returns:
        A dictionary keyed by film title with aggregated metadata (tmdb, imdb, etc.).
    """
    # Collect unique films keeping references to the original film entries
    films: Dict[str, Dict[str, Any]] = {}

    for cinema in cinemas:
        cinema_name = cinema.get("cinema")
        for film in cinema.get("film", []):
            title = film.get("titolo")
            if not title:
                continue

            entry = films.setdefault(
                title,
                {
                    "title": title,
                    "cinema": set(),
                    "programmazione": [],
                    "tmdb": None,
                    "imdb": None,
                    "imdb_url": None,
                    "trakt": None,
                    "refs": [],
                },
            )

            entry["cinema"].add(cinema_name)
            entry["programmazione"].extend(film.get("programmazione", []))
            entry["refs"].append(film)

    # Query Trakt for each film and propagate ids
    for title, info in films.items():
        try:
            results = search_movie(title, limit=1)
        except ValueError as exc:
            raise MissingTraktCredentials(str(exc)) from exc
        except TraktError as exc:
            info["trakt_error"] = {"status": exc.status_code, "message": exc.message}
            continue

        if not results:
            info["trakt_error"] = {"status": None, "message": "not found"}
            continue

        result = results[0]
        info["tmdb"] = result.get("tmdb")
        info["imdb"] = result.get("imdb")
        info["trakt"] = result.get("trakt") or result.get("slug")
        if info["imdb"]:
            info["imdb_url"] = f"https://www.imdb.com/title/{info['imdb']}/"

        # Propagate metadata back to the original film entries
        for film_ref in info["refs"]:
            if info["tmdb"]:
                film_ref["tmdb"] = info["tmdb"]
            if info["trakt"]:
                film_ref["trakt"] = info["trakt"]
            if info["imdb"]:
                film_ref["imdb"] = info["imdb"]
            if info["imdb_url"]:
                film_ref["imdb_url"] = info["imdb_url"]

    # Convert cinema set to sorted list and drop refs before returning
    aggregated: Dict[str, Dict[str, Any]] = {}
    for title, info in films.items():
        aggregated[title] = {
            "title": info["title"],
            "cinema": sorted(info["cinema"]),
            "programmazione": info["programmazione"],
            "tmdb": info.get("tmdb"),
            "imdb": info.get("imdb"),
            "imdb_url": info.get("imdb_url"),
            "trakt": info.get("trakt"),
        }
        if "trakt_error" in info:
            aggregated[title]["trakt_error"] = info["trakt_error"]

    return aggregated

