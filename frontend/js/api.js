// api.js
// Tenka vrstva nad fetch() - kazda funkce odpovida jednomu endpointu REST API.
// Zadna business logika tu neni, jen prevod HTTP <-> JS objekty.

async function apiGet(cesta) {
    const odpoved = await fetch(window.API_BASE + cesta);
    const data = await odpoved.json().catch(() => ({}));
    if (!odpoved.ok) {
        throw new Error(data.detail || "Chyba pri komunikaci s API.");
    }
    return data;
}

async function apiPost(cesta, telo) {
    const odpoved = await fetch(window.API_BASE + cesta, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(telo || {}),
    });
    const data = await odpoved.json().catch(() => ({}));
    if (!odpoved.ok) {
        throw new Error(data.detail || "Chyba pri komunikaci s API.");
    }
    return data;
}

const Api = {
    uzivatele: () => apiGet("/uzivatele"),
    vozidla: () => apiGet("/vozidla"),
    vytvorRezervaci: (uzivatelId, vozidloId) =>
        apiPost("/rezervace", { uzivatel_id: uzivatelId, vozidlo_id: vozidloId }),
    zrusRezervaci: (rezervaceId) =>
        apiPost(`/rezervace/${rezervaceId}/zruseni`),
    zahajJizdu: (rezervaceId) =>
        apiPost("/jizdy", { rezervace_id: rezervaceId }),
    ukonciJizdu: (jizdaId, ujetoKm) =>
        apiPost(`/jizdy/${jizdaId}/ukonceni`, { ujeto_km: ujetoKm }),
    historie: (uzivatelId) => apiGet(`/uzivatele/${uzivatelId}/historie`),

    // ---------- Admin: sprava uzivatelu, vozidel, faktury ----------
    vytvorUzivatele: (adminId, jmeno, role) =>
        apiPost("/admin/uzivatele", { admin_id: adminId, jmeno, role }),
    nastavZablokovani: (adminId, uzivatelId, zablokovan) =>
        apiPost(`/admin/uzivatele/${uzivatelId}/zablokovani`, { admin_id: adminId, zablokovan }),
    zmenRoli: (adminId, uzivatelId, role) =>
        apiPost(`/admin/uzivatele/${uzivatelId}/role`, { admin_id: adminId, role }),
    pridejVozidlo: (adminId, nazev, nabiti, lat, lon) =>
        apiPost("/admin/vozidla", { admin_id: adminId, nazev, nabiti, lat, lon }),
    odeberVozidlo: (adminId, vozidloId) =>
        apiPost(`/admin/vozidla/${vozidloId}/odebrani`, { admin_id: adminId }),
    vsechnyFaktury: (adminId) => apiGet(`/admin/faktury?admin_id=${adminId}`),

    // ---------- Admin + technik: prehled cele floty ----------
    vsechnaVozidla: (uzivatelId) => apiGet(`/vozidla/vsechna?uzivatel_id=${uzivatelId}`),

    // ---------- Technik: servis vozidla ----------
    oznacUdrzbu: (technikId, vozidloId) =>
        apiPost(`/vozidla/${vozidloId}/udrzba`, { technik_id: technikId }),
    ukonciServis: (technikId, vozidloId, nabiti) =>
        apiPost(`/vozidla/${vozidloId}/ukonceni-servisu`, { technik_id: technikId, nabiti }),
};
