# database.py
# Datova vrstva - stara se o SQLite databazi.
# Vytvari tabulky a poskytuje jednoduche funkce pro cteni a zapis dat.
# Psano zamerne jednoduse (bez ORM, bez komprehenci).

import sqlite3
from datetime import datetime


# Vychozi soubor s databazi. Pro testy se pouziva ":memory:" (databaze v pameti).
VYCHOZI_SOUBOR = "carsharing.db"


def vytvor_spojeni(cesta=VYCHOZI_SOUBOR):
    # Vytvori spojeni s databazi.
    # row_factory zaridi, ze se k hodnotam da pristupovat podle nazvu sloupce.
    spojeni = sqlite3.connect(cesta)
    spojeni.row_factory = sqlite3.Row
    return spojeni


def vytvor_tabulky(spojeni):
    # Vytvori vsechny potrebne tabulky, pokud jeste neexistuji.
    kurzor = spojeni.cursor()

    kurzor.execute("""
        CREATE TABLE IF NOT EXISTS uzivatele (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jmeno TEXT NOT NULL,
            role TEXT NOT NULL,
            zablokovan INTEGER NOT NULL DEFAULT 0
        )
    """)

    kurzor.execute("""
        CREATE TABLE IF NOT EXISTS vozidla (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazev TEXT NOT NULL,
            stav TEXT NOT NULL,
            nabiti INTEGER NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    """)

    kurzor.execute("""
        CREATE TABLE IF NOT EXISTS rezervace (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vozidlo_id INTEGER NOT NULL,
            uzivatel_id INTEGER NOT NULL,
            stav TEXT NOT NULL,
            cas_vytvoreni TEXT NOT NULL,
            platnost_do TEXT NOT NULL,
            ucel TEXT NOT NULL DEFAULT 'bezna'
        )
    """)

    kurzor.execute("""
        CREATE TABLE IF NOT EXISTS jizdy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rezervace_id INTEGER NOT NULL,
            vozidlo_id INTEGER NOT NULL,
            uzivatel_id INTEGER NOT NULL,
            cas_start TEXT NOT NULL,
            cas_konec TEXT,
            ujeto_km REAL
        )
    """)

    kurzor.execute("""
        CREATE TABLE IF NOT EXISTS faktury (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jizda_id INTEGER NOT NULL,
            uzivatel_id INTEGER NOT NULL,
            castka REAL NOT NULL
        )
    """)

    # Nastaveni systemu (klic - hodnota). Pouziva se napr. pro K1 -
    # platnost rezervace, kterou smi menit jen admin.
    kurzor.execute("""
        CREATE TABLE IF NOT EXISTS nastaveni (
            klic TEXT PRIMARY KEY,
            hodnota TEXT NOT NULL
        )
    """)

    spojeni.commit()


def napln_ukazkova_data(spojeni):
    # Vlozi nekolik ukazkovych uzivatelu a vozidel, aby bylo co testovat.
    kurzor = spojeni.cursor()

    # Uzivatele: bezny uzivatel, admin, technik
    kurzor.execute("INSERT INTO uzivatele (jmeno, role, zablokovan) VALUES (?, ?, ?)",
                   ("Jan Novak", "uzivatel", 0))
    kurzor.execute("INSERT INTO uzivatele (jmeno, role, zablokovan) VALUES (?, ?, ?)",
                   ("Admin Adminovic", "admin", 0))
    kurzor.execute("INSERT INTO uzivatele (jmeno, role, zablokovan) VALUES (?, ?, ?)",
                   ("Petr Technik", "technik", 0))

    # Vozidla s ruznymi stavy a urovni nabiti
    kurzor.execute("INSERT INTO vozidla (nazev, stav, nabiti, lat, lon) VALUES (?, ?, ?, ?, ?)",
                   ("Auto A", "volne", 80, 50.08, 14.42))
    kurzor.execute("INSERT INTO vozidla (nazev, stav, nabiti, lat, lon) VALUES (?, ?, ?, ?, ?)",
                   ("Auto B", "volne", 15, 50.09, 14.43))
    kurzor.execute("INSERT INTO vozidla (nazev, stav, nabiti, lat, lon) VALUES (?, ?, ?, ?, ?)",
                   ("Auto C", "udrzba", 50, 50.07, 14.41))

    spojeni.commit()


# ---------- Funkce pro uzivatele ----------

def ziskej_uzivatele(spojeni, uzivatel_id):
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM uzivatele WHERE id = ?", (uzivatel_id,))
    return kurzor.fetchone()


def ziskej_vsechny_uzivatele(spojeni):
    # Pouziva se pro vyber uzivatele na prihlasovaci obrazovce frontendu.
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM uzivatele")
    return kurzor.fetchall()


# ---------- Funkce pro vozidla ----------

def ziskej_vozidlo(spojeni, vozidlo_id):
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM vozidla WHERE id = ?", (vozidlo_id,))
    return kurzor.fetchone()


