# 3. Implementace komponenty a 4. Webové služby

## 3.1 Implementovaná komponenta

Klíčovou implementovanou komponentou je **rezervační služba**
(`src/reservation_service.py`), třída `RezervacniSluzba`. Zapouzdřuje business
logiku systému a je napojena na datovou vrstvu i na ostatní komponenty.

Hlavní metody a jejich kontroly, podle oblasti:

**Rezervace a jízda (FR3–FR8, FR15–FR17)**

| Metoda | Co dělá | Kontroly |
|--------|---------|----------|
| `zobraz_dostupna_vozidla()` | Vrátí volná vozidla, uklidí vypršelé rezervace (K1), předá vozidla mapě | – |
| `vytvor_rezervaci(uzivatel_id, vozidlo_id)` | Vytvoří rezervaci, vrátí i `platnost_do` (FR17 - countdown) | uživatel existuje a není zablokovaný, vozidlo je volné, nabití ≥ 20 % (K4) |
| `zrus_rezervaci(rezervace_id)` | Zruší rezervaci a uvolní vozidlo | rezervace je aktivní |
| `zahaj_jizdu(rezervace_id)` | Zahájí jízdu | rezervace je aktivní a nevypršela (K1) |
| `ukonci_jizdu(jizda_id, ujeto_km)` | Ukončí jízdu, sníží nabití (FR15), případně přepne vozidlo do údržby (FR16) a vytvoří fakturu (přeskočí se pro testovací jízdu, FR7a) | jízda ještě neskončila, `ujeto_km` nepřesahuje reálný dojezd podle aktuálního nabití (bugfix #14) |
| `historie_jizd(uzivatel_id)` | Vrátí jízdy uživatele, včetně účelu (běžná/testovací) | – |

**Platnost rezervace (K1, admin)**

| Metoda | Co dělá | Kontroly |
|--------|---------|----------|
| `ziskej_platnost_rezervace_minut()` | Vrátí aktuální limit (výchozí 30 min) | – |
| `nastav_platnost_rezervace(uzivatel_id, minuty)` | Změní limit platnosti rezervace | volající má roli `admin` |
| `over_a_vyprsele_rezervace()` | Interní - zruší vypršelé rezervace a uvolní jejich vozidla | – |

**Admin - uživatelé, flotila, faktury (FR9–FR11, FR18, FR19)**

| Metoda | Co dělá | Kontroly |
|--------|---------|----------|
| `vytvor_uzivatele(admin_id, jmeno, role)` | Vytvoří nového uživatele | volající má roli `admin`, role je platná |
| `nastav_zablokovani_uzivatele(admin_id, cilovy_uzivatel_id, zablokovan)` | (Od)blokuje uživatele | volající má roli `admin` |
| `zmen_roli_uzivatele(admin_id, cilovy_uzivatel_id, nova_role)` | Změní roli uživatele | volající má roli `admin`, role je platná |
| `pridej_vozidlo(admin_id, nazev, nabiti, lat, lon)` | Přidá vozidlo do flotily se stavem "volné" | volající má roli `admin` |
| `odeber_vozidlo(admin_id, vozidlo_id)` | Odebere vozidlo z flotily | volající má roli `admin`, vozidlo nemá aktivní rezervaci/jízdu |
| `vsechna_vozidla(uzivatel_id)` | Vrátí všechna vozidla (i mimo "volné"), s jménem aktivního uživatele u rezervovaných/v jízdě (FR18) | volající má roli `admin` nebo `technik` |
| `vsechny_faktury(admin_id, vozidlo_id=None, uzivatel_id=None)` | Přehled všech faktur, volitelně filtrovaný podle vozidla/uživatele (FR19) | volající má roli `admin` |

**Technik - servis vozidla (FR12, FR13)**

| Metoda | Co dělá | Kontroly |
|--------|---------|----------|
| `oznac_vozidlo_pro_udrzbu(technik_id, vozidlo_id)` | Přepne vozidlo do stavu "údržba" | volající má roli `technik`, vozidlo je "volné" |
| `ukonci_servis(technik_id, vozidlo_id, nabiti)` | Zapíše nové nabití; uvolní vozidlo, jen pokud je nabití ≥ 20 % - jinak zůstává v údržbě | volající má roli `technik`, vozidlo je "v údržbě" |

Každá metoda vrací slovník `{"ok": ..., "zprava": ...}` (případně s dalšími
údaji jako `rezervace_id` nebo seznamem výsledků), takže výsledek se dá stejně
použít v konzoli i v REST API. Metody vázané na roli (admin/technik) neověřují
identitu volajícího heslem, ale dohledáním role podle poslaného ID - viz K5
v kapitole 1.

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
| `GET /verze` | Verze backendu (footer frontendu, FR20) | – |
| `GET /uzivatele` | Seznam všech uživatelů (přihlašovací obrazovka) | – |
| `GET /vozidla` | Seznam dostupných (volných) vozidel | – |
| `POST /rezervace` | Vytvoří rezervaci | `{"uzivatel_id": 1, "vozidlo_id": 1}` |
| `POST /rezervace/{id}/zruseni` | Zruší rezervaci | – |
| `POST /jizdy` | Zahájí jízdu | `{"rezervace_id": 1}` |
| `POST /jizdy/{id}/ukonceni` | Ukončí jízdu, sníží baterii, případně vyfakturuje | `{"ujeto_km": 8}` |
| `POST /nastaveni/platnost-rezervace` | Změní limit platnosti rezervace (K1, jen admin) | `{"uzivatel_id": 2, "minuty": 45}` |
| `GET /uzivatele/{id}/historie` | Historie jízd uživatele (vč. účelu) | – |
| `POST /admin/uzivatele` | Vytvoří uživatele (jen admin) | `{"admin_id": 2, "jmeno": "...", "role": "uzivatel"}` |
| `POST /admin/uzivatele/{id}/zablokovani` | (Od)blokuje uživatele (jen admin) | `{"admin_id": 2, "zablokovan": true}` |
| `POST /admin/uzivatele/{id}/role` | Změní roli uživatele (jen admin) | `{"admin_id": 2, "role": "technik"}` |
| `POST /admin/vozidla` | Přidá vozidlo do flotily (jen admin) | `{"admin_id": 2, "nazev": "...", "nabiti": 100, "lat": 50.08, "lon": 14.42}` |
| `POST /admin/vozidla/{id}/odebrani` | Odebere vozidlo z flotily (jen admin) | `{"admin_id": 2}` |
| `GET /vozidla/vsechna` | Všechna vozidla vč. stavu a aktivního uživatele (admin/technik) | – (`uzivatel_id` jako query parametr) |
| `GET /admin/faktury` | Přehled všech faktur, filtrovatelný (jen admin) | – (`admin_id`, volitelně `vozidlo_id`/`uzivatel_id` jako query parametry) |
| `POST /vozidla/{id}/udrzba` | Označí vozidlo do servisu (jen technik) | `{"technik_id": 3}` |
| `POST /vozidla/{id}/ukonceni-servisu` | Ukončí servis, zapíše nabití (jen technik) | `{"technik_id": 3, "nabiti": 90}` |

Chybové stavy (např. málo nabité vozidlo, chybějící oprávnění) vrací HTTP kód
**400** s popisem chyby. FastAPI navíc automaticky vytvoří interaktivní
dokumentaci na `/docs`, kde je vidět i verze API (`GET /verze` /
`app = FastAPI(version=...)`).

Spuštění serveru (ve složce `src`):

```
uvicorn main:app --reload
```

Alternativně celý systém (API + frontend) přes `docker compose up --build` v
kořeni repozitáře - viz kapitola 2.5.

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

### 7) GET /verze
{"verze":"0.1.0"}

### 8) POST /admin/uzivatele  -d '{"admin_id":2,"jmeno":"Nova Novakova","role":"uzivatel"}'
{"ok":true,"zprava":"Uzivatel vytvoren.","uzivatel_id":4}

### 9) POST /vozidla/1/udrzba  -d '{"technik_id":3}'
{"ok":true,"zprava":"Vozidlo bylo oznaceno do servisu."}

### 10) POST /vozidla/1/udrzba  -d '{"technik_id":1}'   (bezny uzivatel, ne technik)
{"detail":"Pouze technik muze oznacit vozidlo do servisu."}     [HTTP 400]
```

Volání 6 ukazuje, že se pravidlo o minimálním nabití (konflikt K4) uplatní i
přes REST API, nejen v rezervační službě samotné. Volání 10 ukazuje totéž pro
autorizaci podle role (K5) - technikovská akce zavolaná s ID běžného
uživatele se odmítne.
