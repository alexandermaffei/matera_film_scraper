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
from datetime import datetime
from typing import Dict, List, Any

# URL dei cinema di Matera
CINEMA_URLS = {
    "Cinema Comunale Guerrieri": "https://www.comingsoon.it/cinema/matera/cinema-comunale-guerrieri/2635/",
    "Il Piccolo": "https://www.comingsoon.it/cinema/matera/il-piccolo/4976/",
    "UCI Cinemas Red Carpet": "https://www.comingsoon.it/cinema/matera/uci-cinemas-red-carpet/5635/"
}

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

    films = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

    for cinema in data.get('cinema', []):
        cinema_name = cinema.get('cinema', '')
        cinema_short = cinema_short_names.get(cinema_name, cinema_name)
        for film in cinema.get('film', []):
            title = film.get('titolo')
            if not title:
                continue
            for prog in film.get('programmazione', []):
                date = prog.get('data')
                for time in prog.get('orari', []):
                    if not date or not time:
                        continue
                    films[title][cinema_short][date].add(time.replace('.', ':'))

    for title in sorted(films):
        lines.append(f"📽️ {title}")
        cinema_map = films[title]
        for cinema_short in sorted(cinema_map):
            date_map = cinema_map[cinema_short]
            ordered_dates = sorted(date_map)
            normalized = OrderedDict((d, sorted(date_map[d])) for d in ordered_dates)

            groups = []
            current_start = current_end = None
            current_times = None
            for date in normalized:
                times = normalized[date]
                date_obj = dt_class.fromisoformat(date)
                if current_times is None:
                    current_start = current_end = date
                    current_times = times
                elif times == current_times and (date_obj - dt_class.fromisoformat(current_end)).days == 1:
                    current_end = date
                else:
                    groups.append((current_start, current_end, current_times))
                    current_start = current_end = date
                    current_times = times
            if current_times is not None:
                groups.append((current_start, current_end, current_times))

            for start_date, end_date, times in groups:
                date_label = format_range(start_date, end_date)
                orari_str = " • ".join(times)
                lines.append(f"   📅 {date_label} · {cinema_short}")
                lines.append(f"      🕐 {orari_str}")
        lines.append("")

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
    
    all_data = {
        "timestamp": datetime.now().isoformat(),
        "cinema": []
    }
    
    for cinema_name, url in CINEMA_URLS.items():
        cinema_data = scrape_cinema(url, cinema_name)
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

