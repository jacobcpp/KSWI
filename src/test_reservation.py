# test_reservation.py
# Testy pro rezervacni komponentu.
# Obsahuje jednotkove testy (testuji primo rezervacni sluzbu) i integracni
# testy (testuji cely tok a REST API pres TestClient).
# Spusteni ve slozce src:  python3 -m pytest test_reservation.py -v

import os
from datetime import datetime, timedelta

import database
from reservation_service import RezervacniSluzba


def priprav_sluzbu():
    # Pomocna funkce: vytvori cistou databazi v pameti s ukazkovymi daty
    # a vrati rezervacni sluzbu. Kazdy test tak zacina se stejnym stavem.
    spojeni = database.vytvor_spojeni(":memory:")
    database.vytvor_tabulky(spojeni)
    database.napln_ukazkova_data(spojeni)
    return RezervacniSluzba(spojeni)


# ---------- Jednotkove testy rezervacni sluzby ----------

def test_rezervace_uspesna():
    # Bezny uzivatel (1) rezervuje volne a nabite vozidlo (Auto A = 1).
    sluzba = priprav_sluzbu()
    vysledek = sluzba.vytvor_rezervaci(1, 1)

    assert vysledek["ok"] == True
    # Vozidlo ma nyni stav "rezervovano".
    vozidlo = database.ziskej_vozidlo(sluzba.spojeni, 1)
    assert vozidlo["stav"] == "rezervovano"


def test_rezervace_malo_nabiteho_vozidla():
    # Auto B (id 2) ma nabiti 15 %, coz je pod limitem 20 % (konflikt K4).
    sluzba = priprav_sluzbu()
    vysledek = sluzba.vytvor_rezervaci(1, 2)

    assert vysledek["ok"] == False
    assert "nabiti" in vysledek["zprava"]


def test_rezervace_neexistujiciho_vozidla():
    # Vozidlo s id 999 neexistuje.
    sluzba = priprav_sluzbu()
    vysledek = sluzba.vytvor_rezervaci(1, 999)

    assert vysledek["ok"] == False


def test_rezervace_zablokovaneho_uzivatele():
    # Uzivatele 1 nejdriv zablokujeme a pak zkusime rezervaci.
    sluzba = priprav_sluzbu()
    kurzor = sluzba.spojeni.cursor()
    kurzor.execute("UPDATE uzivatele SET zablokovan = 1 WHERE id = 1")
    sluzba.spojeni.commit()

    vysledek = sluzba.vytvor_rezervaci(1, 1)
    assert vysledek["ok"] == False


def test_zruseni_rezervace_uvolni_vozidlo():
    # Po zruseni rezervace je vozidlo zase volne.
    sluzba = priprav_sluzbu()
    rezervace = sluzba.vytvor_rezervaci(1, 1)
    rezervace_id = rezervace["rezervace_id"]

    vysledek = sluzba.zrus_rezervaci(rezervace_id)
    assert vysledek["ok"] == True

    vozidlo = database.ziskej_vozidlo(sluzba.spojeni, 1)
    assert vozidlo["stav"] == "volne"


def test_zahajeni_jizdy_po_vyprseni_rezervace():
    # Kontrola konfliktu K1: kdyz rezervace vyprsi, jizdu nelze zahajit.
    sluzba = priprav_sluzbu()
    rezervace = sluzba.vytvor_rezervaci(1, 1)
    rezervace_id = rezervace["rezervace_id"]

    # Rucne nastavime platnost rezervace do minulosti.
    minulost = (datetime.now() - timedelta(minutes=1)).isoformat()
    kurzor = sluzba.spojeni.cursor()
    kurzor.execute("UPDATE rezervace SET platnost_do = ? WHERE id = ?",
                   (minulost, rezervace_id))
    sluzba.spojeni.commit()

    vysledek = sluzba.zahaj_jizdu(rezervace_id)
    assert vysledek["ok"] == False
    assert "vyprsela" in vysledek["zprava"]


