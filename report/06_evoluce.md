# 6. Evoluce softwaru

V další iteraci vývoje bude potřeba systém rozšířit. Níže jsou tři navržené změny
a jejich dopad na architekturu a na implementovanou rezervační komponentu.

Klíčové zjištění: díky zvolené **vrstvené architektuře** a tomu, že ostatní části
(fakturace, mapa, notifikace) jsou volané přes jasně dané rozhraní, se u většiny
změn **rezervační služba téměř nemění** – vyměňují se hlavně mock komponenty za
reálné implementace.

## 6.1 Změna 1 – Nový typ uživatele: firemní správce

**Popis:** Přibude role „firemní správce", který spravuje více zaměstnaneckých
účtů pod jednou firmou a vidí souhrnnou fakturaci za všechny své zaměstnance.

**Dopad na architekturu:**
- Do modelu uživatelů přibude vazba „firma" a nová role.
- Fakturace musí umět seskupit jízdy více uživatelů pod jednu firemní fakturu.

**Dopad na kód:**
- V `database.py` přibude tabulka `firmy` a sloupec `firma_id` u uživatelů.
- V rezervační službě se rozšíří kontrola oprávnění (nová role), ale samotná
  logika rezervace zůstává stejná.
- Nejvíc práce je ve fakturační komponentě (souhrnná faktura), ne v jádru.

**Náročnost:** střední.

## 6.2 Změna 2 – Integrace s reálnou platební bránou

**Popis:** Mock fakturace (`billing.py`) se nahradí napojením na reálnou platební
bránu (např. Stripe, GoPay), která provede skutečnou platbu.

**Dopad na architekturu:**
- Fakturace se stane skutečnou externí integrací – přibude síťová komunikace,
  potvrzování plateb a ošetření chyb (platba se nemusí povést).
- Vhodné je zpracovat platbu asynchronně a stav platby ukládat.

**Dopad na kód:**
- Změní se pouze `billing.py` – funkce `vytvor_fakturu` zůstane navenek stejná
  (stejné parametry), jen uvnitř zavolá platební bránu.
- **Rezervační služba se nemění vůbec**, protože fakturaci volá přes stejné
  rozhraní. To je hlavní výhoda oddělení komponent.

**Náročnost:** střední (hlavně kvůli ošetření chyb a bezpečnosti plateb).

## 6.3 Změna 3 – Integrace s reálnou mapovou službou

**Popis:** Mock mapy (`maps.py`) se nahradí reálnou mapovou službou (např.
Mapy.cz nebo Google Maps API), včetně vyhledání nejbližšího vozidla podle polohy
uživatele.

**Dopad na architekturu:**
- Mapová služba se stane externí integrací (NFR – riziko výpadku, nutnost
  ošetřit nedostupnost, případně cache).
- Přibude funkce „najdi nejbližší vozidlo", která potřebuje polohu uživatele.

**Dopad na kód:**
- Změní se `maps.py` – funkce `zobraz_na_mape` a `over_dostupnost` získají reálnou
  implementaci. Přibude nová funkce pro nejbližší vozidlo.
- V rezervační službě lze přidat nepovinný krok „doporuč nejbližší vozidlo", ale
  stávající metody se nemusí měnit.

**Náročnost:** střední.

## 6.4 Shrnutí dopadů

| Změna | Hlavní zásah | Rezervační služba | Náročnost |
|-------|--------------|-------------------|-----------|
| Firemní správce | databáze + fakturace | malá úprava (oprávnění) | střední |
| Platební brána | billing.py | beze změny | střední |
| Reálná mapa | maps.py | volitelné rozšíření | střední |

Žádná ze změn nevyžaduje přepsání jádra systému. To potvrzuje, že vrstvená
architektura s oddělenými komponentami byla pro tento systém dobrá volba a
usnadňuje budoucí rozvoj. Při výrazném růstu (mnoho měst, vysoká zátěž) by dalším
krokem mohl být postupný přechod vybraných komponent (fakturace, mapa) na
samostatné **mikroslužby** – architektura je na to připravena.
