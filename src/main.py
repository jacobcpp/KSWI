# main.py
# REST API nad rezervacni sluzbou (prezentacni vrstva).
# Pouziva FastAPI. Kazdy endpoint jen prevede HTTP pozadavek na volani
# rezervacni sluzby - sam neobsahuje business logiku.
#
# Spusteni:  uvicorn main:app --reload
# Dokumentace API po spusteni:  http://127.0.0.1:8000/docs

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import database
from reservation_service import RezervacniSluzba


app = FastAPI(title="Carsharing API")

# Soubor s databazi pro API.
DB_SOUBOR = "carsharing_api.db"


def priprav_databazi():
    # Vytvori tabulky a naplni ukazkova data, pokud je databaze prazdna.
    spojeni = database.vytvor_spojeni(DB_SOUBOR)
    database.vytvor_tabulky(spojeni)

    # Zjistime, jestli uz nejaka vozidla existuji.
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT COUNT(*) FROM vozidla")
    pocet = kurzor.fetchone()[0]
    if pocet == 0:
        database.napln_ukazkova_data(spojeni)

    spojeni.close()


# Pripravime databazi hned pri startu aplikace.
priprav_databazi()


def ziskej_sluzbu():
    # Pro kazdy pozadavek vytvorime nove spojeni (jednoduche a bezpecne).
    spojeni = database.vytvor_spojeni(DB_SOUBOR)
    return RezervacniSluzba(spojeni)


# ---------- Datove modely pro vstup (pydantic) ----------

class RezervaceVstup(BaseModel):
    uzivatel_id: int
    vozidlo_id: int


class JizdaVstup(BaseModel):
    rezervace_id: int


class UkonceniVstup(BaseModel):
    ujeto_km: float


# ---------- Endpointy ----------

@app.get("/vozidla")
def dostupna_vozidla():
    # Vrati seznam dostupnych vozidel.
    spojeni = database.vytvor_spojeni(DB_SOUBOR)
    vozidla = database.ziskej_dostupna_vozidla(spojeni)

    # Radky z databaze prevedeme na seznam slovniku.
    vysledek = []
    for vozidlo in vozidla:
        vysledek.append({
            "id": vozidlo["id"],
            "nazev": vozidlo["nazev"],
            "nabiti": vozidlo["nabiti"],
            "lat": vozidlo["lat"],
            "lon": vozidlo["lon"],
        })

    spojeni.close()
    return vysledek


@app.post("/rezervace")
def vytvor_rezervaci(vstup: RezervaceVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.vytvor_rezervaci(vstup.uzivatel_id, vstup.vozidlo_id)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.post("/rezervace/{rezervace_id}/zruseni")
def zrus_rezervaci(rezervace_id: int):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.zrus_rezervaci(rezervace_id)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.post("/jizdy")
def zahaj_jizdu(vstup: JizdaVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.zahaj_jizdu(vstup.rezervace_id)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.post("/jizdy/{jizda_id}/ukonceni")
def ukonci_jizdu(jizda_id: int, vstup: UkonceniVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.ukonci_jizdu(jizda_id, vstup.ujeto_km)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.get("/uzivatele/{uzivatel_id}/historie")
def historie(uzivatel_id: int):
    sluzba = ziskej_sluzbu()
    jizdy = sluzba.historie_jizd(uzivatel_id)
    sluzba.spojeni.close()

    vysledek = []
    for jizda in jizdy:
        vysledek.append({
            "jizda_id": jizda["id"],
            "vozidlo_id": jizda["vozidlo_id"],
            "ujeto_km": jizda["ujeto_km"],
            "cas_start": jizda["cas_start"],
            "cas_konec": jizda["cas_konec"],
        })

    return vysledek
