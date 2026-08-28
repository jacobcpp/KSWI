// state.js
// Ulozeni "prihlaseneho" uzivatele a jeho aktivni rezervace/jizdy v localStorage.
// Zadne skutecne overeni identity neprobiha (viz otevrena otazka K3 v reportu) -
// uzivatel se jen vybere ze seznamu, API pak dostava jeho uzivatel_id primo v requestu.

const KLIC_UZIVATEL = "carsharing_uzivatel";

function ulozPrihlaseniUzivatele(uzivatel) {
    localStorage.setItem(KLIC_UZIVATEL, JSON.stringify(uzivatel));
}

function nactiPrihlasenehoUzivatele() {
    const data = localStorage.getItem(KLIC_UZIVATEL);
    return data ? JSON.parse(data) : null;
}

function odhlasit() {
    localStorage.removeItem(KLIC_UZIVATEL);
}

function klicStavu(uzivatelId) {
    return `carsharing_stav_${uzivatelId}`;
}

function ulozStav(uzivatelId, stav) {
    localStorage.setItem(klicStavu(uzivatelId), JSON.stringify(stav));
}

function nactiStav(uzivatelId) {
    const data = localStorage.getItem(klicStavu(uzivatelId));
    return data ? JSON.parse(data) : { rezervaceId: null, jizdaId: null };
}

function vycistiStav(uzivatelId) {
    localStorage.removeItem(klicStavu(uzivatelId));
}
