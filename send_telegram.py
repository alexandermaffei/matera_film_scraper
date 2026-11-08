#!/usr/bin/env python3
"""
Scrape dei cinema di Matera + invio del messaggio compatto su Telegram.
Usato dal workflow GitHub `telegram-weekly.yml` (sostituisce lo scenario Make).

Variabili richieste:
  TELEGRAM_BOT_TOKEN   token del bot
  TELEGRAM_CHAT_ID     una o più chat separate da virgola
  TMDB_ACCESS_TOKEN    per link IMDb e voti (opzionale ma consigliato)
"""

import os
import sys

import requests

from app import _scrape_all_cinemas
from scraper import format_telegram_message


def send(token: str, chat_id: str, text: str) -> None:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Telegram {response.status_code}: {response.text}")


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_ids = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]
    if not token or not chat_ids:
        print("TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID sono obbligatori", file=sys.stderr)
        return 1

    data = _scrape_all_cinemas()
    total = data.get("statistics", {}).get("total_films", 0)
    if not total:
        print("Nessun film trovato: messaggio non inviato", file=sys.stderr)
        return 1

    message = format_telegram_message(data)
    for chat_id in chat_ids:
        send(token, chat_id, message)
    print(f"Inviato a {len(chat_ids)} chat ({len(message)} caratteri, {total} film)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
