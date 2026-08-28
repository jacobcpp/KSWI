#!/bin/sh
# Pred startem nginx vygeneruje js/config.js podle promenne prostredi
# API_BASE_URL - musi to byt adresa dosazitelna z prohlizece uzivatele,
# ne interni nazev sluzby v docker siti (viz docker-compose.yml).
set -e

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

cat > /usr/share/nginx/html/js/config.js <<EOF
window.API_BASE = "${API_BASE_URL}";
EOF
