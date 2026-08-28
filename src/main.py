# main.py
# REST API nad rezervacni sluzbou (prezentacni vrstva).
# Pouziva FastAPI. Kazdy endpoint jen prevede HTTP pozadavek na volani
# rezervacni sluzby - sam neobsahuje business logiku.
#
# Spusteni:  uvicorn main:app --reload
# Dokumentace API po spusteni:  http://127.0.0.1:8000/docs

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
from reservation_service import RezervacniSluzba


# Verze backendu (SemVer) - viz issue #21. Zvysuje se rucne: MINOR za novou
# funkcionalitu, PATCH za bugfix, nezavisle na verzi frontendu.
VERZE = "0.1.0"

app = FastAPI(title="Carsharing API", version=VERZE)

# Frontend bezi na jinem originu (jiny kontejner/port), takze potrebuje CORS.
# Zadna autentizace se neresi - viz issue #3 a otevrena otazka u K3 v reportu.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Soubor s databazi pro API. V Dockeru se prepisuje promennou prostredi
# DB_CESTA na cestu v pripojenem volume, aby databaze prezila rebuild
# i restart kontejneru (issue #6). Bez ni se pouzije puvodni chovani
# (soubor v aktualnim adresari - pro lokalni beh mimo Docker).
DB_SOUBOR = os.environ.get("DB_CESTA", "carsharing_api.db")


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


class PlatnostRezervaceVstup(BaseModel):
    uzivatel_id: int
    minuty: int


class NovyUzivatelVstup(BaseModel):
    admin_id: int
    jmeno: str
    role: str


class ZablokovaniVstup(BaseModel):
    admin_id: int
    zablokovan: bool


class RoleVstup(BaseModel):
    admin_id: int
    role: str


class NoveVozidloVstup(BaseModel):
    admin_id: int
    nazev: str
    nabiti: int
    lat: float
    lon: float


class OdebraniVozidlaVstup(BaseModel):
    admin_id: int


class OznaceniUdrzbyVstup(BaseModel):
    technik_id: int


class UkonceniServisuVstup(BaseModel):
    technik_id: int
    nabiti: int


# ---------- Endpointy ----------

@app.get("/verze")
def verze():
    # Pro footer frontendu (issue #21), aby slo poznat, co je zrovna spustene.
    return {"verze": VERZE}


@app.get("/uzivatele")
def seznam_uzivatelu():
    # Vrati vsechny uzivatele - pouziva frontend na prihlasovaci obrazovce
    # (vyber uzivatele misto skutecneho loginu, viz issue #3).
    spojeni = database.vytvor_spojeni(DB_SOUBOR)
    uzivatele = database.ziskej_vsechny_uzivatele(spojeni)

    vysledek = []
    for uzivatel in uzivatele:
        vysledek.append({
            "id": uzivatel["id"],
            "jmeno": uzivatel["jmeno"],
            "role": uzivatel["role"],
            "zablokovan": bool(uzivatel["zablokovan"]),
        })

    spojeni.close()
    return vysledek


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


@app.post("/nastaveni/platnost-rezervace")
def nastav_platnost_rezervace(vstup: PlatnostRezervaceVstup):
    # Zmena limitu platnosti rezervace (K1) - smi jen administrator.
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.nastav_platnost_rezervace(vstup.uzivatel_id, vstup.minuty)
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
            "ucel": jizda["ucel"],
        })

    return vysledek


# ---------- Admin: sprava uzivatelu ----------

@app.post("/admin/uzivatele")
def vytvor_uzivatele(vstup: NovyUzivatelVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.vytvor_uzivatele(vstup.admin_id, vstup.jmeno, vstup.role)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.post("/admin/uzivatele/{uzivatel_id}/zablokovani")
def nastav_zablokovani(uzivatel_id: int, vstup: ZablokovaniVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.nastav_zablokovani_uzivatele(vstup.admin_id, uzivatel_id, vstup.zablokovan)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.post("/admin/uzivatele/{uzivatel_id}/role")
def zmen_roli(uzivatel_id: int, vstup: RoleVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.zmen_roli_uzivatele(vstup.admin_id, uzivatel_id, vstup.role)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


# ---------- Admin: sprava vozidel a prehled faktur ----------

@app.post("/admin/vozidla")
def pridej_vozidlo(vstup: NoveVozidloVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.pridej_vozidlo(vstup.admin_id, vstup.nazev, vstup.nabiti, vstup.lat, vstup.lon)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.post("/admin/vozidla/{vozidlo_id}/odebrani")
def odeber_vozidlo(vozidlo_id: int, vstup: OdebraniVozidlaVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.odeber_vozidlo(vstup.admin_id, vozidlo_id)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.get("/vozidla/vsechna")
def vsechna_vozidla(uzivatel_id: int):
    # Pro admina (sprava flotily) a technika (prehled pro servis) - narozdil
    # od GET /vozidla vraci vozidla ve vsech stavech, ne jen volna.
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.vsechna_vozidla(uzivatel_id)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])

    return [
        {
            "id": vozidlo["id"],
            "nazev": vozidlo["nazev"],
            "stav": vozidlo["stav"],
            "nabiti": vozidlo["nabiti"],
            "lat": vozidlo["lat"],
            "lon": vozidlo["lon"],
            # Jmeno uzivatele s aktivni rezervaci/jizdou na vozidle (jinak
            # None) - pro admina, aby videl kdo ma co v ruce (issue #17).
            "aktivni_uzivatel": vozidlo["aktivni_uzivatel_jmeno"],
        }
        for vozidlo in vysledek["vozidla"]
    ]


@app.get("/admin/faktury")
def vsechny_faktury(admin_id: int, vozidlo_id: int | None = None, uzivatel_id: int | None = None):
    # vozidlo_id/uzivatel_id jsou volitelne filtry pro prehled admina.
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.vsechny_faktury(admin_id, vozidlo_id, uzivatel_id)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])

    return [
        {
            "faktura_id": faktura["id"],
            "jizda_id": faktura["jizda_id"],
            "uzivatel_id": faktura["uzivatel_id"],
            "uzivatel_jmeno": faktura["uzivatel_jmeno"],
            "vozidlo_id": faktura["vozidlo_id"],
            "vozidlo_nazev": faktura["vozidlo_nazev"],
            "ujeto_km": faktura["ujeto_km"],
            "castka": faktura["castka"],
        }
        for faktura in vysledek["faktury"]
    ]


# ---------- Technik: servis vozidla ----------

@app.post("/vozidla/{vozidlo_id}/udrzba")
def oznac_udrzbu(vozidlo_id: int, vstup: OznaceniUdrzbyVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.oznac_vozidlo_pro_udrzbu(vstup.technik_id, vozidlo_id)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek


@app.post("/vozidla/{vozidlo_id}/ukonceni-servisu")
def ukonci_servis(vozidlo_id: int, vstup: UkonceniServisuVstup):
    sluzba = ziskej_sluzbu()
    vysledek = sluzba.ukonci_servis(vstup.technik_id, vozidlo_id, vstup.nabiti)
    sluzba.spojeni.close()
    if vysledek["ok"] == False:
        raise HTTPException(status_code=400, detail=vysledek["zprava"])
    return vysledek
