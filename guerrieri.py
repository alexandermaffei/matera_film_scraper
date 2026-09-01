#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Programmazione CineTeatro Guerrieri dal sito ufficiale.

ComingSoon/Webtic a volte lasciano spettacoli fantasma dopo la Fine (es. Sheep in the Box
con orari 21:00 dal 4 settembre mentre in sala c'è già un altro film).
Il sito ufficiale ha Inizio, Fine, Date escluse e note tipo «unico spettacolo».
"""

from __future__ import annotations

import html as html_lib
import re
import unicodedata
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set

from bs4 import BeautifulSoup

GUERRIERI_OFFICIAL_URL = "https://cineteatroguerrieri.it/?page_id=759"
WEBTIC_GUERRIERI_LOCAL_ID = 5493

MONTH_ABBR = {
    "GEN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAG": 5,
    "GIU": 6,
    "LUG": 7,
    "AGO": 8,
    "SET": 9,
    "OTT": 10,
    "NOV": 11,
    "DIC": 12,
}

MONTH_FULL = {
    "GENNAIO": 1,
    "FEBBRAIO": 2,
    "MARZO": 3,
    "APRILE": 4,
    "MAGGIO": 5,
    "GIUGNO": 6,
    "LUGLIO": 7,
    "AGOSTO": 8,
    "SETTEMBRE": 9,
    "OTTOBRE": 10,
    "NOVEMBRE": 11,
    "DICEMBRE": 12,
}


def _year_for(month: int, day: int, today: Optional[date] = None) -> int:
    today = today or date.today()
    year = today.year
    cand = date(year, month, min(day, 28))
    # Fine stagione: se la data è più di ~4 mesi nel passato, è l'anno prossimo.
    if cand < today - timedelta(days=120):
        return year + 1
    return year


def parse_it_day_month(raw: str, today: Optional[date] = None) -> Optional[date]:
    """Parse '27 Ago', '01 Set', '07 09', '07/09'."""
    text = html_lib.unescape(str(raw or "")).strip()
    if not text:
        return None
    m = re.match(r"^(\d{1,2})\s+([A-Za-zÀ-ÿ]{3})$", text)
    if m:
        day = int(m.group(1))
        month = MONTH_ABBR.get(m.group(2).upper()[:3])
        if not month:
            return None
        try:
            return date(_year_for(month, day, today), month, day)
        except ValueError:
            return None
    m = re.match(r"^(\d{1,2})\s*[/\-\s]\s*(\d{1,2})$", text)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        if month < 1 or month > 12:
            return None
        try:
            return date(_year_for(month, day, today), month, day)
        except ValueError:
            return None
    return None


def parse_showtimes(raw: str) -> List[str]:
    """'18.30 - 21.00' → ['18:30', '21:00']."""
    times: List[str] = []
    for h, m in re.findall(r"\b(\d{1,2})[.:](\d{2})\b", str(raw or "")):
        hh, mm = int(h), int(m)
        if 0 <= hh < 24 and 0 <= mm < 60:
            times.append(f"{hh:02d}:{mm:02d}")
    # uniq preserve order
    seen: Set[str] = set()
    out: List[str] = []
    for t in times:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def parse_excluded_dates(raw: str, today: Optional[date] = None) -> List[date]:
    text = html_lib.unescape(str(raw or "")).strip()
    if not text:
        return []
    found: List[date] = []
    for chunk in re.split(r"[,;]+", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        parsed = parse_it_day_month(chunk, today)
        if parsed:
            found.append(parsed)
            continue
        # "07 09 08 09" coppie giorno mese
        nums = re.findall(r"\d{1,2}", chunk)
        if len(nums) >= 2 and len(nums) % 2 == 0:
            for i in range(0, len(nums), 2):
                parsed = parse_it_day_month(f"{nums[i]} {nums[i + 1]}", today)
                if parsed:
                    found.append(parsed)
    return found


def parse_unique_show_overrides(info: str, today: Optional[date] = None) -> Dict[str, List[str]]:
    """'MARTEDI' 1 SETTEMBRE UNICO SPETTACOLO ORE: 18.30' → { '2026-09-01': ['18:30'] }."""
    text = html_lib.unescape(str(info or ""))
    out: Dict[str, List[str]] = {}
    pattern = re.compile(
        r"(\d{1,2})\s+(" + "|".join(MONTH_FULL.keys()) + r")\b.*?UNICO SPETTACOLO ORE:\s*(\d{1,2}[.:]\d{2})",
        re.I | re.S,
    )
    for m in pattern.finditer(text):
        day = int(m.group(1))
        month = MONTH_FULL.get(m.group(2).upper())
        times = parse_showtimes(m.group(3))
        if not month or not times:
            continue
        try:
            d = date(_year_for(month, day, today), month, day)
        except ValueError:
            continue
        out[d.isoformat()] = times
    return out


def daterange_inclusive(start: date, end: date) -> List[date]:
    if end < start:
        return []
    days: List[date] = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def unescape_js_html_string(raw: str) -> str:
    text = raw.replace("\\/", "/")
    text = text.replace("\\n", "\n")
    text = text.replace("\\t", "\t")
    text = text.replace('\\"', '"')
    text = text.replace("\\'", "'")
    return text


def extract_embedded_listing_html(page_html: str) -> str:
    """La griglia film è in un innerHTML JS (Divi), non nel DOM statico."""
    m = re.search(
        r"outputContainer\.innerHTML\s*=\s*\"(.*?)\"\s*;\s*contentRendered",
        page_html,
        re.S,
    )
    if m:
        return unescape_js_html_string(m.group(1))
    m = re.search(r"innerHTML\s*=\s*\"(.*movie-main-title-elemento.*)\"\s*;\s*contentRendered", page_html, re.S)
    if m:
        return unescape_js_html_string(m.group(1))
    return page_html


def _label_value_boxes(article) -> Dict[str, str]:
    boxes: Dict[str, str] = {}
    for box in article.select(".date-box"):
        label = box.select_one(".date-box-label-elemento")
        value = box.select_one(".date-box-value")
        if not label or not value:
            continue
        boxes[label.get_text(strip=True).casefold()] = value.get_text(" ", strip=True)
    return boxes


def _orari_rows(article) -> Dict[str, str]:
    rows: Dict[str, str] = {}
    for block in article.select(".orari"):
        label = block.select_one(".info-label")
        value = block.select_one(".info-value")
        if not label or not value:
            continue
        rows[label.get_text(strip=True).rstrip(":").casefold()] = value.get_text(" ", strip=True)
    return rows


def parse_guerrieri_article(article, today: Optional[date] = None) -> Optional[Dict[str, Any]]:
    title_el = article.select_one(".movie-main-title-elemento")
    title = title_el.get_text(strip=True) if title_el else ""
    if not title:
        return None

    boxes = _label_value_boxes(article)
    if any("prossimamente" in k for k in boxes) or any("definire" in v.casefold() for v in boxes.values()):
        return None

    start = parse_it_day_month(boxes.get("inizio", ""), today)
    end = parse_it_day_month(boxes.get("fine", ""), today)
    if not start or not end:
        return None

    excluded = parse_excluded_dates(boxes.get("date escluse", ""), today)
    excluded_set = {d.isoformat() for d in excluded}

    info_rows = _orari_rows(article)
    default_times = parse_showtimes(info_rows.get("orario", ""))
    overrides = parse_unique_show_overrides(info_rows.get("info", ""), today)

    days = [
        d.isoformat()
        for d in daterange_inclusive(start, end)
        if d.isoformat() not in excluded_set
    ]
    if not days:
        return None

    return {
        "titolo": title,
        "days": days,
        "default_times": default_times,
        "overrides": overrides,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def parse_guerrieri_listing_html(html: str, today: Optional[date] = None) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(extract_embedded_listing_html(html), "html.parser")
    films: List[Dict[str, Any]] = []
    for article in soup.select("article.movie-preview-container-elemento"):
        parsed = parse_guerrieri_article(article, today)
        if parsed:
            films.append(parsed)
    return films


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    normalized = unicodedata.normalize("NFKD", title)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = normalized.lower()
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def _webtic_times_by_norm_title(webtic_films: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[str]]]:
    out: Dict[str, Dict[str, List[str]]] = {}
    for film in webtic_films:
        norm = _normalize_title(film.get("titolo", ""))
        if not norm:
            continue
        by_day: Dict[str, List[str]] = {}
        for prog in film.get("programmazione") or []:
            day = prog.get("data")
            times = list(prog.get("orari") or [])
            if day and times:
                by_day[day] = times
        if by_day:
            out[norm] = by_day
    return out


def _match_webtic_days(title: str, webtic_by_title: Dict[str, Dict[str, List[str]]]) -> Dict[str, List[str]]:
    norm = _normalize_title(title)
    if norm in webtic_by_title:
        return webtic_by_title[norm]
    for other, days in webtic_by_title.items():
        if norm in other or other in norm:
            return days
    return {}


def build_programmazione(
    listing: Dict[str, Any],
    allowed_dates: List[str],
    webtic_days: Optional[Dict[str, List[str]]] = None,
) -> List[Dict[str, Any]]:
    allowed = set(allowed_dates)
    webtic_days = webtic_days or {}
    programmi: List[Dict[str, Any]] = []
    for day in listing["days"]:
        if day not in allowed:
            continue
        if day in listing["overrides"]:
            times = listing["overrides"][day]
        elif day in webtic_days:
            times = webtic_days[day]
        else:
            times = listing["default_times"]
        times = sorted(set(times))
        if not times:
            continue
        programmi.append({"data": day, "giorno": "", "orari": times})
    return programmi


def scrape_guerrieri_official(
    allowed_dates: List[str],
    page_html: Optional[str] = None,
    webtic_films: Optional[List[Dict[str, Any]]] = None,
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Scraping Guerrieri: date dal sito ufficiale, orari Webtic solo nei giorni validi."""
    if page_html is None:
        from scraper import get_page

        soup = get_page(GUERRIERI_OFFICIAL_URL)
        if soup is None:
            return []
        page_html = str(soup)

    listings = parse_guerrieri_listing_html(page_html, today=today)
    if not listings:
        return []

    webtic_by_title = _webtic_times_by_norm_title(webtic_films or [])
    films: List[Dict[str, Any]] = []
    for listing in listings:
        webtic_days = _match_webtic_days(listing["titolo"], webtic_by_title)
        programmazione = build_programmazione(listing, allowed_dates, webtic_days)
        if not programmazione:
            continue
        all_times = sorted({t.replace(":", ".") for p in programmazione for t in p["orari"]})
        films.append({
            "titolo": listing["titolo"],
            "orari": all_times,
            "sala": None,
            "programmazione": programmazione,
            "source": ["guerrieri_official"],
            "lingua_originale": None,
        })
    return films
