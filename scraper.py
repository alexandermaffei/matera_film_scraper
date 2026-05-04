#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler per estrarre i film in programmazione nei cinema di Matera
da comingsoon.it e salvarli in un file JSON.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
import unicodedata

# URL dei cinema di Matera
CINEMA_URLS = {
    "Cinema Comunale Guerrieri": "https://www.comingsoon.it/cinema/matera/cinema-comunale-guerrieri/2635/",
    "Il Piccolo": "https://www.comingsoon.it/cinema/matera/il-piccolo/4976/",
    "UCI Cinemas Red Carpet": "https://www.comingsoon.it/cinema/matera/uci-cinemas-red-carpet/5635/"
}

UCI_THEATRE_SLUG = "uci-cinemas-redcarpet-matera"
UCI_API_BASE_URL = "https://uci-backend-production-1042268733238.europe-west8.run.app/api"
REPORT_WINDOW_DAYS = 7

def get_page(url: str) -> BeautifulSoup:
    """
    Scarica una pagina web e restituisce un oggetto BeautifulSoup.
    
    Args:
        url: URL della pagina da scaricare
        
    Returns:
        BeautifulSoup object
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"Errore nel caricare {url}: {e}")
        return None


def normalize_title(title: str) -> str:
    """Normalizza un titolo film per confronti tra fonti diverse."""
    if not title:
        return ""
    normalized = unicodedata.normalize("NFKD", title)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return normalized.strip()


def report_window_dates(window_days: int = REPORT_WINDOW_DAYS) -> List[str]:
    """Ritorna le date ISO da oggi per i successivi N giorni (incluso oggi)."""
    today = datetime.now().date()
    return [(today + timedelta(days=i)).isoformat() for i in range(window_days)]


def filter_programmazione_by_dates(programmazione: List[Dict[str, Any]], allowed_dates: List[str]) -> List[Dict[str, Any]]:
    """Filtra la programmazione in base alla finestra temporale desiderata."""
    allowed = set(allowed_dates)
    filtered = [p for p in programmazione if p.get("data") in allowed and p.get("orari")]
    filtered.sort(key=lambda x: x.get("data", ""))
    return filtered


def fetch_uci_programming_for_date(day_iso: str) -> List[Dict[str, Any]]:
    """Recupera la programmazione UCI del giorno dal backend ufficiale."""
    url = f"{UCI_API_BASE_URL}/theatres/{UCI_THEATRE_SLUG}/programming/{day_iso}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://ucicinemas.it",
        "User-Agent": "Mozilla/5.0",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", []) if isinstance(payload, dict) else []
    except requests.RequestException as e:
        print(f"Errore nel caricare la programmazione UCI ({day_iso}): {e}")
        return []
    except ValueError:
        print(f"Risposta JSON non valida da UCI per {day_iso}")
        return []


def scrape_uci_official_window(allowed_dates: List[str]) -> List[Dict[str, Any]]:
    """
    Scrape della programmazione UCI ufficiale nella finestra data.
    Restituisce una lista film nello stesso formato usato dal progetto.
    """
    by_title: Dict[str, Dict[str, Any]] = {}

    for day_iso in allowed_dates:
        day_films = fetch_uci_programming_for_date(day_iso)
        for film in day_films:
            title = film.get("title")
            if not title:
                continue

            if title not in by_title:
                by_title[title] = {
                    "titolo": title,
                    "orari": [],
                    "sala": None,
                    "programmazione": defaultdict(set),
                    "programmazione_vo": defaultdict(set),
                    "programmazione_non_vo": defaultdict(set),
                    "source": ["uci_official"],
                    "lingua_originale": False,
                    "lingue_disponibili": set(),
                }

            screens = film.get("screens", [])
            for screen_group in screens:
                if not isinstance(screen_group, dict):
                    continue
                for variants in screen_group.values():
                    if not isinstance(variants, list):
                        continue
                    for variant in variants:
                        language = (variant.get("language") or {}).get("name")
                        lang_slug = ((variant.get("language") or {}).get("slug") or "").upper()
                        subtitles_name = (variant.get("subtitles") or {}).get("name")
                        is_vo_variant = lang_slug in {"EN", "ENG"} or (
                            language and language.upper() in {"EN", "ENG", "ENGLISH"}
                        )
                        if language:
                            by_title[title]["lingue_disponibili"].add(language)
                        if subtitles_name:
                            by_title[title]["lingue_disponibili"].add(f"sottotitoli {subtitles_name}")
                        # Consideriamo VO quando la traccia audio non e' italiana
                        if is_vo_variant:
                            by_title[title]["lingua_originale"] = True

                        performances = variant.get("performances", [])
                        for perf in performances:
                            perf_day = perf.get("day")
                            perf_time = perf.get("actual_start_at")
                            if not perf_day or not perf_time or perf_day not in allowed_dates:
                                continue
                            by_title[title]["programmazione"][perf_day].add(perf_time)
                            target_key = "programmazione_vo" if is_vo_variant else "programmazione_non_vo"
                            by_title[title][target_key][perf_day].add(perf_time)

    films = []
    for title in sorted(by_title):
        schedule_map = by_title[title]["programmazione"]
        schedule_vo_map = by_title[title]["programmazione_vo"]
        schedule_non_vo_map = by_title[title]["programmazione_non_vo"]
        programmazione = []
        programmazione_vo = []
        programmazione_non_vo = []
        all_times = set()
        for date_str in sorted(schedule_map):
            times = sorted(schedule_map[date_str])
            all_times.update(t.replace(":", ".") for t in times)
            programmazione.append({
                "data": date_str,
                "giorno": "",
                "orari": times,
            })
        for date_str in sorted(schedule_vo_map):
            programmazione_vo.append({
                "data": date_str,
                "giorno": "",
                "orari": sorted(schedule_vo_map[date_str]),
            })
        for date_str in sorted(schedule_non_vo_map):
            programmazione_non_vo.append({
                "data": date_str,
                "giorno": "",
                "orari": sorted(schedule_non_vo_map[date_str]),
            })

        films.append({
            "titolo": title,
            "orari": sorted(all_times),
            "sala": None,
            "programmazione": programmazione,
            "programmazione_vo": programmazione_vo,
            "programmazione_non_vo": programmazione_non_vo,
            "source": ["uci_official"],
            "lingua_originale": by_title[title].get("lingua_originale", False),
            "lingue_disponibili": sorted(by_title[title].get("lingue_disponibili", set())),
        })

    return films


def merge_film_entries(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    """Unisce due record film (ComingSoon + UCI) senza duplicati."""
    merged = {
        "titolo": base.get("titolo") or extra.get("titolo"),
        "orari": sorted(set((base.get("orari") or []) + (extra.get("orari") or []))),
        "sala": base.get("sala") or extra.get("sala"),
        "programmazione": [],
    }

    base_vo = base.get("lingua_originale")
    extra_vo = extra.get("lingua_originale")
    if base_vo is True or extra_vo is True:
        merged["lingua_originale"] = True
    elif base_vo is False and extra_vo is False:
        merged["lingua_originale"] = False
    else:
        # Nessuna fonte certa: lasciamo sconosciuto
        merged["lingua_originale"] = None

    lingue = sorted(set((base.get("lingue_disponibili") or []) + (extra.get("lingue_disponibili") or [])))
    if lingue:
        merged["lingue_disponibili"] = lingue

    source = []
    for s in (base.get("source") or []) + (extra.get("source") or []):
        if s not in source:
            source.append(s)
    if source:
        merged["source"] = source

    prog_map: Dict[str, set] = defaultdict(set)
    day_map: Dict[str, str] = {}
    for item in (base.get("programmazione") or []) + (extra.get("programmazione") or []):
        date_str = item.get("data")
        if not date_str:
            continue
        for time in item.get("orari", []):
            prog_map[date_str].add(time)
        if item.get("giorno"):
            day_map[date_str] = item.get("giorno")

    for date_str in sorted(prog_map):
        merged["programmazione"].append({
            "data": date_str,
            "giorno": day_map.get(date_str, ""),
            "orari": sorted(prog_map[date_str]),
        })

    def merge_programmazione_field(field_name: str) -> None:
        f_map: Dict[str, set] = defaultdict(set)
        for item in (base.get(field_name) or []) + (extra.get(field_name) or []):
            date_str = item.get("data")
            if not date_str:
                continue
            for time in item.get("orari", []):
                f_map[date_str].add(time)
        if f_map:
            merged[field_name] = [
                {"data": date_str, "giorno": "", "orari": sorted(f_map[date_str])}
                for date_str in sorted(f_map)
            ]

    merge_programmazione_field("programmazione_vo")
    merge_programmazione_field("programmazione_non_vo")

    return merged


def merge_red_carpet_with_uci(comingsoon_films: List[Dict[str, Any]], uci_films: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fonde i film del Red Carpet da ComingSoon e sito ufficiale UCI."""
    merged_by_norm: Dict[str, Dict[str, Any]] = {}

    for film in comingsoon_films:
        film_copy = dict(film)
        film_copy["source"] = ["comingsoon"]
        if "lingua_originale" not in film_copy:
            film_copy["lingua_originale"] = None
        norm = normalize_title(film_copy.get("titolo", ""))
        if not norm:
            continue
        merged_by_norm[norm] = film_copy

    for film in uci_films:
        norm = normalize_title(film.get("titolo", ""))
        if not norm:
            continue
        if norm in merged_by_norm:
            merged_by_norm[norm] = merge_film_entries(merged_by_norm[norm], film)
        else:
            merged_by_norm[norm] = film

    merged_list = list(merged_by_norm.values())
    merged_list.sort(key=lambda x: x.get("titolo", ""))
    return merged_list


