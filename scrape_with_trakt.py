#!/usr/bin/env python3
"""Esegue lo scraping dei cinema e arricchisce i film con link TMDB/IMDB via Trakt."""

import json
import os
from pathlib import Path
from typing import Dict, Any

from scraper import CINEMA_URLS, scrape_cinema, format_telegram_message
from trakt_search import search_movie, TraktError

OUTPUT_JSON = Path("programmazione_cinema_matera.json")
OUTPUT_ENRICHED = Path("programmazione_cinema_matera_with_trakt.json")


def ensure_trakt_credentials() -> str:
    client_id = os.getenv("TRAKT_CLIENT_ID")
    if not client_id:
        raise SystemExit(
            "TRAKT_CLIENT_ID non impostata. Esegui `export TRAKT_CLIENT_ID=...` prima di lanciare lo script."
        )
    return client_id


def main() -> None:
    ensure_trakt_credentials()

    print("Inizio scraping dei cinema con arricchimento Trakt...\n")

    all_data: Dict[str, Any] = {
        "cinema": [],
        "timestamp": None,
        "statistics": {},
        "films": {}
    }

    # Scrape ciascun cinema
    for cinema_name, url in CINEMA_URLS.items():
        cinema_data = scrape_cinema(url, cinema_name)
        all_data["cinema"].append(cinema_data)
        print(f"- {cinema_name}: {len(cinema_data['film'])} film")

    # Salva dati raw
    OUTPUT_JSON.write_text(json.dumps(all_data, ensure_ascii=False, indent=2))

    # Catalogo film unici
    unique_films: Dict[str, Dict[str, Any]] = {}
    for cinema in all_data["cinema"]:
        for film in cinema["film"]:
            title = film.get("titolo")
            if not title:
                continue
            if title not in unique_films:
                unique_films[title] = {
                    "title": title,
                    "cinema": [cinema["cinema"]],
                    "programmazione": film.get("programmazione", []),
                    "trakt": None,
                    "tmdb": None,
                    "imdb": None,
                    "imdb_url": None,
                    "entries": [film],
                }
            else:
                unique_films[title]["cinema"].append(cinema["cinema"])
                unique_films[title]["programmazione"].extend(film.get("programmazione", []))
                unique_films[title]["entries"].append(film)

    print("\nRicerca su Trakt per ogni film...")

    for title, film_info in unique_films.items():
        try:
            results = search_movie(title, limit=1)
        except TraktError as exc:
            print(f"  ! Errore Trakt per '{title}': {exc.status_code} {exc.message}")
            continue

        if not results:
            print(f"  - Nessun risultato per '{title}'")
            continue

        result = results[0]
        film_info["trakt"] = result.get("slug")
        film_info["tmdb"] = result.get("tmdb")
        film_info["imdb"] = result.get("imdb")
        film_info["imdb_url"] = (
            f"https://www.imdb.com/title/{film_info['imdb']}/" if film_info["imdb"] else None
        )

        for entry in film_info.get("entries", []):
            entry["trakt"] = film_info["trakt"]
            entry["tmdb"] = film_info["tmdb"]
            entry["imdb"] = film_info["imdb"]
            entry["imdb_url"] = film_info["imdb_url"]

        print(
            f"  ✅ {title}: TMDB {film_info['tmdb']} | IMDB {film_info['imdb']}"
        )

    # Salva JSON arricchito
    enriched_films = {}
    for title, info in unique_films.items():
        enriched_films[title] = {
            "title": info["title"],
            "cinema": info["cinema"],
            "programmazione": info["programmazione"],
            "trakt": info["trakt"],
            "tmdb": info["tmdb"],
            "imdb": info["imdb"],
            "imdb_url": info["imdb_url"],
        }

    enriched = {
        "timestamp": all_data.get("timestamp"),
        "films": enriched_films,
    }
    OUTPUT_ENRICHED.write_text(json.dumps(enriched, ensure_ascii=False, indent=2))

    print(f"\nDati base salvati in {OUTPUT_JSON}")
    print(f"Dati arricchiti salvati in {OUTPUT_ENRICHED}")

    # Mostra messaggio Telegram per comodità
    telegram_msg = format_telegram_message({"cinema": all_data["cinema"], "timestamp": all_data.get("timestamp")})
    Path("messaggio_telegram.txt").write_text(telegram_msg)
    print("Messaggio Telegram aggiornato in messaggio_telegram.txt")


if __name__ == "__main__":
    main()
