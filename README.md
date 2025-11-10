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

### Ricerca film su Trakt (TMDB/IMDB)

Per trovare rapidamente gli ID TMDB o IMDB a partire dal titolo del film, usa lo script `trakt_search.py`.

1. Esporta le tue credenziali Trakt (non inserirle nel codice!):
   ```bash
   export TRAKT_CLIENT_ID="110995ce03b0765434c85ddf9354508121f36bf3f10fbce11e814e0dbb818da1"
   # Il client secret non è necessario per la sola ricerca pubblica
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

Lo script usa l'endpoint pubblico `/search/movie` di Trakt e restituisce già i link diretti TMDB/IMDB quando disponibili.

### Come API HTTP (per Make.com)

Avvia il server Flask:
```bash
python app.py
```

Il server sarà disponibile su `http://localhost:5000`

### Endpoint disponibili

- `GET /` - Informazioni sul servizio
- `GET /health` - Controllo dello stato del servizio
- `GET /api/films` - Ottiene tutti i film dai 3 cinema (endpoint principale per Make.com)
- `GET /api/films/<cinema_name>` - Ottiene i film di un cinema specifico

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

