# Systém pro správu sdílených elektromobilů

**Zápočtový úkol – Softwarové inženýrství**

Návrh a částečná implementace softwarového systému pro správu sdílených
elektromobilů ve městě. Report pokrývá inženýrství požadavků, návrh architektury,
implementaci klíčové komponenty s REST API, testování a návrh evoluce systému.

## Obsah

1. Inženýrství požadavků – role, use case a activity diagramy, funkční a
   nefunkční požadavky, konfliktní požadavky a jejich řešení
2. Softwarová architektura – volba architektury, diagram komponent
3. Implementace komponenty (rezervační služba) a 4. Webové služby (REST API)
5. Testování softwaru – implementované testy a testovací plán
6. Evoluce softwaru – návrh budoucích změn

**Technologie:** Python 3.12, FastAPI, SQLite, vanilla JS/nginx (frontend),
Docker Compose (nasazení). Backend je v adresáři `src/` (spustitelná
konzolová ukázka `src/console_demo.py`, REST API `src/main.py`), webový
frontend v adresáři `frontend/`.

---