def apply_report_window(cinema_data: Dict[str, Any], allowed_dates: List[str]) -> Dict[str, Any]:
    """Applica il filtro della finestra report su un cinema."""
    filtered_films = []
    for film in cinema_data.get("film", []):
        film_copy = dict(film)
        film_copy["programmazione"] = filter_programmazione_by_dates(
            film_copy.get("programmazione", []),
            allowed_dates,
        )
        if "programmazione_vo" in film_copy:
            film_copy["programmazione_vo"] = filter_programmazione_by_dates(
                film_copy.get("programmazione_vo", []),
                allowed_dates,
            )
        if "programmazione_non_vo" in film_copy:
            film_copy["programmazione_non_vo"] = filter_programmazione_by_dates(
                film_copy.get("programmazione_non_vo", []),
                allowed_dates,
            )
        if "lingua_originale" not in film_copy:
            film_copy["lingua_originale"] = None
        filtered_films.append(film_copy)
    cinema_data["film"] = filtered_films
    return cinema_data

def extract_dates_and_times_from_ticket_page(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Estrae date e orari dalla pagina dettagliata del ticket.
    
    La struttura è: ogni giorno è in un <div class="media mbm"> con:
    - <div class="media-left"> contiene: weekday, day, month
    - <div class="media-body"> contiene: pulsanti <button class="btn-fab c"> con gli orari
    
    Args:
        soup: BeautifulSoup object della pagina del ticket
        
    Returns:
        Lista di dizionari con data e orari per quella data (senza duplicati)
    """
    dates_times = []
    
    if soup is None:
        return dates_times
    
    # Cerca tutti i div con classe "media mbm" che rappresentano un giorno
    media_elements = soup.find_all('div', class_=re.compile(r'media.*mbm', re.I))
    
    # Converti mese in numero
    month_map = {
        'GEN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
        'MAG': '05', 'GIU': '06', 'LUG': '07', 'AGO': '08',
        'SET': '09', 'OTT': '10', 'NOV': '11', 'DIC': '12'
    }
    
    # Usa un dict per raggruppare per data (evita duplicati)
    dates_dict = {}
    
    for media_elem in media_elements:
        # Estrai la data da media-left
        media_left = media_elem.find('div', class_='media-left')
        if not media_left:
            continue
        
        weekday_elem = media_left.find('span', class_='weekday')
        day_elem = media_left.find('span', class_='day')
        month_elem = media_left.find('span', class_='month')
        
        if not (weekday_elem and day_elem and month_elem):
            continue
        
        day_name = weekday_elem.get_text(strip=True)
        day_num = day_elem.get_text(strip=True)
        month = month_elem.get_text(strip=True)
        
        # Converti mese
        month_num = month_map.get(month.upper(), '01')
        
        # Costruisci la data (anno corrente)
        current_year = datetime.now().year
        now = datetime.now()
        # Se il mese è passato rispetto ad oggi, probabilmente è dell'anno prossimo
        if int(month_num) < now.month:
            current_year += 1
        elif int(month_num) == now.month and int(day_num) < now.day:
            current_year += 1
        
        date_str = f"{current_year}-{month_num}-{day_num.zfill(2)}"
        
        # Estrai gli orari da media-body
        media_body = media_elem.find('div', class_='media-body')
        times = []
        
        if media_body:
            # Cerca tutti i pulsanti con orari
            time_buttons = media_body.find_all('button', class_=re.compile(r'btn-fab', re.I))
            for btn in time_buttons:
                btn_text = btn.get_text(strip=True)
                # Estrai orari nel formato HH:MM
                if re.match(r'\d{1,2}:\d{2}', btn_text):
                    try:
                        h, m = map(int, btn_text.split(':'))
                        if 0 <= h < 24 and 0 <= m < 60:
                            times.append(btn_text)
                    except:
                        continue
        
        # Raggruppa per data (unisce orari se stessa data appare più volte)
        if date_str in dates_dict:
            # Unisci gli orari, rimuovi duplicati
            dates_dict[date_str]['orari'].extend(times)
            dates_dict[date_str]['orari'] = sorted(list(set(dates_dict[date_str]['orari'])))
        else:
            dates_dict[date_str] = {
                "data": date_str,
                "giorno": day_name,
                "orari": sorted(list(set(times))) if times else []
            }
    
    # Converti dict in lista, filtra solo quelli con orari
    dates_times = [dt for dt in dates_dict.values() if dt['orari']]
    
    # Ordina per data
    dates_times.sort(key=lambda x: x['data'])
    
    return dates_times

def extract_times_from_text(text: str) -> List[str]:
    """
    Estrae gli orari di proiezione da una stringa.
    
    Esempi di formato:
    - "17.30 / 7,00€ - 19.35 / 7,00€"
    - "Sala 1 | Posti 447  17.30 / 7,00€ - 19.35 / 7,00€"
    
    Args:
        text: Testo contenente gli orari
        
    Returns:
        Lista di orari nel formato HH.MM
    """
    # Pattern per trovare orari nel formato HH.MM o HH:MM
    time_pattern = r'\b(\d{1,2}[.:]\d{2})\b'
    matches = re.findall(time_pattern, text)
    
    # Pulisci gli orari e normalizza il formato
    cleaned_times = []
    for time in matches:
        # Normalizza i due punti in punto
        time_normalized = time.replace(':', '.')
        
        # Converti in numero per validare
        try:
            time_float = float(time_normalized.replace(',', '.'))
        except ValueError:
            continue
        
        # Filtra i prezzi (solitamente < 20 euro, quindi numeri piccoli con virgola)
        # Gli orari sono sempre >= 0 e < 24 (formato 0.00 - 23.59)
        if 0 <= time_float < 24:
            # Se ha una virgola ma è < 25, potrebbe essere un prezzo in formato europeo
            if ',' in time and time_float < 10:
                # Probabilmente è un prezzo, salta
                continue
            cleaned_times.append(time_normalized.replace(',', '.'))
        # Se è >= 24, potrebbe essere un anno o altro, salta
    
    return cleaned_times

def extract_film_data(soup: BeautifulSoup, cinema_name: str) -> List[Dict[str, Any]]:
    """
    Estrae i dati dei film dalla pagina HTML.
    
    Args:
        soup: BeautifulSoup object della pagina
        cinema_name: Nome del cinema
        
    Returns:
        Lista di dizionari con i dati dei film
    """
    films = []
    
    if soup is None:
        return films
    
    # Cerca tutte le sezioni film usando la classe specifica identificata
    # Ogni film è in un div con classe "header-scheda streaming min no-bg container-fluid pbl"
    film_sections = soup.find_all('div', class_=re.compile(r'header-scheda.*streaming', re.I))
    
    # Se non trova con quella classe, prova a cercare in modo diverso
    if not film_sections:
        # Cerca la sezione "Film in programmazione" e poi tutti i div seguenti
        film_heading = soup.find('h2', string=re.compile(r'Film in programmazione', re.I))
        if film_heading:
            # Trova il section parent
            section = film_heading.find_parent('section')
            if section:
                film_sections = section.find_all('div', class_=re.compile(r'header-scheda', re.I))
    
    # Processa ogni sezione film trovata
    for section in film_sections:
        # Estrai il titolo del film - è in un <a> con classe "tit_olo h1"
        title_elem = section.find('a', class_=re.compile(r'tit_olo', re.I))
        
        if not title_elem:
            continue
        
        title = title_elem.get_text(strip=True)
        
        if not title:
            continue
        
        # Estrai gli orari e la sala
        # Gli orari sono in un div con classe "cs-btn col primary ico sala"
        schedule_elem = section.find('div', class_=re.compile(r'cs-btn.*sala', re.I))
        
        times = []
        sala_info = None
        
        if schedule_elem:
            # Estrai la sala (prima dello span con clock)
            sala_span = schedule_elem.find('span', string=re.compile(r'Sala', re.I))
            if sala_span:
                sala_text = sala_span.get_text(strip=True)
                # Estrai "Sala X | Posti Y" o solo "Sala X"
                sala_match = re.search(r'Sala\s+(\d+)[^|]*', sala_text)
                if sala_match:
                    sala_info = f"Sala {sala_match.group(1)}"
            
            # Estrai gli orari (dallo span con icona clock o qualsiasi span con orari)
            spans = schedule_elem.find_all('span')
            schedule_text = ""
            
            # Cerca lo span con gli orari (di solito il secondo span o quello con icona clock)
            for span in spans:
                span_text = span.get_text(strip=True)
                # Se contiene pattern di orari, è quello che cerchiamo
                if re.search(r'\d{1,2}[.:]\d{2}', span_text):
                    schedule_text = span_text
                    break
            
            # Se non trova in uno span specifico, prendi tutto il testo del div
            if not schedule_text:
                schedule_text = schedule_elem.get_text(strip=True)
            
            if schedule_text:
                times = extract_times_from_text(schedule_text)
        
        # Se non ha trovato orari, prova a cercare in tutto il testo della sezione
        if not times:
            all_text = section.get_text()
            times = extract_times_from_text(all_text)
            # Cerca anche la sala nel testo completo
            sala_match = re.search(r'Sala\s+(\d+)', all_text)
            if sala_match:
                sala_info = f"Sala {sala_match.group(1)}"
        
        # Cerca il link "Acquista biglietto e vedi tutte le date"
        ticket_link = None
        # Prova prima con una ricerca per href che contiene "ticket"
        ticket_elem = section.find('a', href=re.compile(r'ticket', re.I))
        if not ticket_elem:
            # Prova a cercare per testo (potrebbe essere su più righe)
            ticket_elem = section.find('a', string=re.compile(r'Acquista.*biglietto', re.I))
        
        if ticket_elem:
            ticket_href = ticket_elem.get('href', '')
            if ticket_href:
                # Costruisci l'URL completo se è relativo
                if ticket_href.startswith('/'):
                    ticket_link = f"https://www.comingsoon.it{ticket_href}"
                elif ticket_href.startswith('http'):
                    ticket_link = ticket_href
                else:
                    ticket_link = f"https://www.comingsoon.it{ticket_href}"
        
        # Se c'è il link, scrapa la pagina dettagliata per date e orari
        programmazione = []
        if ticket_link:
            print(f"  Scraping pagina dettagliata per '{title}'...")
            ticket_soup = get_page(ticket_link)
            if ticket_soup:
                programmazione = extract_dates_and_times_from_ticket_page(ticket_soup)
        
        # Crea struttura dati per il film
        if title:  # Aggiungi anche se non ci sono orari (potrebbe essere programmazione futura)
            film_data = {
                "titolo": title,
                "orari": times if times else [],  # Orari dalla pagina principale (per retrocompatibilità)
                "sala": sala_info,
                "programmazione": programmazione if programmazione else []  # Date e orari dettagliati
            }
            films.append(film_data)
    
    return films

def scrape_cinema(url: str, cinema_name: str) -> Dict[str, Any]:
    """
    Scrape i dati di un singolo cinema.
    
    Args:
        url: URL della pagina del cinema
        cinema_name: Nome del cinema
        
    Returns:
        Dizionario con i dati del cinema
    """
    print(f"Scraping {cinema_name}...")
    soup = get_page(url)
    
    films = extract_film_data(soup, cinema_name)
    
    return {
        "cinema": cinema_name,
        "url": url,
        "film": films
    }

def format_telegram_message(data: Dict[str, Any]) -> str:
    """Format Telegram message grouped by film with compact date ranges."""
    from collections import defaultdict, OrderedDict
    from datetime import datetime as dt_class

    lines = ["🎬 FILM IN PROGRAMMAZIONE - MATERA\n"]

    cinema_short_names = {
        "Cinema Comunale Guerrieri": "Guerrieri",
        "Il Piccolo": "Piccolo",
        "UCI Cinemas Red Carpet": "Red Carpet",
    }

    mesi_italiano = {
        '01': 'gennaio', '02': 'febbraio', '03': 'marzo', '04': 'aprile',
        '05': 'maggio', '06': 'giugno', '07': 'luglio', '08': 'agosto',
        '09': 'settembre', '10': 'ottobre', '11': 'novembre', '12': 'dicembre'
    }

    def format_date(date_str: str) -> str:
        anno, mese, giorno = date_str.split('-')
        return f"{int(giorno)} {mesi_italiano.get(mese, mese)}"

    def format_range(start_date: str, end_date: str) -> str:
        if start_date == end_date:
            return format_date(start_date)
        a_y, a_m, a_d = start_date.split('-')
        b_y, b_m, b_d = end_date.split('-')
        if a_y == b_y and a_m == b_m:
            return f"{int(a_d)}-{int(b_d)} {mesi_italiano.get(a_m, a_m)}"
        return f"{format_date(start_date)} → {format_date(end_date)}"

    films_all = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    films_vo = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    films_non_vo = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    film_meta = {}

    for cinema in data.get('cinema', []):
        cinema_name = cinema.get('cinema', '')
        cinema_short = cinema_short_names.get(cinema_name, cinema_name)
        for film in cinema.get('film', []):
            title = film.get('titolo')
            if not title:
                continue
            imdb_id = film.get('imdb')
            imdb_url = film.get('imdb_url')
            if imdb_url:
                film_meta.setdefault(title, {})['imdb_url'] = imdb_url
            elif imdb_id:
                film_meta.setdefault(title, {})['imdb_url'] = f"https://www.imdb.com/title/{imdb_id}/"

            for prog in film.get('programmazione', []):
                date = prog.get('data')
                for time in prog.get('orari', []):
                    if not date or not time:
                        continue
                    films_all[title][cinema_short][date].add(time.replace('.', ':'))
            for prog in film.get('programmazione_vo', []):
                date = prog.get('data')
                for time in prog.get('orari', []):
                    if not date or not time:
                        continue
                    films_vo[title][cinema_short][date].add(time.replace('.', ':'))
            for prog in film.get('programmazione_non_vo', []):
                date = prog.get('data')
                for time in prog.get('orari', []):
                    if not date or not time:
                        continue
                    films_non_vo[title][cinema_short][date].add(time.replace('.', ':'))

    vo_titles = []
    regular_titles = []
    for title in sorted(films_all):
        is_vo = False
        for cinema in data.get('cinema', []):
            for film in cinema.get('film', []):
                if film.get('titolo') == title and film.get('lingua_originale') is True:
                    is_vo = True
                    break
            if is_vo:
                break
        if is_vo:
            vo_titles.append(title)
        else:
            regular_titles.append(title)

    def append_times_line(times: List[str]) -> None:
        if len(times) > 5:
            lines.append(f"      🕐 {len(times)} spettacoli - primo spettacolo: {times[0]}, ultimo spettacolo: {times[-1]}")
        else:
            lines.append(f"      🕐 {' • '.join(times)}")

    def append_title_block(title: str, mark_vo: bool = False) -> None:
        imdb_url = film_meta.get(title, {}).get('imdb_url')
        title_prefix = "📽️ 🌐VO" if mark_vo else "📽️"
        if imdb_url:
            lines.append(f"{title_prefix} {title} · {imdb_url}")
        else:
            lines.append(f"{title_prefix} {title}")

        if mark_vo:
            cinema_map = films_vo[title]
        else:
            # Per i film VO mostriamo nella sezione "Altri" solo le proiezioni non VO.
            if title in vo_titles:
                cinema_map = films_non_vo[title]
            else:
                cinema_map = films_all[title]

        if not cinema_map:
            lines.append("   📅 Nessuna proiezione disponibile")
            lines.append("")
            return

        for cinema_short in sorted(cinema_map):
            date_map = cinema_map[cinema_short]
            for date in sorted(date_map):
                times = sorted(date_map[date])
                date_label = format_date(date)
                lines.append(f"   📅 {date_label} · {cinema_short}")
                append_times_line(times)
        lines.append("")

    if vo_titles:
        lines.append("🌐 FILM IN LINGUA ORIGINALE")
        lines.append("")
        for title in vo_titles:
            append_title_block(title, mark_vo=True)

    regular_titles_with_non_vo = list(regular_titles)
    for title in vo_titles:
        if films_non_vo.get(title):
            regular_titles_with_non_vo.append(title)

    if regular_titles_with_non_vo:
        lines.append("🎞️ ALTRI FILM")
        lines.append("")
        for title in sorted(regular_titles_with_non_vo):
            append_title_block(title, mark_vo=False)

    timestamp = data.get('timestamp')
    if timestamp:
        try:
            dt_obj = dt_class.fromisoformat(timestamp.replace('Z', '+00:00'))
            lines.append(f"Aggiornato il {dt_obj.strftime('%d/%m/%Y alle %H:%M')}")
        except Exception:
            pass

    return "\n".join(lines)

def main():
    """
    Funzione principale che esegue lo scraping di tutti i cinema.
    """
    print("Inizio scraping dei cinema di Matera...")
    
    allowed_dates = report_window_dates(REPORT_WINDOW_DAYS)

    all_data = {
        "timestamp": datetime.now().isoformat(),
        "report_window": {
            "days": REPORT_WINDOW_DAYS,
            "from": allowed_dates[0],
            "to": allowed_dates[-1]
        },
        "cinema": []
    }
    
    for cinema_name, url in CINEMA_URLS.items():
        cinema_data = scrape_cinema(url, cinema_name)
        cinema_data = apply_report_window(cinema_data, allowed_dates)

        # Fusione dedicata per UCI Red Carpet: ComingSoon + sito ufficiale UCI
        if cinema_name == "UCI Cinemas Red Carpet":
            uci_films = scrape_uci_official_window(allowed_dates)
            cinema_data["film"] = merge_red_carpet_with_uci(cinema_data.get("film", []), uci_films)

        all_data["cinema"].append(cinema_data)
        print(f"Trovati {len(cinema_data['film'])} film per {cinema_name}")
    
    # Salva i dati in JSON
    output_file = "programmazione_cinema_matera.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nDati salvati in {output_file}")
    print(f"Totale cinema: {len(all_data['cinema'])}")
    print(f"Totale film: {sum(len(c['film']) for c in all_data['cinema'])}")
    
    # Genera messaggio Telegram
    telegram_msg = format_telegram_message(all_data)
    telegram_file = "messaggio_telegram.txt"
    with open(telegram_file, 'w', encoding='utf-8') as f:
        f.write(telegram_msg)
    
    print(f"\nMessaggio Telegram salvato in {telegram_file}")
    print("\n" + "="*50)
    print(telegram_msg)
    print("="*50)

if __name__ == "__main__":
    main()

