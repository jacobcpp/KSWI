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

echo "### 8) Verze backendu"
curl -s $ZAKLAD/verze; echo

echo "### 9) Admin (uzivatel 2) vytvori noveho uzivatele"
curl -s -X POST $ZAKLAD/admin/uzivatele \
     -H "Content-Type: application/json" \
     -d '{"admin_id":2,"jmeno":"Nova Novakova","role":"uzivatel"}'; echo

echo "### 10) Technik (uzivatel 3) oznaci vozidlo 1 do servisu"
curl -s -X POST $ZAKLAD/vozidla/1/udrzba \
     -H "Content-Type: application/json" \
     -d '{"technik_id":3}'; echo

echo "### 11) Bezny uzivatel (1) zkusi totez - ma byt odmitnuto"
curl -s -X POST $ZAKLAD/vozidla/1/udrzba \
     -H "Content-Type: application/json" \
     -d '{"technik_id":1}'; echo

echo "### 12) Admin (2) vidi vsechny faktury"
curl -s "$ZAKLAD/admin/faktury?admin_id=2"; echo
