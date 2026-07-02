# 3. Implementace komponenty a 4. Webové služby

## 3.1 Implementovaná komponenta

Klíčovou implementovanou komponentou je **rezervační služba**
(`src/reservation_service.py`), třída `RezervacniSluzba`. Zapouzdřuje business
logiku systému a je napojena na datovou vrstvu i na ostatní komponenty.

Hlavní metody a jejich kontroly:

| Metoda | Co dělá | Kontroly |
|--------|---------|----------|
| `zobraz_dostupna_vozidla()` | Vrátí volná vozidla a předá je mapě | – |
| `vytvor_rezervaci(uzivatel_id, vozidlo_id)` | Vytvoří rezervaci | uživatel existuje a není zablokovaný, vozidlo je volné, nabití ≥ 20 % (K4) |
| `zrus_rezervaci(rezervace_id)` | Zruší rezervaci a uvolní vozidlo | rezervace je aktivní |
| `zahaj_jizdu(rezervace_id)` | Zahájí jízdu | rezervace je aktivní a nevypršela (K1) |
| `ukonci_jizdu(jizda_id, ujeto_km)` | Ukončí jízdu a vytvoří fakturu | jízda ještě neskončila |
| `historie_jizd(uzivatel_id)` | Vrátí jízdy uživatele | – |

Každá metoda vrací slovník `{"ok": ..., "zprava": ...}` (případně s dalšími údaji
jako `rezervace_id`), takže výsledek se dá stejně použít v konzoli i v REST API.

## 3.2 Komunikace s ostatními komponentami

Rezervační služba komunikuje s dalšími částmi systému. Ostatní komponenty jsou
v této fázi mocky, které tisknou na standardní výstup, takže je komunikace vidět.

Výstup konzolové ukázky (`src/console_demo.py`) při rezervaci a jízdě:

```
[MAPA] Zobrazuji dostupna vozidla na mape:
   - Auto A na pozici 50.08 14.42 (nabiti 80 %)
   - Auto B na pozici 50.09 14.43 (nabiti 15 %)
[MAPA] Overuji polohu vozidla Auto A
[NOTIFIKACE] Uzivatel c. 1 -> Vase rezervace vozidla byla vytvorena.
...
[FAKTURACE] Vytvarim fakturu za jizdu c. 1 - ujeto 12 km, castka 60.0 Kc
[NOTIFIKACE] Uzivatel c. 1 -> Vase jizda byla ukoncena a vyuctovana.
```

Z výstupu je vidět, že rezervační služba postupně volá **mapovou službu**
(zobrazení a ověření polohy), **notifikace** (potvrzení uživateli) a
**fakturaci** (vytvoření faktury po jízdě). Také je vidět kontrola z konfliktu
K4 – vozidlo s nízkým nabitím (Auto B) systém odmítne rezervovat.

## 4.1 REST API

Nad rezervační službou je jednoduché REST API (`src/main.py`, FastAPI).
Endpointy jen převádějí HTTP požadavky na volání služby.

| Metoda a cesta | Popis | Tělo požadavku |
|----------------|-------|----------------|
| `GET /vozidla` | Seznam dostupných vozidel | – |
| `POST /rezervace` | Vytvoří rezervaci | `{"uzivatel_id": 1, "vozidlo_id": 1}` |
| `POST /rezervace/{id}/zruseni` | Zruší rezervaci | – |
| `POST /jizdy` | Zahájí jízdu | `{"rezervace_id": 1}` |
| `POST /jizdy/{id}/ukonceni` | Ukončí jízdu a vyfakturuje | `{"ujeto_km": 8}` |
| `GET /uzivatele/{id}/historie` | Historie jízd uživatele | – |

Chybové stavy (např. málo nabité vozidlo) vrací HTTP kód **400** s popisem chyby.
FastAPI navíc automaticky vytvoří interaktivní dokumentaci na `/docs`.

Spuštění serveru (ve složce `src`):

```
uvicorn main:app --reload
```

## 4.2 Ukázka volání (curl)

Následující volání byla skutečně spuštěna proti běžícímu API. Skript je také
v souboru `curl_ukazky.sh`.

```
### 1) GET /vozidla
[{"id":1,"nazev":"Auto A","nabiti":80,"lat":50.08,"lon":14.42},
 {"id":2,"nazev":"Auto B","nabiti":15,"lat":50.09,"lon":14.43}]

### 2) POST /rezervace  -d '{"uzivatel_id":1,"vozidlo_id":1}'
{"ok":true,"zprava":"Rezervace vytvorena.","rezervace_id":1}

### 3) POST /jizdy  -d '{"rezervace_id":1}'
{"ok":true,"zprava":"Jizda zahajena.","jizda_id":1}

### 4) POST /jizdy/1/ukonceni  -d '{"ujeto_km":8}'
{"ok":true,"zprava":"Jizda ukoncena.","faktura_id":1}

### 5) GET /uzivatele/1/historie
[{"jizda_id":1,"vozidlo_id":1,"ujeto_km":8.0,
  "cas_start":"...","cas_konec":"..."}]

### 6) POST /rezervace  -d '{"uzivatel_id":1,"vozidlo_id":2}'   (nizke nabiti)
{"detail":"Vozidlo ma prilis nizke nabiti."}     [HTTP 400]
```

Poslední volání ukazuje, že se pravidlo o minimálním nabití (konflikt K4)
uplatní i přes REST API, nejen v rezervační službě samotné.
