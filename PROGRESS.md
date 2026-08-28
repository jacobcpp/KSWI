# PROGRESS – Zápočtový úkol SWI (systém sdílených elektromobilů)

Tento soubor je kontrolní bod. Kdokoli (i nová session) si přečte tento soubor
a hotové soubory a plynule naváže tam, kde se skončilo.

## Zadání (stručně)
Návrh + částečná implementace systému pro správu sdílených elektromobilů ve městě.
6 bodů: (1) požadavky, (2) architektura, (3) implementace komponenty, (4) REST API,
(5) testování, (6) evoluce. Výstup: report ~10 stran (Markdown) + spustitelný kód (zip).

## Rozhodnutí (neměnit bez domluvy s uživatelem)
- **Jazyk kódu:** Python 3.12 + FastAPI
- **Styl kódu:** jako začátečník – žádné komprehence, žádný async navíc, žádná "magie",
  jasné názvy proměnných, komentáře česky. (Výjimka: FastAPI vyžaduje jednoduché
  pydantic modely, dekorátory a základní type hints v hlavičkách funkcí – to je OK.)
- **Databáze:** SQLite přes vestavěný modul `sqlite3` (žádné ORM)
- **Diagramy:** Mermaid přímo v Markdownu
- **Report:** česky
- **Role uživatelů:** běžný uživatel, admin, servisní technik
- **Klíčová komponenta:** rezervační služba. Ostatní části (fakturace, mapa,
  notifikace) jsou jednoduché mocky, které tisknou na stdout.

## Struktura projektu
```
carsharing/
├── PROGRESS.md              # tento soubor
├── requirements.txt         # závislosti
├── report/                  # části reportu (na konci spojeny do report.md)
│   ├── 01_pozadavky.md
│   ├── 02_architektura.md
│   ├── 05_testovani.md
│   └── 06_evoluce.md
└── src/                     # zdrojový kód
    ├── database.py          # SQLite – tabulky a přístup k datům
    ├── reservation_service.py  # KLÍČOVÁ komponenta – rezervační logika
    ├── billing.py           # mock fakturace
    ├── maps.py              # mock mapové služby
    ├── notifications.py     # mock notifikací
    ├── console_demo.py      # konzolová ukázka komunikace komponent
    ├── main.py              # REST API (FastAPI)
    └── test_reservation.py  # testy (pytest)
```

## Stav kroků
- [x] Krok 0 – Setup (struktura, PROGRESS.md, requirements.txt)
- [x] Krok 1 – Požadavky -> report/01_pozadavky.md
- [x] Krok 2 – Architektura -> report/02_architektura.md
- [x] Krok 3 – Implementace jádra -> src/database.py, reservation_service.py, mocky, console_demo.py
- [x] Krok 4 – REST API -> src/main.py + curl ukázky
- [x] Krok 5 – Testy -> src/test_reservation.py + report/05_testovani.md
- [x] Krok 6 – Evoluce -> report/06_evoluce.md
- [x] Krok 7 – Finalizace -> report.md (spojeni) + carsharing.zip

## Poznámky k navázání
(sem se během práce doplňují důležité věci, např. názvy tabulek, signatury funkcí,
aby na sebe kód a report navazovaly)

### Z kroku 1 (požadavky) – co se musí promítnout do kódu (krok 3)
- Stavy vozidla (FR14): `volne`, `rezervovano`, `v_jizde`, `udrzba`.
- K1: rezervace má časový limit platnosti (výchozí 30 min, mění jen admin,
  tabulka `nastaveni`) -> FR5.
- K2: účtuje se jen jízda (od zahájení do ukončení), rezervace zdarma.
- K3: technik smí i rezervovat vozidlo jako běžný uživatel - jde o testovací
  jízdu (sloupec `ucel` na rezervaci), která se nefakturuje.
- K4: minimální nabití pro rezervaci (konstanta, např. 20 %).
- Klíčová komponenta = rezervační služba, kontroluje: stav vozidla == volne,
  nabití >= minimum, uživatel není zablokovaný.

### Z kroku 3 (kód) – pro navázání v krocích 4 (API) a 5 (testy)
- Tabulky: uzivatele, vozidla, rezervace, jizdy, faktury, nastaveni.
- Třída `RezervacniSluzba(spojeni)` v `reservation_service.py`, metody vrací
  slovník `{"ok": bool, "zprava": str, ...}`:
  - `zobraz_dostupna_vozidla()`
  - `vytvor_rezervaci(uzivatel_id, vozidlo_id)` -> + "rezervace_id"
  - `zrus_rezervaci(rezervace_id)`
  - `zahaj_jizdu(rezervace_id)` -> + "jizda_id"
  - `ukonci_jizdu(jizda_id, ujeto_km)` -> + "faktura_id"
  - `historie_jizd(uzivatel_id)` -> seznam řádků
- Konstanty: MIN_NABITI_PROCENT=20, PLATNOST_REZERVACE_MINUT_VYCHOZI=30, CENA_ZA_KM=5.0.
  Platnost rezervace lze prepsat pres `RezervacniSluzba.nastav_platnost_rezervace`
  (jen role admin), hodnota se ukladá do tabulky `nastaveni`.
- `database.vytvor_spojeni(":memory:")` pro testy (DB v paměti).
- Ukázková data: uživatel 1=uzivatel, 2=admin, 3=technik; vozidlo 1=Auto A(volne,80),
  2=Auto B(volne,15 -> pod limitem), 3=Auto C(udrzba,50).
- Importy v kódu jsou "ploché" (import database), takže se spouští ze složky src/.

### Z kroku 4 (REST API) – pro navázání v kroku 5 (testy)
- `src/main.py` (FastAPI), DB soubor "carsharing_api.db", při startu seed pokud prázdná.
- Endpointy: GET /vozidla, POST /rezervace, POST /rezervace/{id}/zruseni,
  POST /jizdy, POST /jizdy/{id}/ukonceni, GET /uzivatele/{id}/historie,
  POST /nastaveni/platnost-rezervace (jen admin, K1).
- Chyby vrací HTTP 400 (HTTPException) s detailem = zprava ze služby.
- Ověřeno curl skriptem curl_ukazky.sh (v kořeni projektu). Sekce reportu:
  report/03_implementace_api.md (pokrývá body 3 i 4 zadání).
- Pro integrační test API půjde použít fastapi TestClient (httpx je nainstalováno).
