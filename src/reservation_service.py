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
MIN_NABITI_PROCENT = 20                # K4: vozidlo pod touto urovni nelze rezervovat
PLATNOST_REZERVACE_MINUT_VYCHOZI = 30  # K1: vychozi platnost rezervace, meni jen admin
KLIC_PLATNOST_REZERVACE = "platnost_rezervace_minut"

# K3: technik smi rezervovat vozidlo stejne jako bezny uzivatel, ale jde
# o testovaci jizdu, ktera se nefakturuje. Ucel se urci podle role uzivatele
# v okamziku vytvoreni rezervace a od te chvile uz je nezavisly na roli
# (pozdejsi zmena role uzivatele fakturaci existujicich jizd neovlivni).
ROLE_TECHNIK = "technik"
UCEL_BEZNA = "bezna"
UCEL_TESTOVACI = "testovaci"

# Admin akce (spravu uzivatelu, vozidel a prehled faktur) - viz issue #5.
ROLE_ADMIN = "admin"
ROLE_UZIVATEL = "uzivatel"
PLATNE_ROLE = {ROLE_UZIVATEL, ROLE_ADMIN, ROLE_TECHNIK}

# Spotreba baterie za kazdy ujety kilometr (v procentech nabiti).
SPOTREBA_NABITI_PROCENT_NA_KM = 0.3