def test_rezervace_technika_je_testovaci():
    # Konflikt K3: technik (uzivatel 3) rezervuje stejne jako bezny uzivatel,
    # ale rezervace se ulozi s ucelem "testovaci".
    sluzba = priprav_sluzbu()
    vysledek = sluzba.vytvor_rezervaci(3, 1)

    assert vysledek["ok"] == True
    rezervace = database.ziskej_rezervaci(sluzba.spojeni, vysledek["rezervace_id"])
    assert rezervace["ucel"] == "testovaci"


def test_rezervace_bezneho_uzivatele_je_bezna():
    # Bezny uzivatel (1) ma ucel rezervace "bezna".
    sluzba = priprav_sluzbu()
    vysledek = sluzba.vytvor_rezervaci(1, 1)

    rezervace = database.ziskej_rezervaci(sluzba.spojeni, vysledek["rezervace_id"])
    assert rezervace["ucel"] == "bezna"


def test_testovaci_jizda_technika_negeneruje_fakturu():
    # Konflikt K3: po ukonceni testovaci jizdy technika nevznikne faktura,
    # ale jizda zustane v historii stejne jako u beznych uzivatelu.
    sluzba = priprav_sluzbu()

    rezervace = sluzba.vytvor_rezervaci(3, 1)
    jizda = sluzba.zahaj_jizdu(rezervace["rezervace_id"])
    konec = sluzba.ukonci_jizdu(jizda["jizda_id"], 10)

    assert konec["ok"] == True
    assert konec["faktura_id"] is None

    faktury = database.ziskej_faktury_uzivatele(sluzba.spojeni, 3)
    assert len(faktury) == 0

    historie = sluzba.historie_jizd(3)
    assert len(historie) == 1
    assert historie[0]["id"] == jizda["jizda_id"]


# ---------- Integracni testy ----------

def test_cely_tok_rezervace_az_faktura():
    # Integracni test: rezervace -> jizda -> ukonceni -> faktura.
    sluzba = priprav_sluzbu()

    rezervace = sluzba.vytvor_rezervaci(1, 1)
    assert rezervace["ok"] == True

    jizda = sluzba.zahaj_jizdu(rezervace["rezervace_id"])
    assert jizda["ok"] == True

    konec = sluzba.ukonci_jizdu(jizda["jizda_id"], 10)
    assert konec["ok"] == True

    # Faktura vznikla a ma spravnou castku (10 km * 5 Kc = 50 Kc).
    faktury = database.ziskej_faktury_uzivatele(sluzba.spojeni, 1)
    assert len(faktury) == 1
    assert faktury[0]["castka"] == 50.0

    # Po ukonceni jizdy je vozidlo zase volne.
    vozidlo = database.ziskej_vozidlo(sluzba.spojeni, 1)
    assert vozidlo["stav"] == "volne"


def test_api_rezervace_pres_endpoint():
    # Integracni test REST API pres TestClient.
    from fastapi.testclient import TestClient
    import main

    # Zacneme s cistou databazi, aby byl test opakovatelny.
    if os.path.exists(main.DB_SOUBOR):
        os.remove(main.DB_SOUBOR)
    main.priprav_databazi()

    klient = TestClient(main.app)

    # Seznam vozidel vrati kod 200 a neprazdny seznam.
    odpoved_vozidla = klient.get("/vozidla")
    assert odpoved_vozidla.status_code == 200
    assert len(odpoved_vozidla.json()) > 0

    # Vytvoreni rezervace pres API.
    odpoved_rezervace = klient.post("/rezervace",
                                    json={"uzivatel_id": 1, "vozidlo_id": 1})
    assert odpoved_rezervace.status_code == 200
    assert odpoved_rezervace.json()["ok"] == True

    # Uklid po testu.
    if os.path.exists(main.DB_SOUBOR):
        os.remove(main.DB_SOUBOR)
