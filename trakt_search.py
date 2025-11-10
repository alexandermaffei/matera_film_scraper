#!/usr/bin/env python3
"""Utility per cercare film su Trakt e ottenere TMDB/IMDB ID."""

import os
import sys
import argparse
import requests
from typing import List, Dict, Any, Optional

TRAKT_API_URL = "https://api.trakt.tv"
TRAKT_API_VERSION = "2"

class TraktError(Exception):
    """Errore generico durante la chiamata a Trakt."""
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def get_trakt_client_id() -> str:
    """Recupera il client ID di Trakt dalle variabili d'ambiente.

    Returns:
        Il client ID come stringa.
        Solleva ValueError se non impostato.
    """
    client_id = os.getenv("TRAKT_CLIENT_ID")
    if not client_id:
        raise ValueError(
            "TRAKT_CLIENT_ID not set. Export it with `export TRAKT_CLIENT_ID=...`"
        )
    return client_id


def search_movie(query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Esegue una ricerca film su Trakt.

    Args:
        query: stringa da cercare (titolo del film)
        year: opzionale, anno per restringere la ricerca
        limit: numero massimo di risultati da restituire (default 10)

    Returns:
        Lista di risultati con informazioni su titolo, anno, tmdb, imdb, slug, score.
    """
    client_id = get_trakt_client_id()

    params = {
        "query": query,
        "type": "movie",
        "limit": limit,
    }
    if year:
        params["year"] = year

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "trakt-api-version": TRAKT_API_VERSION,
        "trakt-api-key": client_id,
    }

    response = requests.get(
        f"{TRAKT_API_URL}/search/movie",
        params=params,
        headers=headers,
        timeout=15,
    )

    if not response.ok:
        raise TraktError(response.status_code, response.text)

    data = response.json()

    results = []
    for item in data:
        movie = item.get("movie", {})
        ids = movie.get("ids", {})
        results.append(
            {
                "title": movie.get("title"),
                "year": movie.get("year"),
                "slug": ids.get("slug"),
                "tmdb": ids.get("tmdb"),
                "imdb": ids.get("imdb"),
                "trakt": ids.get("trakt"),
                "score": item.get("score"),
            }
        )
    return results


def format_results(results: List[Dict[str, Any]]) -> str:
    """Formatter for CLI output."""
    if not results:
        return "No results found."

    lines = []
    for idx, res in enumerate(results, start=1):
        title = res.get("title")
        year = res.get("year")
        tmdb = res.get("tmdb")
        imdb = res.get("imdb")
        slug = res.get("slug")
        score = res.get("score")

        lines.append(f"{idx}. {title} ({year})")
        if score is not None:
            lines.append(f"   Score: {score}")
        lines.append(f"   Trakt slug: {slug}")
        if tmdb:
            lines.append(f"   TMDB: https://www.themoviedb.org/movie/{tmdb}")
        else:
            lines.append("   TMDB: n/a")
        if imdb:
            lines.append(f"   IMDB: https://www.imdb.com/title/{imdb}/")
        else:
            lines.append("   IMDB: n/a")
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search movies on Trakt")
    parser.add_argument("query", help="Movie title to search")
    parser.add_argument("--year", type=int, help="Optional release year")
    parser.add_argument("--limit", type=int, default=5, help="Number of results")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    try:
        args = parse_args(argv)
        results = search_movie(query=args.query, year=args.year, limit=args.limit)
        print(format_results(results))
        return 0
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1
    except TraktError as exc:
        print(f"Trakt API error ({exc.status_code}): {exc.message}")
        return 1
    except Exception as exc:  # pragma: no cover - just in case
        print(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
