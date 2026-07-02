# billing.py
# Mock fakturacni sluzby.
# Ve skutecnem systemu by to byla samostatna komponenta (napr. napojena na
# platebni branu). Tady jen spocita cenu, ulozi fakturu a vytiskne informaci.

import database


# Cena za ujety kilometr v Kc. Podle konfliktu K2 se uctuje jen jizda.
CENA_ZA_KM = 5.0


def vytvor_fakturu(spojeni, jizda_id, uzivatel_id, ujeto_km):
    # Spocita castku a ulozi fakturu do databaze.
    castka = ujeto_km * CENA_ZA_KM

    print("[FAKTURACE] Vytvarim fakturu za jizdu c.", jizda_id,
          "- ujeto", ujeto_km, "km, castka", castka, "Kc")

    faktura_id = database.uloz_fakturu(spojeni, jizda_id, uzivatel_id, castka)
    return faktura_id
