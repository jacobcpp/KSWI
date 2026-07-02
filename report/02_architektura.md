# 2. Softwarová architektura

## 2.1 Volba architektury

Pro systém byla zvolena **vrstvená architektura (layered / monolitická)**, nikoli
mikroslužby.

### Zdůvodnění

Zvažovány byly dvě varianty:

**Vrstvená architektura (zvolená):**
- Systém je v této fázi malý a spravuje ho jeden tým – monolit je jednodušší na
  vývoj, nasazení i testování.
- Jednotlivé odpovědnosti se dají čistě oddělit do vrstev (prezentace, logika,
  data), takže kód zůstává přehledný a snadno rozšiřitelný (splňuje NFR6).
- Nižší provozní režie – jedna aplikace, jedna databáze, žádná složitá
  komunikace po síti mezi službami.

**Mikroslužby (zamítnuty pro tuto fázi):**
- Přinesly by zbytečnou složitost (síťová komunikace, distribuované transakce,
  více nasazení) pro systém, který zatím nemá velkou zátěž ani velký tým.
- Mají smysl až při růstu (mnoho měst, vysoká zátěž) – proto jsou uvedeny jako
  možná evoluce v kapitole 6.

Vrstvená architektura je zároveň dobrým výchozím bodem: jednotlivé vrstvy a
komponenty jsou navrženy tak, aby z nich šlo v budoucnu vyčlenit samostatné
služby, pokud to bude potřeba.

## 2.2 Vrstvy systému

```mermaid
flowchart TB
    subgraph P[Prezentační vrstva]
        API[REST API - FastAPI]
        CLI[Konzolová ukázka]
    end
    subgraph L[Logická vrstva - business logika]
        RES[Rezervační služba - KLÍČOVÁ KOMPONENTA]
        BIL[Fakturace - mock]
        MAP[Mapová služba - mock]
        NOT[Notifikace - mock]
    end
    subgraph D[Datová vrstva]
        DB[(SQLite databáze)]
    end

    API --> RES
    CLI --> RES
    RES --> BIL
    RES --> MAP
    RES --> NOT
    RES --> DB
    BIL --> DB
```

- **Prezentační vrstva** – přijímá požadavky zvenčí. Obsahuje REST API (FastAPI)
  pro webové volání a konzolovou ukázku, která demonstruje komunikaci komponent.
- **Logická vrstva** – jádro systému. Obsahuje rezervační službu (klíčová
  komponenta) a pomocné služby fakturace, mapy a notifikací (v této fázi mocky).
- **Datová vrstva** – SQLite databáze, přístup přes jednoduchý modul `database.py`.

## 2.3 Diagram komponent a interakce

Následující diagram ukazuje hlavní komponenty a to, jak spolu komunikují při
rezervaci a jízdě. Podle zadání nejde o striktní UML.

```mermaid
flowchart LR
    subgraph Klient
        U[Uživatel / HTTP klient]
    end

    API[REST API]
    RES[Rezervační služba]
    DB[(SQLite)]
    MAP[Mapová služba - mock]
    BIL[Fakturace - mock]
    NOT[Notifikace - mock]

    U -- HTTP požadavek --> API
    API -- volá metody --> RES
    RES -- čte/zapisuje vozidla a rezervace --> DB
    RES -- ověří polohu / dostupnost --> MAP
    RES -- po jízdě vytvoří fakturu --> BIL
    RES -- pošle potvrzení --> NOT
    BIL -- uloží fakturu --> DB
    API -- HTTP odpověď --> U
```

### Popis interakcí

1. **Klient → REST API** – uživatel (nebo curl/Postman) pošle HTTP požadavek,
   např. „rezervuj vozidlo".
2. **REST API → Rezervační služba** – API zavolá odpovídající metodu služby.
   Samo neobsahuje business logiku, jen převádí HTTP na volání služby.
3. **Rezervační služba → Databáze** – služba načte stav vozidla a uživatele,
   ověří podmínky (volné vozidlo, dostatečné nabití, neblokovaný uživatel) a
   uloží novou rezervaci.
4. **Rezervační služba → Mapová služba** – ověří / doplní informace o poloze
   vozidla (v této fázi mock, který vrací připravená data).
5. **Rezervační služba → Fakturace** – po ukončení jízdy si vyžádá vytvoření
   faktury; fakturace spočítá cenu a uloží ji.
6. **Rezervační služba → Notifikace** – odešle uživateli potvrzení (mock tiskne
   na stdout).
7. **REST API → Klient** – vrátí výsledek operace (např. ID rezervace nebo chybu).

## 2.4 Mapování komponent na soubory

Aby report a kód na sebe navazovaly, každá komponenta odpovídá jednomu souboru:

| Komponenta | Soubor | Odpovědnost |
|------------|--------|-------------|
| Datová vrstva | `src/database.py` | Vytvoření tabulek a přístup k datům (SQLite) |
| Rezervační služba (klíčová) | `src/reservation_service.py` | Rezervace, kontroly stavu, jízdy |
| Fakturace (mock) | `src/billing.py` | Výpočet a uložení faktury |
| Mapová služba (mock) | `src/maps.py` | Poloha a dostupnost vozidel |
| Notifikace (mock) | `src/notifications.py` | Odeslání zpráv uživateli |
| Konzolová ukázka | `src/console_demo.py` | Demonstrace komunikace komponent |
| REST API | `src/main.py` | HTTP rozhraní nad rezervační službou |
