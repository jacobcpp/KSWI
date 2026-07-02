# console_demo.py
# Konzolova ukazka, ktera projde cely tok:
# zobrazeni vozidel -> rezervace -> zahajeni jizdy -> ukonceni jizdy -> historie.
# Diky vypisum mocku (MAPA, FAKTURACE, NOTIFIKACE) je videt, jak spolu
# komponenty komunikuji.

import database
from reservation_service import RezervacniSluzba


def vytiskni_oddelovac(nadpis):
    print("")
    print("=" * 55)
    print(nadpis)
    print("=" * 55)


def spust_ukazku():
    # Pouzijeme databazi v pameti, aby se ukazka dala spustit opakovane.
    spojeni = database.vytvor_spojeni(":memory:")
    database.vytvor_tabulky(spojeni)
    database.napln_ukazkova_data(spojeni)

    sluzba = RezervacniSluzba(spojeni)

    # ID 1 = bezny uzivatel (Jan Novak), vozidlo 1 = Auto A (volne, nabiti 80)
    uzivatel_id = 1
    vozidlo_id = 1

    vytiskni_oddelovac("1) Zobrazeni dostupnych vozidel")
    sluzba.zobraz_dostupna_vozidla()

    vytiskni_oddelovac("2) Rezervace vozidla Auto A")
    vysledek = sluzba.vytvor_rezervaci(uzivatel_id, vozidlo_id)
    print("Vysledek:", vysledek["zprava"])
    rezervace_id = vysledek["rezervace_id"]

    vytiskni_oddelovac("3) Pokus o rezervaci malo nabiteho vozidla (Auto B)")
    vysledek_b = sluzba.vytvor_rezervaci(uzivatel_id, 2)
    print("Vysledek:", vysledek_b["zprava"])

    vytiskni_oddelovac("4) Zahajeni jizdy")
    vysledek_jizda = sluzba.zahaj_jizdu(rezervace_id)
    print("Vysledek:", vysledek_jizda["zprava"])
    jizda_id = vysledek_jizda["jizda_id"]

    vytiskni_oddelovac("5) Ukonceni jizdy (ujeto 12 km)")
    vysledek_konec = sluzba.ukonci_jizdu(jizda_id, 12)
    print("Vysledek:", vysledek_konec["zprava"])

    vytiskni_oddelovac("6) Historie jizd uzivatele")
    jizdy = sluzba.historie_jizd(uzivatel_id)
    for jizda in jizdy:
        print("   Jizda c.", jizda["id"],
              "- vozidlo", jizda["vozidlo_id"],
              "- ujeto", jizda["ujeto_km"], "km")

    spojeni.close()


if __name__ == "__main__":
    spust_ukazku()
