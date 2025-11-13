#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server Flask per esporre lo scraper dei cinema di Matera come API HTTP.
Può essere chiamato da Make.com o altri servizi web.
"""

from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from scraper import scrape_cinema, CINEMA_URLS, format_telegram_message
from trakt_enrich import enrich_with_trakt, MissingTraktCredentials
from datetime import datetime
import traceback

app = Flask(__name__)
CORS(app)  # Abilita CORS per permettere chiamate da Make.com

def _parse_bool(value):
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on"}


def _scrape_all_cinemas(enrich=False):
    data = {
        "timestamp": datetime.now().isoformat(),
        "cinema": [],
    }

    for cinema_name, url in CINEMA_URLS.items():
        cinema_data = scrape_cinema(url, cinema_name)
        data["cinema"].append(cinema_data)

    aggregated = None
    if enrich:
        aggregated = enrich_with_trakt(data["cinema"])

    total_films = sum(len(c['film']) for c in data["cinema"])
    data["statistics"] = {
        "total_cinema": len(data["cinema"]),
        "total_films": total_films,
    }

    return data, aggregated

@app.route('/')
def index():
    """Endpoint di benvenuto."""
    return jsonify({
        "service": "Matera Film Scraper API",
        "description": "API per ottenere i film in programmazione nei cinema di Matera",
        "endpoints": {
            "/api/films": "GET - Ottiene tutti i film dai 3 cinema (JSON)",
            "/api/films/telegram": "GET - Ottiene messaggio formattato per Telegram",
            "/api/films/<cinema_name>": "GET - Ottiene i film di un cinema specifico",
            "/health": "GET - Controlla lo stato del servizio"
        },
        "cinema": list(CINEMA_URLS.keys())
    })

@app.route('/health')
def health():
    """Endpoint per controllare lo stato del servizio."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/films', methods=['GET'])
def get_all_films():
    """Restituisce tutti i film; usa ?enrich=1 per includere metadata Trakt."""
    try:
        enrich = _parse_bool(request.args.get('enrich'))
        data, aggregated = _scrape_all_cinemas(enrich=enrich)
        if aggregated is not None:
            data["trakt_enriched"] = aggregated
        return jsonify(data), 200
    except MissingTraktCredentials as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/films/<cinema_name>', methods=['GET'])
def get_cinema_films(cinema_name):
    """
    Endpoint per ottenere i film di un cinema specifico.
    
    Args:
        cinema_name: Nome del cinema (normalizzato)
    """
    try:
        # Normalizza il nome del cinema per la ricerca
        cinema_name_normalized = cinema_name.lower().replace('-', ' ').replace('_', ' ')
        
        # Trova il cinema corrispondente
        matched_cinema = None
        matched_url = None
        
        for name, url in CINEMA_URLS.items():
            if cinema_name_normalized in name.lower() or name.lower() in cinema_name_normalized:
                matched_cinema = name
                matched_url = url
                break
        
        if not matched_cinema:
            return jsonify({
                "error": f"Cinema '{cinema_name}' non trovato",
                "available_cinema": list(CINEMA_URLS.keys())
            }), 404
        
        # Scrape il cinema specifico
        cinema_data = scrape_cinema(matched_url, matched_cinema)
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "cinema": [cinema_data]
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/films/telegram', methods=['GET'])
def get_telegram_message():
    """Restituisce il messaggio formattato per Telegram. Usa ?enrich=1 per includere link IMDb."""
    try:
        enrich = _parse_bool(request.args.get('enrich'))
        data, _ = _scrape_all_cinemas(enrich=enrich)
        telegram_msg = format_telegram_message(data)
        return Response(
            telegram_msg,
            mimetype='text/plain; charset=utf-8',
            headers={'Content-Disposition': 'inline'}
        ), 200
    except MissingTraktCredentials as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    # Configurazione per il deployment
    # In produzione, usa un server WSGI come Gunicorn
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