def ziskej_dostupna_vozidla(spojeni):
    # Vrati seznam vozidel, ktera jsou volna.
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM vozidla WHERE stav = ?", ("volne",))
    return kurzor.fetchall()


def nastav_stav_vozidla(spojeni, vozidlo_id, novy_stav):
    kurzor = spojeni.cursor()
    kurzor.execute("UPDATE vozidla SET stav = ? WHERE id = ?", (novy_stav, vozidlo_id))
    spojeni.commit()


def nastav_nabiti_vozidla(spojeni, vozidlo_id, nabiti):
    kurzor = spojeni.cursor()
    kurzor.execute("UPDATE vozidla SET nabiti = ? WHERE id = ?", (nabiti, vozidlo_id))
    spojeni.commit()


# ---------- Funkce pro rezervace ----------

def uloz_rezervaci(spojeni, vozidlo_id, uzivatel_id, platnost_do, ucel="bezna"):
    # ucel ("bezna"/"testovaci") se urcuje jednou pri vytvoreni rezervace
    # a zustava u ni ulozeny - viz konflikt K3 (testovaci jizda technika).
    kurzor = spojeni.cursor()
    cas = datetime.now().isoformat()
    kurzor.execute("""
        INSERT INTO rezervace (vozidlo_id, uzivatel_id, stav, cas_vytvoreni, platnost_do, ucel)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (vozidlo_id, uzivatel_id, "aktivni", cas, platnost_do, ucel))
    spojeni.commit()
    return kurzor.lastrowid


def ziskej_rezervaci(spojeni, rezervace_id):
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM rezervace WHERE id = ?", (rezervace_id,))
    return kurzor.fetchone()


def nastav_stav_rezervace(spojeni, rezervace_id, novy_stav):
    kurzor = spojeni.cursor()
    kurzor.execute("UPDATE rezervace SET stav = ? WHERE id = ?", (novy_stav, rezervace_id))
    spojeni.commit()


# ---------- Funkce pro jizdy ----------

def uloz_jizdu(spojeni, rezervace_id, vozidlo_id, uzivatel_id):
    kurzor = spojeni.cursor()
    cas = datetime.now().isoformat()
    kurzor.execute("""
        INSERT INTO jizdy (rezervace_id, vozidlo_id, uzivatel_id, cas_start, cas_konec, ujeto_km)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (rezervace_id, vozidlo_id, uzivatel_id, cas, None, None))
    spojeni.commit()
    return kurzor.lastrowid


def ziskej_jizdu(spojeni, jizda_id):
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM jizdy WHERE id = ?", (jizda_id,))
    return kurzor.fetchone()


def ukonci_jizdu_v_databazi(spojeni, jizda_id, ujeto_km):
    kurzor = spojeni.cursor()
    cas = datetime.now().isoformat()
    kurzor.execute("UPDATE jizdy SET cas_konec = ?, ujeto_km = ? WHERE id = ?",
                   (cas, ujeto_km, jizda_id))
    spojeni.commit()


def ziskej_historii_jizd(spojeni, uzivatel_id):
    # Vrati vsechny jizdy daneho uzivatele.
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM jizdy WHERE uzivatel_id = ?", (uzivatel_id,))
    return kurzor.fetchall()


# ---------- Funkce pro aktivni rezervace ----------

def ziskej_aktivni_rezervace(spojeni):
    # Vrati vsechny rezervace, ktere jeste nebyly zruseny/vyprsely/dokonceny.
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM rezervace WHERE stav = ?", ("aktivni",))
    return kurzor.fetchall()


# ---------- Funkce pro nastaveni ----------

def ziskej_nastaveni(spojeni, klic, vychozi):
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT hodnota FROM nastaveni WHERE klic = ?", (klic,))
    radek = kurzor.fetchone()
    if radek is None:
        return vychozi
    return radek["hodnota"]


def uloz_nastaveni(spojeni, klic, hodnota):
    kurzor = spojeni.cursor()
    kurzor.execute("""
        INSERT INTO nastaveni (klic, hodnota) VALUES (?, ?)
        ON CONFLICT(klic) DO UPDATE SET hodnota = excluded.hodnota
    """, (klic, str(hodnota)))
    spojeni.commit()


# ---------- Funkce pro faktury ----------

def uloz_fakturu(spojeni, jizda_id, uzivatel_id, castka):
    kurzor = spojeni.cursor()
    kurzor.execute("INSERT INTO faktury (jizda_id, uzivatel_id, castka) VALUES (?, ?, ?)",
                   (jizda_id, uzivatel_id, castka))
    spojeni.commit()
    return kurzor.lastrowid


def ziskej_faktury_uzivatele(spojeni, uzivatel_id):
    kurzor = spojeni.cursor()
    kurzor.execute("SELECT * FROM faktury WHERE uzivatel_id = ?", (uzivatel_id,))
    return kurzor.fetchall()
