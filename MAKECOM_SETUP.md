# Configurazione Make.com per Matera Film Scraper

## Setup HTTP Request Module

### Opzione 1: Endpoint JSON (per processare i dati)

**Module**: HTTP > Make a Request

**Configuration**:
- **URL**: `https://matera-film-scraper.onrender.com/api/films`
- **Method**: `GET`
- **Headers**: (nessun header necessario)
- **Response format**: `JSON`
- **Timeout**: `30` (secondi)

**Output**: Riceverai un JSON con tutti i dati dei film, cinema, date e orari.

---

### Opzione 2: Endpoint Telegram (pronto per inviare a Telegram)

**Module**: HTTP > Make a Request

**Configuration**:
- **URL**: `https://matera-film-scraper.onrender.com/api/films/telegram`
- **Method**: `GET`
- **Headers**: (nessun header necessario)
- **Response format**: `Text` (o `Raw`)
- **Timeout**: `30` (secondi)

**Output**: Riceverai il messaggio già formattato con emoji, pronto per essere inviato direttamente a Telegram.

---

## Esempio Scenario Completo

### Scenario: Invia messaggio Telegram automaticamente

1. **HTTP Module** (Make a Request):
   - URL: `https://matera-film-scraper.onrender.com/api/films/telegram`
   - Method: `GET`
   - Response format: `Text`

2. **Telegram Module** (Send a Message):
   - Chat ID: (il tuo chat ID o ID del canale)
   - Text: `{{1.text}}` (output del modulo HTTP precedente)
   - Parse mode: `Markdown` (per interpretare *bold*, emoji, etc.)

---

### Scenario: Salva su Google Sheets

1. **HTTP Module** (Make a Request):
   - URL: `https://matera-film-scraper.onrender.com/api/films`
   - Method: `GET`
   - Response format: `JSON`

2. **Google Sheets Module** (Add a Row):
   - Spreadsheet: (seleziona il tuo foglio)
   - Sheet: (seleziona il foglio)
   - Mappare i campi dal JSON:
     - Cinema: `{{1.cinema[0].cinema}}`
     - Film: `{{1.cinema[0].film[0].titolo}}`
     - Date: `{{1.cinema[0].film[0].programmazione[0].data}}`
     - Orari: `{{1.cinema[0].film[0].programmazione[0].orari}}`

---

## Struttura JSON (per riferimento)

Se usi l'endpoint `/api/films`, riceverai:

```json
{
  "timestamp": "2025-11-02T02:16:00.000000",
  "cinema": [
    {
      "cinema": "Cinema Comunale Guerrieri",
      "url": "...",
      "film": [
        {
          "titolo": "Bugonia",
          "orari": ["17.30", "19.35"],
          "sala": null,
          "programmazione": [
            {
              "data": "2025-11-03",
              "giorno": "lunedì",
              "orari": ["17:30", "19:35"]
            }
          ]
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

---

## Note Importanti

1. **Cold Start**: Se il servizio è spento (piano gratuito), la prima richiesta può richiedere 30-60 secondi. Imposta un timeout sufficiente (30 secondi).

2. **Errori**: Se la richiesta fallisce, verifica:
   - Che l'URL sia corretto
   - Che il servizio sia "Live" su Render (controlla il dashboard)
   - Che il timeout sia sufficiente

3. **Parsing**: Se usi il JSON, Make.com mapperà automaticamente i dati. Usa il visual mapper per vedere tutti i campi disponibili.

4. **Formato Telegram**: L'endpoint `/api/films/telegram` restituisce testo formattato con:
   - Emoji (🎬, 🎪, 📽️, etc.)
   - Markdown (`*bold*` per i titoli)
   - Formattazione già pronta per Telegram

---

## Test Rapido

Puoi testare l'endpoint prima di configurare Make.com:

```bash
# Test JSON
curl https://matera-film-scraper.onrender.com/api/films

# Test Telegram
curl https://matera-film-scraper.onrender.com/api/films/telegram
```

