# maps.py
# Mock mapove sluzby.
# Ve skutecnem systemu by volala externi API (napr. Google Maps / Mapy.cz).
# Tady jen vytiskne vozidla a vzdy potvrdi dostupnost.


def zobraz_na_mape(vozidla):
    # Vytiskne dostupna vozidla, jako by se zobrazila na mape.
    print("[MAPA] Zobrazuji dostupna vozidla na mape:")
    for vozidlo in vozidla:
        print("   -", vozidlo["nazev"], "na pozici", vozidlo["lat"], vozidlo["lon"],
              "(nabiti", str(vozidlo["nabiti"]) + " %)")


def over_dostupnost(vozidlo):
    # Overi, ze vozidlo je na mape dosazitelne. Mock vzdy vrati True.
    print("[MAPA] Overuji polohu vozidla", vozidlo["nazev"])
    return True
