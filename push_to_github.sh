#!/bin/bash
# Script per pushare il repository su GitHub

# Aggiungi il remote (se non esiste già)
git remote remove origin 2>/dev/null
git remote add origin https://github.com/alexandermaffei/matera_film_scraper.git

# Push al branch main
git branch -M main
git push -u origin main

echo ""
echo "✓ Push completato!"
echo "Repository: https://github.com/alexandermaffei/matera_film_scraper"

