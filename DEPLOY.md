# Guida al Deploy su Render.com (GRATIS)

## Perché Render.com?

- ✅ **Gratuito**: Tier gratuito generoso
- ✅ **Perfetto per uso sporadico**: Il servizio si spegne dopo inattività (ok per chiamate ogni 2-3 giorni)
- ✅ **Facile da usare**: Setup in pochi minuti
- ✅ **HTTPS incluso**: URL sicuro incluso
- ⚠️ **Cold start**: La prima richiesta dopo lo spegnimento può richiedere 30-60 secondi (accettabile per il tuo uso)

## Passo 1: Preparare il repository Git

Assicurati che il progetto sia su GitHub/GitLab/Bitbucket:

```bash
# Se non hai ancora inizializzato git
git init
git add .
git commit -m "Initial commit"

# Aggiungi il remote (sostituisci con il tuo repository)
git remote add origin https://github.com/tuonome/matera_film_scraper.git
git push -u origin main
```

## Passo 2: Deploy su Render

1. **Vai su** [https://render.com](https://render.com)

2. **Registrati** con GitHub (più facile)

3. **Clicca su "New +"** → **"Web Service"**

4. **Connetti il repository**:
   - Se hai già connesso GitHub, seleziona il repository `matera_film_scraper`
   - Oppure collega GitHub e autorizza Render ad accedere ai tuoi repository

5. **Configurazione del servizio**:
   - **Name**: `matera-film-scraper` (o quello che preferisci)
   - **Region**: `Frankfurt` (più vicino all'Italia) o `Oregon` (USA)
   - **Branch**: `main` (o `master`)
   - **Root Directory**: *(lascia vuoto)*
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

6. **Plan**: Seleziona **"Free"** (il piano gratuito)

7. **Clicca "Create Web Service"**

Render inizierà a fare il deploy. La prima volta potrebbe richiedere 5-10 minuti.

## Passo 3: Verifica il deploy

1. Render ti darà un URL tipo: `https://matera-film-scraper.onrender.com`

2. Testa l'endpoint:
   ```
   https://tuo-nome.onrender.com/api/films
   ```

3. La prima chiamata potrebbe richiedere 30-60 secondi se il servizio è "spento" (cold start)

## Passo 4: Usa con Make.com

In Make.com, configura:
- **URL**: `https://tuo-nome.onrender.com/api/films`
- **Method**: `GET`
- **Response format**: `JSON`

## Note importanti

- **Cold Start**: Dopo 15 minuti di inattività, Render spegne il servizio. La prima richiesta dopo può richiedere 30-60 secondi. Non è un problema per il tuo uso!
- **Limite gratuito**: 750 ore/mese di runtime (più che sufficiente per il tuo caso)
- **Timeout**: Le richieste hanno un timeout di 30 secondi. Lo scraper dovrebbe completarsi prima.

## Alternative gratuite (se Render non ti convince)

### Railway.app
- Tier gratuito con $5 di crediti/mese
- Nessun cold start
- Più veloce ma può esaurire i crediti se lasci acceso 24/7

### Fly.io
- Tier gratuito generoso
- Un po' più complesso da configurare
- Nessun cold start

---

**Consiglio**: Inizia con Render.com, è il più semplice per il tuo caso d'uso!

