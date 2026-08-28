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


def test_vychozi_platnost_rezervace_je_30_minut():
    # K1: vychozi limit je 30 minut, dokud ho admin nezmeni.
    sluzba = priprav_sluzbu()
    assert sluzba.ziskej_platnost_rezervace_minut() == 30


def test_admin_muze_zmenit_platnost_rezervace():
    # Uzivatel 2 je v ukazkovych datech admin.
    sluzba = priprav_sluzbu()
    vysledek = sluzba.nastav_platnost_rezervace(2, 45)

    assert vysledek["ok"] == True
    assert sluzba.ziskej_platnost_rezervace_minut() == 45


def test_bezny_uzivatel_nemuze_zmenit_platnost_rezervace():
    # Uzivatel 1 je bezny uzivatel, zmena mu musi byt odepnuta.
    sluzba = priprav_sluzbu()
    vysledek = sluzba.nastav_platnost_rezervace(1, 45)

    assert vysledek["ok"] == False
    assert sluzba.ziskej_platnost_rezervace_minut() == 30


def test_nova_rezervace_pouziva_zmeneny_limit():
    # Po zmene limitu administratorem se novy limit projevi v nove rezervaci.
    sluzba = priprav_sluzbu()
    sluzba.nastav_platnost_rezervace(2, 45)

    rezervace = sluzba.vytvor_rezervaci(1, 1)
    ulozena = database.ziskej_rezervaci(sluzba.spojeni, rezervace["rezervace_id"])

    ocekavana_platnost = datetime.now() + timedelta(minutes=45)
    skutecna_platnost = datetime.fromisoformat(ulozena["platnost_do"])
    # Porovnavame s tolerenci nekolika sekund kvuli behu testu.
    assert abs((skutecna_platnost - ocekavana_platnost).total_seconds()) < 5


def test_vyprsela_rezervace_uvolni_vozidlo_bez_zahajeni_jizdy():
    # K1: vozidlo se uvolni automaticky, i kdyz nikdo nezavola zahaj_jizdu
    # na konkretni rezervaci - staci, ze se sahne na dostupna vozidla.
    sluzba = priprav_sluzbu()
    rezervace = sluzba.vytvor_rezervaci(1, 1)
    rezervace_id = rezervace["rezervace_id"]

    minulost = (datetime.now() - timedelta(minutes=1)).isoformat()
    kurzor = sluzba.spojeni.cursor()
    kurzor.execute("UPDATE rezervace SET platnost_do = ? WHERE id = ?",
                   (minulost, rezervace_id))
    sluzba.spojeni.commit()

    vozidla = sluzba.zobraz_dostupna_vozidla()
    assert any(vozidlo["id"] == 1 for vozidlo in vozidla)

    vozidlo = database.ziskej_vozidlo(sluzba.spojeni, 1)
    assert vozidlo["stav"] == "volne"

    rezervace_po = database.ziskej_rezervaci(sluzba.spojeni, rezervace_id)
    assert rezervace_po["stav"] == "vyprsela"


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


def test_admin_muze_vytvorit_uzivatele():
    sluzba = priprav_sluzbu()
    vysledek = sluzba.vytvor_uzivatele(2, "Nova Novakova", "uzivatel")

    assert vysledek["ok"] == True
    novy = database.ziskej_uzivatele(sluzba.spojeni, vysledek["uzivatel_id"])
    assert novy["jmeno"] == "Nova Novakova"
    assert novy["role"] == "uzivatel"


def test_bezny_uzivatel_nemuze_vytvorit_uzivatele():
    sluzba = priprav_sluzbu()
    vysledek = sluzba.vytvor_uzivatele(1, "Falesny Admin", "admin")

    assert vysledek["ok"] == False


def test_admin_muze_zablokovat_a_odblokovat_uzivatele():
    sluzba = priprav_sluzbu()
    vysledek = sluzba.nastav_zablokovani_uzivatele(2, 1, True)
    assert vysledek["ok"] == True
    assert database.ziskej_uzivatele(sluzba.spojeni, 1)["zablokovan"] == 1

    vysledek = sluzba.nastav_zablokovani_uzivatele(2, 1, False)
    assert vysledek["ok"] == True
    assert database.ziskej_uzivatele(sluzba.spojeni, 1)["zablokovan"] == 0


def test_admin_muze_zmenit_roli_uzivatele():
    sluzba = priprav_sluzbu()
    vysledek = sluzba.zmen_roli_uzivatele(2, 1, "technik")

    assert vysledek["ok"] == True
    assert database.ziskej_uzivatele(sluzba.spojeni, 1)["role"] == "technik"


