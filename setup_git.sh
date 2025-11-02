#!/bin/bash
# Script per configurare git per questo repository con un account diverso

echo "Configurazione Git per questo repository"
echo ""
echo "Inserisci le credenziali per il nuovo account GitHub:"
echo ""

read -p "Username GitHub: " GIT_USERNAME
read -p "Email GitHub: " GIT_EMAIL

# Configura solo per questo repository (non globalmente)
git config user.name "$GIT_USERNAME"
git config user.email "$GIT_EMAIL"

echo ""
echo "✓ Configurato git per questo repository:"
echo "  Username: $GIT_USERNAME"
echo "  Email: $GIT_EMAIL"
echo ""
echo "Prossimi passi:"
echo "1. Crea un nuovo repository su GitHub (se non esiste già)"
echo "2. Aggiungi i file: git add ."
echo "3. Fai il commit: git commit -m 'Initial commit'"
echo "4. Aggiungi il remote: git remote add origin https://github.com/$GIT_USERNAME/matera_film_scraper.git"
echo "5. Push: git push -u origin main"

