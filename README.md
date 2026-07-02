# Carsharing – systém pro správu sdílených elektromobilů

Zápočtový úkol ze Softwarového inženýrství. Návrh a částečná implementace systému
pro sdílení elektromobilů. Podrobnosti jsou v souboru `report.md`.

## Struktura projektu

```
carsharing/
├── report.md              # kompletní report (všech 6 bodů zadání)
├── report/                # jednotlivé sekce reportu
├── requirements.txt       # závislosti
├── curl_ukazky.sh         # ukázková volání REST API
└── src/                   # zdrojový kód
    ├── database.py             # datová vrstva (SQLite)
    ├── reservation_service.py  # klíčová komponenta – rezervační služba
    ├── billing.py              # mock fakturace
    ├── maps.py                 # mock mapové služby
    ├── notifications.py        # mock notifikací
    ├── console_demo.py         # konzolová ukázka
    ├── main.py                 # REST API (FastAPI)
    └── test_reservation.py     # testy
```

## Instalace

```
pip install -r requirements.txt
```

## Spuštění konzolové ukázky

```
cd src
python3 console_demo.py
```

Ukázka projde celý tok (zobrazení vozidel → rezervace → jízda → faktura →
historie) a na výstupu je vidět komunikace mezi komponentami.

## Spuštění REST API

```
cd src
uvicorn main:app --reload
```

Dokumentace API poté běží na `http://127.0.0.1:8000/docs`.
Ukázková volání jsou v `curl_ukazky.sh` (spusťte v jiném terminálu, když běží server).

## Spuštění testů

```
cd src
python3 -m pytest test_reservation.py -v
```