def test_admin_muze_pridat_a_odebrat_vozidlo():
    sluzba = priprav_sluzbu()
    vysledek = sluzba.pridej_vozidlo(2, "Auto D", 60, 50.1, 14.4)
    assert vysledek["ok"] == True

    vozidlo_id = vysledek["vozidlo_id"]
    assert database.ziskej_vozidlo(sluzba.spojeni, vozidlo_id)["stav"] == "volne"

    vysledek = sluzba.odeber_vozidlo(2, vozidlo_id)
    assert vysledek["ok"] == True
    assert database.ziskej_vozidlo(sluzba.spojeni, vozidlo_id) is None


def test_nelze_odebrat_vozidlo_s_aktivni_rezervaci():
    sluzba = priprav_sluzbu()
    sluzba.vytvor_rezervaci(1, 1)

    vysledek = sluzba.odeber_vozidlo(2, 1)
    assert vysledek["ok"] == False
    assert database.ziskej_vozidlo(sluzba.spojeni, 1) is not None


def test_admin_vidi_vsechny_faktury():
    sluzba = priprav_sluzbu()
    rezervace = sluzba.vytvor_rezervaci(1, 1)
    jizda = sluzba.zahaj_jizdu(rezervace["rezervace_id"])
    sluzba.ukonci_jizdu(jizda["jizda_id"], 10)

    vysledek = sluzba.vsechny_faktury(2)
    assert vysledek["ok"] == True
    assert len(vysledek["faktury"]) == 1
    faktura = vysledek["faktury"][0]
    assert faktura["uzivatel_jmeno"] == "Jan Novak"
    assert faktura["vozidlo_nazev"] == "Auto A"
    assert faktura["ujeto_km"] == 10


def test_admin_muze_filtrovat_faktury_podle_vozidla_a_uzivatele():
    sluzba = priprav_sluzbu()

    rezervace1 = sluzba.vytvor_rezervaci(1, 1)
    jizda1 = sluzba.zahaj_jizdu(rezervace1["rezervace_id"])
    sluzba.ukonci_jizdu(jizda1["jizda_id"], 10)

    # Vozidlo 1 je zase volne, druhou jizdu na nem udela admin (uzivatel 2).
    rezervace2 = sluzba.vytvor_rezervaci(2, 1)
    jizda2 = sluzba.zahaj_jizdu(rezervace2["rezervace_id"])
    sluzba.ukonci_jizdu(jizda2["jizda_id"], 20)

    vsechny = sluzba.vsechny_faktury(2)
    assert len(vsechny["faktury"]) == 2

    podle_vozidla = sluzba.vsechny_faktury(2, vozidlo_id=1)
    assert len(podle_vozidla["faktury"]) == 2

    podle_uzivatele = sluzba.vsechny_faktury(2, uzivatel_id=1)
    assert len(podle_uzivatele["faktury"]) == 1
    assert podle_uzivatele["faktury"][0]["uzivatel_jmeno"] == "Jan Novak"


def test_technik_muze_oznacit_a_ukoncit_servis():
    sluzba = priprav_sluzbu()
    vysledek = sluzba.oznac_vozidlo_pro_udrzbu(3, 1)
    assert vysledek["ok"] == True
    assert database.ziskej_vozidlo(sluzba.spojeni, 1)["stav"] == "udrzba"

    vysledek = sluzba.ukonci_servis(3, 1, 90)
    assert vysledek["ok"] == True
    vozidlo = database.ziskej_vozidlo(sluzba.spojeni, 1)
    assert vozidlo["stav"] == "volne"
    assert vozidlo["nabiti"] == 90


def test_ukonceni_servisu_s_nizkym_nabitim_necha_vozidlo_v_udrzbe():
    sluzba = priprav_sluzbu()
    sluzba.oznac_vozidlo_pro_udrzbu(3, 1)

    vysledek = sluzba.ukonci_servis(3, 1, 10)
    assert vysledek["ok"] == True
    assert database.ziskej_vozidlo(sluzba.spojeni, 1)["stav"] == "udrzba"


def test_bezny_uzivatel_nemuze_oznacit_vozidlo_do_servisu():
    sluzba = priprav_sluzbu()
    vysledek = sluzba.oznac_vozidlo_pro_udrzbu(1, 1)

    assert vysledek["ok"] == False
    assert database.ziskej_vozidlo(sluzba.spojeni, 1)["stav"] == "volne"


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

    # Seznam uzivatelu pro prihlasovaci obrazovku frontendu (issue #3).
    odpoved_uzivatele = klient.get("/uzivatele")
    assert odpoved_uzivatele.status_code == 200
    jmena = [u["jmeno"] for u in odpoved_uzivatele.json()]
    assert "Jan Novak" in jmena

    # Uklid po testu.
    if os.path.exists(main.DB_SOUBOR):
        os.remove(main.DB_SOUBOR)
