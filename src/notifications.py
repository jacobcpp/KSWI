# notifications.py
# Mock notifikacni sluzby.
# Ve skutecnem systemu by posilala e-mail nebo push notifikaci.
# Tady jen vytiskne zpravu na standardni vystup.


def posli(uzivatel_id, zprava):
    print("[NOTIFIKACE] Uzivatel c.", uzivatel_id, "->", zprava)
