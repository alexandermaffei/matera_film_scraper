#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server Flask per esporre lo scraper dei cinema di Matera come API HTTP.
Può essere chiamato da Make.com o altri servizi web.
"""

from flask import Flask, jsonify, Response
from flask_cors import CORS
from scraper import scrape_cinema, CINEMA_URLS, format_telegram_message
from datetime import datetime
import traceback

app = Flask(__name__)
CORS(app)  # Abilita CORS per permettere chiamate da Make.com

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
    """
    Endpoint principale che restituisce tutti i film dai 3 cinema.
    Questo è l'endpoint da chiamare da Make.com.
    """
    try:
        result = {
            "timestamp": datetime.now().isoformat(),
            "cinema": []
        }
        
        # Scrape tutti i cinema
        for cinema_name, url in CINEMA_URLS.items():
            cinema_data = scrape_cinema(url, cinema_name)
            result["cinema"].append(cinema_data)
        
        # Calcola statistiche
        total_films = sum(len(c['film']) for c in result["cinema"])
        result["statistics"] = {
            "total_cinema": len(result["cinema"]),
            "total_films": total_films
        }
        
        return jsonify(result), 200
        
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
    """
    Endpoint che restituisce un messaggio formattato per Telegram.
    Perfetto per inviare direttamente a un bot Telegram o un canale.
    """
    try:
        result = {
            "timestamp": datetime.now().isoformat(),
            "cinema": []
        }
        
        # Scrape tutti i cinema
        for cinema_name, url in CINEMA_URLS.items():
            cinema_data = scrape_cinema(url, cinema_name)
            result["cinema"].append(cinema_data)
        
        # Genera messaggio Telegram
        telegram_msg = format_telegram_message(result)
        
        # Restituisci come testo plain con encoding UTF-8
        return Response(
            telegram_msg,
            mimetype='text/plain; charset=utf-8',
            headers={'Content-Disposition': 'inline'}
        ), 200
        
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

