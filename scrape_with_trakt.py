#!/usr/bin/env python3
"""Scraping cinema + matching TMDB (id, IMDb, locandina). Trakt è opzionale e non sovrascrive gli id."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from scraper import (
    CINEMA_URLS,
    scrape_cinema,
    format_telegram_message,
    report_window_dates,
    REPORT_WINDOW_DAYS,
    apply_report_window,
)
from trakt_enrich import enrich_with_trakt, MissingTraktCredentials
from tmdb_enrich import enrich_films_from_tmdb, MissingTmdbCredentials

OUTPUT_JSON = Path("programmazione_cinema_matera.json")
OUTPUT_ENRICHED = Path("programmazione_cinema_matera_with_trakt.json")


def main() -> None:
    print("Inizio scraping dei cinema con matching TMDB...\n")

    all_data: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "report_window": {},
        "cinema": [],
    }
    allowed_dates = report_window_dates(REPORT_WINDOW_DAYS)
    all_data["report_window"] = {
        "days": REPORT_WINDOW_DAYS,
        "from": allowed_dates[0],
        "to": allowed_dates[-1],
    }

    for cinema_name, url in CINEMA_URLS.items():
        cinema_data = scrape_cinema(url, cinema_name)
        cinema_data = apply_report_window(cinema_data, allowed_dates)
        all_data["cinema"].append(cinema_data)
        print(f"- {cinema_name}: {len(cinema_data['film'])} film")

    OUTPUT_JSON.write_text(json.dumps(all_data, ensure_ascii=False, indent=2))

    print("\nMatching TMDB (titolo + anno / uscita Italia, poi IMDb e locandina)...")
    try:
        matched = enrich_films_from_tmdb(all_data["cinema"])
    except MissingTmdbCredentials as exc:
        raise SystemExit(
            f"{exc}\nEsporta TMDB_ACCESS_TOKEN (Bearer v4) oppure TMDB_API_KEY."
        ) from exc

    for title, info in sorted(matched.items()):
        print(
            f"  ✅ {title}: TMDB {info.get('tmdb')} | IMDB {info.get('imdb')} | score {info.get('tmdb_match_score')}"
        )

    aggregated = None
    if os.getenv("TRAKT_CLIENT_ID"):
        print("\nTrakt opzionale (non sovrascrive id TMDB)...")
        try:
            aggregated = enrich_with_trakt(all_data["cinema"])
        except MissingTraktCredentials as exc:
            print(f"  Trakt saltato: {exc}")

    OUTPUT_JSON.write_text(json.dumps(all_data, ensure_ascii=False, indent=2))

    films_out = aggregated or {
        title: {
            "title": info.get("title") or title,
            "tmdb": info.get("tmdb"),
            "imdb": info.get("imdb"),
            "imdb_url": info.get("imdb_url"),
            "poster_url": info.get("poster_url"),
        }
        for title, info in matched.items()
    }
    enriched = {
        "timestamp": all_data.get("timestamp"),
        "films": films_out,
    }
    OUTPUT_ENRICHED.write_text(json.dumps(enriched, ensure_ascii=False, indent=2))

    print(f"\nDati salvati in {OUTPUT_JSON}")
    print(f"Indice film salvato in {OUTPUT_ENRICHED}")

    telegram_msg = format_telegram_message(all_data)
    Path("messaggio_telegram.txt").write_text(telegram_msg, encoding="utf-8")
    print(f"Messaggio Telegram aggiornato in messaggio_telegram.txt ({len(telegram_msg)} caratteri)")


if __name__ == "__main__":
    main()
