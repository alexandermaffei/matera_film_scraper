# Come verificare e forzare deploy su Render

## Verifica dello stato del deploy

### 1. Tramite Dashboard Render
1. Vai su [render.com](https://render.com) e accedi
2. Clicca sul tuo servizio `matera-film-scraper`
3. Nella sezione **"Events"** o **"Deploys"** vedrai:
   - Lo stato del deploy più recente (Building, Live, Failed)
   - Il commit associato (hash e messaggio)
   - Timestamp del deploy

### 2. Verifica il commit deployato
Nel dashboard di Render, cerca la sezione "Recent Deploys" e verifica:
- **Commit message**: Dovrebbe essere "Aggiunto formato Telegram: messaggio formattato con emoji..."
- **Commit hash**: Dovrebbe iniziare con `3db763d` (l'ultimo commit)
- **Status**: Dovrebbe essere "Live" se il deploy è completato

### 3. Test diretto dell'endpoint
Una volta che il deploy è completato, testa:
```bash
# Test endpoint JSON
curl https://matera-film-scraper.onrender.com/api/films

# Test endpoint Telegram
curl https://matera-film-scraper.onrender.com/api/films/telegram

# Test health check
curl https://matera-film-scraper.onrender.com/health
```

## Forzare deploy manuale

### Opzione 1: Manual Deploy dal Dashboard (CONSIGLIATO)
1. Vai sul dashboard di Render
2. Clicca sul tuo servizio `matera-film-scraper`
3. In alto a destra, clicca sul pulsante **"Manual Deploy"**
4. Seleziona il branch (di solito `main`)
5. Seleziona il commit che vuoi deployare (di solito il più recente)
6. Clicca **"Deploy"**

### Opzione 2: Render CLI (se installato)
Se hai installato Render CLI:
```bash
# Installa Render CLI (se non ce l'hai)
npm install -g render-cli

# Login
render login

# Forza deploy
render services:deploy <service-id> --ref main
```

### Opzione 3: Push vuoto (trick)
Se non hai Render CLI, puoi fare un commit vuoto per forzare il deploy:
```bash
git commit --allow-empty -m "Trigger deploy"
git push origin main
```

## Verificare che il nuovo codice sia attivo

### Test endpoint Telegram
Dopo il deploy, verifica che il nuovo endpoint funzioni:
```bash
curl https://matera-film-scraper.onrender.com/api/films/telegram
```

Dovresti vedere il messaggio formattato con emoji.

### Verifica versioni
Nel dashboard Render, nella sezione "Logs", dovresti vedere:
- Il commit hash durante il build
- Messaggi di build che confermano l'installazione delle dipendenze

## Troubleshooting

### Il deploy non parte automaticamente
- Verifica che il repository sia connesso correttamente
- Controlla che il branch sia `main` (non `master`)
- Assicurati che Auto-Deploy sia abilitato nelle impostazioni del servizio

### Il deploy fallisce
- Controlla i log nel dashboard Render
- Verifica che tutte le dipendenze siano in `requirements.txt`
- Assicurati che `Procfile` sia presente e corretto

### Il servizio si spegne dopo inattività
- È normale sul piano gratuito
- La prima richiesta dopo lo spegnimento può richiedere 30-60 secondi (cold start)
- Non è un problema per il tuo uso sporadico

## Checklist post-deploy

- [ ] Il servizio mostra status "Live" nel dashboard
- [ ] L'endpoint `/health` risponde correttamente
- [ ] L'endpoint `/api/films` restituisce JSON valido
- [ ] L'endpoint `/api/films/telegram` restituisce il messaggio formattato
- [ ] Il messaggio Telegram contiene emoji e formattazione corretta