class RezervacniSluzba:
    # Sluzba drzi spojeni s databazi. Diky tomu se da pri testech
    # pouzit databaze v pameti.

    def __init__(self, spojeni):
        self.spojeni = spojeni

    # ---------- Zobrazeni dostupnych vozidel ----------

    def zobraz_dostupna_vozidla(self):
        # Nejdriv uklidime prosle rezervace, aby se jejich vozidla ukazala
        # jako volna (K1), a az pak nacteme volna vozidla pro mapovou sluzbu.
        self.over_a_vyprsele_rezervace()
        vozidla = database.ziskej_dostupna_vozidla(self.spojeni)
        maps.zobraz_na_mape(vozidla)
        return vozidla

    # ---------- Nastaveni platnosti rezervace (K1) ----------

    def ziskej_platnost_rezervace_minut(self):
        # Vrati aktualne nastavenou platnost rezervace v minutach (int).
        hodnota = database.ziskej_nastaveni(self.spojeni, KLIC_PLATNOST_REZERVACE,
                                            PLATNOST_REZERVACE_MINUT_VYCHOZI)
        return int(hodnota)

    def nastav_platnost_rezervace(self, uzivatel_id, minuty):
        # Zmenu limitu smi provest jen administrator.
        uzivatel = database.ziskej_uzivatele(self.spojeni, uzivatel_id)
        if uzivatel is None:
            return {"ok": False, "zprava": "Uzivatel neexistuje."}

        if uzivatel["role"] != "admin":
            return {"ok": False, "zprava": "Pouze administrator muze menit platnost rezervace."}

        if minuty <= 0:
            return {"ok": False, "zprava": "Platnost rezervace musi byt kladne cislo."}

        database.uloz_nastaveni(self.spojeni, KLIC_PLATNOST_REZERVACE, minuty)
        return {"ok": True, "zprava": "Platnost rezervace byla zmenena."}

    # ---------- Uklizeni prosly rezervaci ----------

    def over_a_vyprsele_rezervace(self):
        # Projde aktivni rezervace a ty, kterym vyprsela platnost, automaticky
        # zrusi a uvolni jejich vozidlo (K1 / FR5).
        aktivni_rezervace = database.ziskej_aktivni_rezervace(self.spojeni)
        ted = datetime.now()

        for rezervace in aktivni_rezervace:
            platnost_do = datetime.fromisoformat(rezervace["platnost_do"])
            if ted > platnost_do:
                database.nastav_stav_rezervace(self.spojeni, rezervace["id"], "vyprsela")
                database.nastav_stav_vozidla(self.spojeni, rezervace["vozidlo_id"], "volne")
                notifications.posli(rezervace["uzivatel_id"],
                                    "Vase rezervace vyprsela a byla zrusena.")

    # ---------- Rezervace vozidla ----------

    def vytvor_rezervaci(self, uzivatel_id, vozidlo_id):
        # Overi vsechny podminky a vytvori rezervaci.
        # Vraci slovnik s vysledkem, aby ho slo pouzit v API i v konzoli.

        # Nejdriv uklidime prosle rezervace, aby se pripadne uvolnilo
        # vozidlo, o ktere ma uzivatel zajem (K1).
        self.over_a_vyprsele_rezervace()

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

        # Vypocet platnosti rezervace (K1) - limit je konfigurovatelny administratorem.
        platnost_minut = self.ziskej_platnost_rezervace_minut()
        platnost_do = datetime.now() + timedelta(minutes=platnost_minut)
        platnost_do_text = platnost_do.isoformat()

        # Ucel rezervace podle role (K3) - technikova jizda je testovaci.
        ucel = UCEL_TESTOVACI if uzivatel["role"] == ROLE_TECHNIK else UCEL_BEZNA

        # Ulozeni rezervace a zmena stavu vozidla.
        rezervace_id = database.uloz_rezervaci(self.spojeni, vozidlo_id,
                                               uzivatel_id, platnost_do_text, ucel)
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

        # Kontrola realneho dojezdu podle aktualniho nabiti - ujeta vzdalenost
        # nesmi vyzadovat vic energie, nez kolik jich vozidlo melo (bugfix,
        # oprava spotreby baterie z issue #11).
        vozidlo = database.ziskej_vozidlo(self.spojeni, jizda["vozidlo_id"])
        max_dojezd_km = vozidlo["nabiti"] / SPOTREBA_NABITI_PROCENT_NA_KM
        if ujeto_km > max_dojezd_km:
            return {"ok": False, "zprava":
                    f"Ujeta vzdalenost presahuje dojezd vozidla podle aktualniho "
                    f"nabiti (max. {max_dojezd_km:.0f} km)."}

        # Ukonceni jizdy v databazi.
        database.ukonci_jizdu_v_databazi(self.spojeni, jizda_id, ujeto_km)

        # Ujeta vzdalenost snizuje nabiti vozidla (baterie se vybiji bez
        # ohledu na to, jestli se jizda fakturuje - feature request #11).
        nove_nabiti = max(0, round(vozidlo["nabiti"] - ujeto_km * SPOTREBA_NABITI_PROCENT_NA_KM))
        database.nastav_nabiti_vozidla(self.spojeni, jizda["vozidlo_id"], nove_nabiti)

        # Rezervace je dokoncena. Pokud vozidlo po jizde kleslo pod minimalni
        # nabiti pro rezervaci (K4), automaticky se posle do servisu - dal uz
        # je na technikovi, aby servis ukoncil (ukonci_servis).
        rezervace = database.ziskej_rezervaci(self.spojeni, jizda["rezervace_id"])
        database.nastav_stav_rezervace(self.spojeni, jizda["rezervace_id"], "dokoncena")
        novy_stav_vozidla = "udrzba" if nove_nabiti < MIN_NABITI_PROCENT else "volne"
        database.nastav_stav_vozidla(self.spojeni, jizda["vozidlo_id"], novy_stav_vozidla)

        # K3: testovaci jizda (technik) se nefakturuje - o fakturaci rozhoduje
        # ucel ulozeny na rezervaci, ne aktualni role uzivatele.
        if rezervace["ucel"] == UCEL_TESTOVACI:
            faktura_id = None
            notifications.posli(jizda["uzivatel_id"], "Testovaci jizda byla ukoncena.")
        else:
            # Volani fakturacni komponenty - vytvori fakturu.
            faktura_id = billing.vytvor_fakturu(self.spojeni, jizda_id,
                                                jizda["uzivatel_id"], ujeto_km)
            notifications.posli(jizda["uzivatel_id"], "Vase jizda byla ukoncena a vyuctovana.")

        return {"ok": True, "zprava": "Jizda ukoncena.", "faktura_id": faktura_id}

    # ---------- Historie jizd ----------

    def historie_jizd(self, uzivatel_id):
        jizdy = database.ziskej_historii_jizd(self.spojeni, uzivatel_id)
        return jizdy

    # ---------- Admin: sprava uzivatelu ----------
    # Autorizace je stejna jako u K1 (nastav_platnost_rezervace) - server si
    # podle poslaneho *_id dohleda uzivatele v DB a overi roli, zadne
    # heslo/token navic (viz otevrena otazka v issue #2/#3).

    def _ma_roli(self, uzivatel_id, ocekavana_role):
        uzivatel = database.ziskej_uzivatele(self.spojeni, uzivatel_id)
        return uzivatel is not None and uzivatel["role"] == ocekavana_role

    def vytvor_uzivatele(self, admin_id, jmeno, role):
        if not self._ma_roli(admin_id, ROLE_ADMIN):
            return {"ok": False, "zprava": "Pouze administrator muze vytvaret uzivatele."}

        if not jmeno or not jmeno.strip():
            return {"ok": False, "zprava": "Jmeno nesmi byt prazdne."}

        if role not in PLATNE_ROLE:
            return {"ok": False, "zprava": "Neplatna role."}

        novy_id = database.vytvor_uzivatele(self.spojeni, jmeno.strip(), role)
        return {"ok": True, "zprava": "Uzivatel vytvoren.", "uzivatel_id": novy_id}

    def nastav_zablokovani_uzivatele(self, admin_id, cilovy_uzivatel_id, zablokovan):
        if not self._ma_roli(admin_id, ROLE_ADMIN):
            return {"ok": False, "zprava": "Pouze administrator muze (od)blokovat uzivatele."}

        cilovy = database.ziskej_uzivatele(self.spojeni, cilovy_uzivatel_id)
        if cilovy is None:
            return {"ok": False, "zprava": "Uzivatel neexistuje."}

        database.nastav_zablokovani_uzivatele(self.spojeni, cilovy_uzivatel_id, zablokovan)
        zprava = "Uzivatel byl zablokovan." if zablokovan else "Uzivatel byl odblokovan."
        return {"ok": True, "zprava": zprava}

    def zmen_roli_uzivatele(self, admin_id, cilovy_uzivatel_id, nova_role):
        if not self._ma_roli(admin_id, ROLE_ADMIN):
            return {"ok": False, "zprava": "Pouze administrator muze menit role."}

        if nova_role not in PLATNE_ROLE:
            return {"ok": False, "zprava": "Neplatna role."}

        cilovy = database.ziskej_uzivatele(self.spojeni, cilovy_uzivatel_id)
        if cilovy is None:
            return {"ok": False, "zprava": "Uzivatel neexistuje."}

        database.nastav_roli_uzivatele(self.spojeni, cilovy_uzivatel_id, nova_role)
        return {"ok": True, "zprava": "Role byla zmenena."}

    # ---------- Admin: sprava vozidel a prehled faktur ----------

    def pridej_vozidlo(self, admin_id, nazev, nabiti, lat, lon):
        if not self._ma_roli(admin_id, ROLE_ADMIN):
            return {"ok": False, "zprava": "Pouze administrator muze pridavat vozidla."}

        if not nazev or not nazev.strip():
            return {"ok": False, "zprava": "Nazev vozidla nesmi byt prazdny."}

        if not (0 <= nabiti <= 100):
            return {"ok": False, "zprava": "Nabiti musi byt mezi 0 a 100."}

        vozidlo_id = database.pridej_vozidlo(self.spojeni, nazev.strip(), nabiti, lat, lon)
        return {"ok": True, "zprava": "Vozidlo pridano do floty.", "vozidlo_id": vozidlo_id}

    def odeber_vozidlo(self, admin_id, vozidlo_id):
        if not self._ma_roli(admin_id, ROLE_ADMIN):
            return {"ok": False, "zprava": "Pouze administrator muze odebirat vozidla."}

        vozidlo = database.ziskej_vozidlo(self.spojeni, vozidlo_id)
        if vozidlo is None:
            return {"ok": False, "zprava": "Vozidlo neexistuje."}

        # Vozidlo s aktivni rezervaci/jizdou nelze odebrat (viz issue #5).
        if vozidlo["stav"] not in ("volne", "udrzba"):
            return {"ok": False, "zprava": "Vozidlo ma aktivni rezervaci nebo jizdu, nelze ho odebrat."}

        database.odeber_vozidlo(self.spojeni, vozidlo_id)
        return {"ok": True, "zprava": "Vozidlo bylo odebrano z floty."}

    def vsechna_vozidla(self, uzivatel_id):
        # Pouziva admin (sprava flotily) i technik (prehled pro servis).
        if not (self._ma_roli(uzivatel_id, ROLE_ADMIN) or self._ma_roli(uzivatel_id, ROLE_TECHNIK)):
            return {"ok": False, "zprava": "Nemate opravneni videt vsechna vozidla."}

        return {"ok": True, "vozidla": database.ziskej_vsechna_vozidla(self.spojeni)}

    def vsechny_faktury(self, admin_id, vozidlo_id=None, uzivatel_id=None):
        if not self._ma_roli(admin_id, ROLE_ADMIN):
            return {"ok": False, "zprava": "Pouze administrator muze videt vsechny faktury."}

        faktury = database.ziskej_vsechny_faktury(self.spojeni, vozidlo_id, uzivatel_id)
        return {"ok": True, "faktury": faktury}

    # ---------- Technik: servis vozidla ----------

    def oznac_vozidlo_pro_udrzbu(self, technik_id, vozidlo_id):
        if not self._ma_roli(technik_id, ROLE_TECHNIK):
            return {"ok": False, "zprava": "Pouze technik muze oznacit vozidlo do servisu."}

        vozidlo = database.ziskej_vozidlo(self.spojeni, vozidlo_id)
        if vozidlo is None:
            return {"ok": False, "zprava": "Vozidlo neexistuje."}

        # Prave rezervovane/pouzivane vozidlo nelze poslat do servisu (FR12).
        if vozidlo["stav"] != "volne":
            return {"ok": False, "zprava": "Vozidlo neni volne, nelze ho dat do servisu."}

        database.nastav_stav_vozidla(self.spojeni, vozidlo_id, "udrzba")
        return {"ok": True, "zprava": "Vozidlo bylo oznaceno do servisu."}

    def ukonci_servis(self, technik_id, vozidlo_id, nabiti):
        if not self._ma_roli(technik_id, ROLE_TECHNIK):
            return {"ok": False, "zprava": "Pouze technik muze ukoncit servis."}

        vozidlo = database.ziskej_vozidlo(self.spojeni, vozidlo_id)
        if vozidlo is None:
            return {"ok": False, "zprava": "Vozidlo neexistuje."}

        if vozidlo["stav"] != "udrzba":
            return {"ok": False, "zprava": "Vozidlo neni v servisu."}

        if not (0 <= nabiti <= 100):
            return {"ok": False, "zprava": "Nabiti musi byt mezi 0 a 100."}

        database.nastav_nabiti_vozidla(self.spojeni, vozidlo_id, nabiti)

        # Diagram 1.3.7: pri nedostatecnem nabiti zustava vozidlo v servisu.
        if nabiti < MIN_NABITI_PROCENT:
            return {"ok": True, "zprava": "Nabiti je stale nedostatecne, vozidlo zustava v servisu."}

        database.nastav_stav_vozidla(self.spojeni, vozidlo_id, "volne")
        return {"ok": True, "zprava": "Servis byl ukoncen, vozidlo je znovu volne."}
