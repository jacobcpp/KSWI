#!/bin/bash
# curl_ukazky.sh
# Ukazkova volani REST API pomoci curl.
# Nejdriv spustte server ve slozce src:
#   uvicorn main:app --reload
# Pak spustte tento skript:  bash curl_ukazky.sh

ZAKLAD="http://127.0.0.1:8000"

echo "### 1) Seznam dostupnych vozidel"
curl -s $ZAKLAD/vozidla; echo

echo "### 2) Vytvoreni rezervace (uzivatel 1 rezervuje vozidlo 1)"
curl -s -X POST $ZAKLAD/rezervace \
     -H "Content-Type: application/json" \
     -d '{"uzivatel_id":1,"vozidlo_id":1}'; echo

echo "### 3) Zahajeni jizdy (z rezervace 1)"
curl -s -X POST $ZAKLAD/jizdy \
     -H "Content-Type: application/json" \
     -d '{"rezervace_id":1}'; echo

echo "### 4) Ukonceni jizdy c. 1 (ujeto 8 km)"
curl -s -X POST $ZAKLAD/jizdy/1/ukonceni \
     -H "Content-Type: application/json" \
     -d '{"ujeto_km":8}'; echo

echo "### 5) Historie jizd uzivatele 1"
curl -s $ZAKLAD/uzivatele/1/historie; echo

echo "### 6) Zruseni rezervace c. 1 (pokud jeste existuje)"
curl -s -X POST $ZAKLAD/rezervace/1/zruseni; echo

echo "### 7) Zmena platnosti rezervace na 45 minut (admin, uzivatel 2)"
curl -s -X POST $ZAKLAD/nastaveni/platnost-rezervace \
     -H "Content-Type: application/json" \
     -d '{"uzivatel_id":2,"minuty":45}'; echo
