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
        
        # Crea struttura dati per il film
        if title:  # Aggiungi anche se non ci sono orari (potrebbe essere programmazione futura)
            film_data = {
                "titolo": title,
                "orari": times if times else [],
                "sala": sala_info
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

if __name__ == "__main__":
    main()

