#!/bin/bash
# Script per verificare lo stato del deploy su Render

RENDER_URL="https://matera-film-scraper.onrender.com"

echo "🔍 Verifica stato deploy Render"
echo "================================"
echo ""

# Verifica health
echo "1. Health check:"
curl -s "$RENDER_URL/health" | python3 -m json.tool 2>/dev/null || echo "❌ Servizio non raggiungibile"
echo ""

# Verifica endpoint Telegram
echo "2. Test endpoint Telegram (primi 200 caratteri):"
curl -s "$RENDER_URL/api/films/telegram" | head -c 200
echo "..."
echo ""

# Verifica endpoint JSON
echo "3. Test endpoint JSON (statistiche):"
curl -s "$RENDER_URL/api/films" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Cinema: {d.get('statistics', {}).get('total_cinema', 'N/A')}, Film: {d.get('statistics', {}).get('total_films', 'N/A')}\")" 2>/dev/null || echo "❌ Errore nel parsing JSON"
echo ""

echo "✅ Se tutti i test passano, il servizio è operativo!"
echo ""
echo "💡 Per forzare deploy manuale:"
echo "   1. Vai su https://dashboard.render.com"
echo "   2. Clicca sul servizio 'matera-film-scraper'"
echo "   3. Clicca 'Manual Deploy' in alto a destra"
echo "   4. Seleziona branch 'main' e commit più recente"

