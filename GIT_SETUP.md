# Setup Git per account diverso

Per usare un account GitHub diverso da quello globale, puoi:

## Opzione 1: Configurare solo questo repository

```bash
# Configura nome e email solo per questo repository
git config user.name "Tuo Username"
git config user.email "tua.email@example.com"
```

Oppure esegui lo script:
```bash
./setup_git.sh
```

## Opzione 2: Fare commit e push manualmente

1. **Configura git per questo repo** (se non l'hai già fatto):
   ```bash
   git config user.name "Tuo Username"
   git config user.email "tua.email@example.com"
   ```

2. **Aggiungi i file**:
   ```bash
   git add .
   ```

3. **Fai il commit**:
   ```bash
   git commit -m "Initial commit: Matera Film Scraper"
   ```

4. **Crea un repository su GitHub**:
   - Vai su [github.com](https://github.com)
   - Clicca "New repository"
   - Nome: `matera_film_scraper` (o quello che preferisci)
   - Non inizializzare con README/gitignore (abbiamo già tutto)
   - Clicca "Create repository"

5. **Aggiungi il remote e push**:
   ```bash
   git remote add origin https://github.com/TUO_USERNAME/matera_film_scraper.git
   git branch -M main
   git push -u origin main
   ```

## Nota importante

Se hai autenticazione SSH configurata per l'altro account, potresti dover:
- Usare HTTPS invece di SSH per il remote
- Oppure configurare SSH per questo account specifico

Se usi HTTPS, GitHub potrebbe chiederti username/password. Puoi usare un **Personal Access Token** invece della password:
- Vai su GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Genera un nuovo token con permessi `repo`
- Usa il token come password quando richiesto

