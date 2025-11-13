#!/usr/bin/env python3
"""Esegue lo scraping dei cinema e arricchisce i film con link TMDB/IMDB via Trakt."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from scraper import CINEMA_URLS, scrape_cinema, format_telegram_message
from trakt_enrich import enrich_with_trakt, MissingTraktCredentials

OUTPUT_JSON = Path("programmazione_cinema_matera.json")
OUTPUT_ENRICHED = Path("programmazione_cinema_matera_with_trakt.json")


def ensure_trakt_credentials() -> None:
    if not os.getenv("TRAKT_CLIENT_ID"):
        raise SystemExit(
            "TRAKT_CLIENT_ID non impostata. Esegui `export TRAKT_CLIENT_ID=...` prima di lanciare lo script."
        )


def main() -> None:
    ensure_trakt_credentials()

    print("Inizio scraping dei cinema con arricchimento Trakt...\n")

    all_data: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "cinema": [],
    }

    # Scrape ciascun cinema
    for cinema_name, url in CINEMA_URLS.items():
        cinema_data = scrape_cinema(url, cinema_name)
        all_data["cinema"].append(cinema_data)
        print(f"- {cinema_name}: {len(cinema_data['film'])} film")

    # Salva dati raw
    OUTPUT_JSON.write_text(json.dumps(all_data, ensure_ascii=False, indent=2))

    print("\nRicerca su Trakt per ogni film...")
    try:
        aggregated = enrich_with_trakt(all_data["cinema"])
    except MissingTraktCredentials as exc:
        raise SystemExit(str(exc)) from exc

    for title, info in sorted(aggregated.items()):
        print(f"  ✅ {title}: TMDB {info.get('tmdb')} | IMDB {info.get('imdb')}")

    # Salva JSON arricchito
    enriched = {
        "timestamp": all_data.get("timestamp"),
        "films": aggregated,
    }
    OUTPUT_ENRICHED.write_text(json.dumps(enriched, ensure_ascii=False, indent=2))

    print(f"\nDati base salvati in {OUTPUT_JSON}")
    print(f"Dati arricchiti salvati in {OUTPUT_ENRICHED}")

    # Aggiorna messaggio Telegram
    telegram_msg = format_telegram_message(all_data)
    Path("messaggio_telegram.txt").write_text(telegram_msg)
    print("Messaggio Telegram aggiornato in messaggio_telegram.txt")


if __name__ == "__main__":
    main()
