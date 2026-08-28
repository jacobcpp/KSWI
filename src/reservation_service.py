# reservation_service.py
# KLICOVA KOMPONENTA systemu - rezervacni sluzba.
# Obsahuje business logiku: rezervace vozidla, zruseni, zahajeni a ukonceni jizdy.
# Komunikuje s datovou vrstvou (database) a s ostatnimi komponentami
# (maps, billing, notifications).

from datetime import datetime, timedelta

import database
import maps
import billing
import notifications


# Konstanty vychazejici z analyzy konfliktnich pozadavku:
MIN_NABITI_PROCENT = 20        # K4: vozidlo pod touto urovni nelze rezervovat
PLATNOST_REZERVACE_MINUT = 15  # K1: jak dlouho rezervace drzi vozidlo

# Spotreba baterie za kazdy ujety kilometr (v procentech nabiti).
SPOTREBA_NABITI_PROCENT_NA_KM = 0.3


class RezervacniSluzba:
    # Sluzba drzi spojeni s databazi. Diky tomu se da pri testech
    # pouzit databaze v pameti.

    def __init__(self, spojeni):
        self.spojeni = spojeni

    # ---------- Zobrazeni dostupnych vozidel ----------

    def zobraz_dostupna_vozidla(self):
        # Nacte volna vozidla a preda je mapove sluzbe k zobrazeni.
        vozidla = database.ziskej_dostupna_vozidla(self.spojeni)
        maps.zobraz_na_mape(vozidla)
        return vozidla

    # ---------- Rezervace vozidla ----------

    def vytvor_rezervaci(self, uzivatel_id, vozidlo_id):
        # Overi vsechny podminky a vytvori rezervaci.
        # Vraci slovnik s vysledkem, aby ho slo pouzit v API i v konzoli.

        uzivatel = database.ziskej_uzivatele(self.spojeni, uzivatel_id)
        if uzivatel is None:
            return {"ok": False, "zprava": "Uzivatel neexistuje."}

        # Kontrola z konfliktu K3 a NFR3: zablokovany uzivatel nesmi rezervovat.
        if uzivatel["zablokovan"] == 1:
            return {"ok": False, "zprava": "Uzivatel je zablokovany."}

        vozidlo = database.ziskej_vozidlo(self.spojeni, vozidlo_id)
        if vozidlo is None:
            return {"ok": False, "zprava": "Vozidlo neexistuje."}

        # Vozidlo musi byt volne (FR14).
        if vozidlo["stav"] != "volne":
            return {"ok": False, "zprava": "Vozidlo neni volne."}

        # Kontrola z konfliktu K4: dostatecne nabiti.
        if vozidlo["nabiti"] < MIN_NABITI_PROCENT:
            return {"ok": False, "zprava": "Vozidlo ma prilis nizke nabiti."}

        # Overeni polohy pres mapovou sluzbu.
        maps.over_dostupnost(vozidlo)

        # Vypocet platnosti rezervace (K1).
        platnost_do = datetime.now() + timedelta(minutes=PLATNOST_REZERVACE_MINUT)
        platnost_do_text = platnost_do.isoformat()

        # Ulozeni rezervace a zmena stavu vozidla.
        rezervace_id = database.uloz_rezervaci(self.spojeni, vozidlo_id,
                                               uzivatel_id, platnost_do_text)
        database.nastav_stav_vozidla(self.spojeni, vozidlo_id, "rezervovano")

        # Notifikace uzivateli.
        notifications.posli(uzivatel_id, "Vase rezervace vozidla byla vytvorena.")

        return {"ok": True, "zprava": "Rezervace vytvorena.", "rezervace_id": rezervace_id}

    # ---------- Zruseni rezervace ----------

    def zrus_rezervaci(self, rezervace_id):
        rezervace = database.ziskej_rezervaci(self.spojeni, rezervace_id)
        if rezervace is None:
            return {"ok": False, "zprava": "Rezervace neexistuje."}

        if rezervace["stav"] != "aktivni":
            return {"ok": False, "zprava": "Rezervaci uz nelze zrusit."}

        # Zruseni rezervace a uvolneni vozidla.
        database.nastav_stav_rezervace(self.spojeni, rezervace_id, "zrusena")
        database.nastav_stav_vozidla(self.spojeni, rezervace["vozidlo_id"], "volne")

        notifications.posli(rezervace["uzivatel_id"], "Vase rezervace byla zrusena.")

        return {"ok": True, "zprava": "Rezervace zrusena."}

    # ---------- Zahajeni jizdy ----------

    def zahaj_jizdu(self, rezervace_id):
        rezervace = database.ziskej_rezervaci(self.spojeni, rezervace_id)
        if rezervace is None:
            return {"ok": False, "zprava": "Rezervace neexistuje."}

        if rezervace["stav"] != "aktivni":
            return {"ok": False, "zprava": "Rezervace neni aktivni."}

        # Kontrola z konfliktu K1: rezervace mohla vyprset.
        platnost_do = datetime.fromisoformat(rezervace["platnost_do"])
        if datetime.now() > platnost_do:
            # Rezervace vyprsela - uvolnime vozidlo.
            database.nastav_stav_rezervace(self.spojeni, rezervace_id, "vyprsela")
            database.nastav_stav_vozidla(self.spojeni, rezervace["vozidlo_id"], "volne")
            return {"ok": False, "zprava": "Rezervace vyprsela."}

        # Vytvoreni jizdy a zmena stavu vozidla.
        jizda_id = database.uloz_jizdu(self.spojeni, rezervace_id,
                                       rezervace["vozidlo_id"], rezervace["uzivatel_id"])
        database.nastav_stav_vozidla(self.spojeni, rezervace["vozidlo_id"], "v_jizde")

        notifications.posli(rezervace["uzivatel_id"], "Vase jizda byla zahajena.")

        return {"ok": True, "zprava": "Jizda zahajena.", "jizda_id": jizda_id}

    # ---------- Ukonceni jizdy ----------

    def ukonci_jizdu(self, jizda_id, ujeto_km):
        jizda = database.ziskej_jizdu(self.spojeni, jizda_id)
        if jizda is None:
            return {"ok": False, "zprava": "Jizda neexistuje."}

        if jizda["cas_konec"] is not None:
            return {"ok": False, "zprava": "Jizda uz byla ukoncena."}

        # Ukonceni jizdy v databazi.
        database.ukonci_jizdu_v_databazi(self.spojeni, jizda_id, ujeto_km)

        # Ujeta vzdalenost snizuje nabiti vozidla (baterie se vybiji bez
        # ohledu na to, jestli se jizda fakturuje - feature request #11).
        vozidlo = database.ziskej_vozidlo(self.spojeni, jizda["vozidlo_id"])
        nove_nabiti = max(0, round(vozidlo["nabiti"] - ujeto_km * SPOTREBA_NABITI_PROCENT_NA_KM))
        database.nastav_nabiti_vozidla(self.spojeni, jizda["vozidlo_id"], nove_nabiti)

        # Rezervace je dokoncena a vozidlo je zase volne.
        database.nastav_stav_rezervace(self.spojeni, jizda["rezervace_id"], "dokoncena")
        database.nastav_stav_vozidla(self.spojeni, jizda["vozidlo_id"], "volne")

        # Volani fakturacni komponenty - vytvori fakturu.
        faktura_id = billing.vytvor_fakturu(self.spojeni, jizda_id,
                                            jizda["uzivatel_id"], ujeto_km)

        notifications.posli(jizda["uzivatel_id"], "Vase jizda byla ukoncena a vyuctovana.")

        return {"ok": True, "zprava": "Jizda ukoncena.", "faktura_id": faktura_id}

    # ---------- Historie jizd ----------

    def historie_jizd(self, uzivatel_id):
        jizdy = database.ziskej_historii_jizd(self.spojeni, uzivatel_id)
        return jizdy
