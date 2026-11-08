# Matera Film Scraper

Scraper per estrarre i film in programmazione nei cinema di Matera da comingsoon.it.

## Struttura del Progetto

- `scraper.py`: Modulo principale con le funzioni di scraping
- `app.py`: Server Flask per esporre l'API HTTP
- `requirements.txt`: Dipendenze Python

## Installazione

1. Crea un virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

2. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

## Utilizzo

### Come script standalone

Esegui lo scraper direttamente:
```bash
python scraper.py
```

Genererà un file `programmazione_cinema_matera.json` con tutti i dati.

### Ricerca film su TMDB (IMDb + locandine)

Il matching **non** prende il primo risultato della search (così si evitano id IMDb sbagliati).
Per ogni titolo: search `it-IT` sull’anno corrente e precedente, score su similarità titolo + recency dell’uscita, tie-break con `release_dates` teatrali IT, poi `external_ids` e `images`.

```bash
export TMDB_ACCESS_TOKEN="eyJ..."   # Bearer v4, oppure TMDB_API_KEY=...
source venv/bin/activate
python scrape_with_trakt.py
```

`TRAKT_CLIENT_ID` è opzionale: se presente aggiunge lo slug Trakt **senza** sovrascrivere tmdb/imdb.

Output:
- `programmazione_cinema_matera.json` → programmazione + `tmdb`, `imdb`, `imdb_url`, `poster_url`, `voto_tmdb`
- `programmazione_cinema_matera_with_trakt.json` → indice per titolo
- `messaggio_telegram.txt`

### Ricerca film su Trakt (solo slug, non gli id)

Per una ricerca manuale Trakt resta `trakt_search.py` (non usarlo per gli id IMDb).

1. Esporta le tue credenziali Trakt (non inserirle nel codice!):
   ```bash
   export TRAKT_CLIENT_ID="..."
   ```

2. Esegui la ricerca:
   ```bash
   python trakt_search.py "Bugonia" --year 2025 --limit 3
   ```

   Output di esempio:
   ```
   1. Bugonia (2025)
      Score: 980.0
      Trakt slug: bugonia-2025
      TMDB: https://www.themoviedb.org/movie/123456
      IMDB: https://www.imdb.com/title/tt1234567/
   ```

Lo script usa l'endpoint pubblico `/search/movie` di Trakt solo per lo slug; gli id IMDb vanno presi da TMDB.

### Come API HTTP (per Make.com)

Avvia il server Flask:
```bash
python app.py
```

Il server sarà disponibile su `http://localhost:5000`

### Endpoint disponibili


> Imposta `TMDB_ACCESS_TOKEN` (Bearer v4) o `TMDB_API_KEY` sul server: `/api/films` arricchisce automaticamente ogni film con tmdb/imdb/poster. `?enrich=1` è opzionale (solo slug Trakt; richiede `TRAKT_CLIENT_ID`).
- `GET /` - Informazioni sul servizio
- `GET /health` - Controllo dello stato del servizio
- `GET /api/films` - Tutti i film dai 3 cinema (JSON). Matching TMDB automatico se il token è impostato.
- `GET /api/films/<cinema_name>` - Film di un cinema specifico
- `GET /api/films/telegram` - Messaggio compatto per Telegram/WhatsApp (max 4096 caratteri)

### Esempio di risposta JSON

```json
{
  "timestamp": "2025-11-02T01:55:36.338273",
  "cinema": [
    {
      "cinema": "Cinema Comunale Guerrieri",
      "url": "https://www.comingsoon.it/cinema/matera/cinema-comunale-guerrieri/2635/",
      "film": [
        {
          "titolo": "Bugonia",
          "orari": ["17.30", "19.35"],
          "sala": "Sala 1"
        }
      ]
    }
  ],
  "statistics": {
    "total_cinema": 3,
    "total_films": 15
  }
}
```

## Utilizzo con Make.com

1. **Deploya il server** su una piattaforma cloud (Heroku, Railway, Render, Fly.io, ecc.)

2. **In Make.com**, aggiungi un modulo **HTTP > Make a request**:
   - **Method**: `GET`
   - **URL**: `https://tuo-server.com/api/films`
   - **Response format**: `JSON`

3. Il modulo restituirà il JSON con tutti i film raggruppati per cinema, con la seguente struttura:
   ```json
   {
     "timestamp": "2025-11-02T01:55:36.338273",
     "cinema": [
       {
         "cinema": "Cinema Comunale Guerrieri",
         "url": "...",
         "film": [
           {
             "titolo": "Nome Film",
             "orari": ["17.30", "19.35"],
             "sala": "Sala 1"
           }
         ]
       }
     ],
     "statistics": {
       "total_cinema": 3,
       "total_films": 15
     }
   }
   ```

4. Puoi poi usare i dati in Make.com per processarli, inviarli via email, salvarli su Google Sheets, ecc.

## Deploy su piattaforme cloud

**📘 Vedi il file [DEPLOY.md](DEPLOY.md) per una guida dettagliata passo-passo per Render.com (GRATIS e consigliato per uso sporadico)**

### Quick Start per Render.com

1. Crea un repository Git e carica il progetto su GitHub
2. Vai su [render.com](https://render.com) e registrati
3. Crea un nuovo "Web Service"
4. Connetti il repository
5. Configurazione:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free
6. Salva e attendi il deploy (5-10 minuti)

Il servizio sarà disponibile su un URL tipo: `https://tuo-nome.onrender.com/api/films`

**Nota**: Il tier gratuito di Render spegne il servizio dopo inattività (ok per chiamate ogni 2-3 giorni). La prima richiesta dopo lo spegnimento può richiedere 30-60 secondi (cold start).

### Variabili d'ambiente

- `PORT`: Porta del server (opzionale, default: 5000)

## Cinema supportati

- Cinema Comunale Guerrieri
- Il Piccolo
- UCI Cinemas Red Carpet

