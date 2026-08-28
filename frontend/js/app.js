// app.js
// Hlavni obrazovka po prihlaseni: seznam vozidel -> rezervace -> jizda -> historie.
// Aktivni rezervace/jizda uzivatele se drzi v localStorage (viz state.js),
// protoze API nema endpoint na dotaz "moje aktualne aktivni rezervace/jizda".

const uzivatel = nactiPrihlasenehoUzivatele();
if (!uzivatel) {
    window.location.href = "index.html";
}

const boxChyba = document.getElementById("chyba");
const boxZprava = document.getElementById("zprava");
const kartaVozidla = document.getElementById("kartaVozidla");
const kartaRezervace = document.getElementById("kartaRezervace");
const kartaJizda = document.getElementById("kartaJizda");
const seznamVozidel = document.getElementById("seznamVozidel");
const popisRezervace = document.getElementById("popisRezervace");
const popisJizdy = document.getElementById("popisJizdy");
const tabulkaHistorieTelo = document.querySelector("#tabulkaHistorie tbody");
const historiePrazdna = document.getElementById("historiePrazdna");
const kartaTechnik = document.getElementById("kartaTechnik");
const kartaAdmin = document.getElementById("kartaAdmin");

function nazevRole(role) {
    if (role === "admin") return "admin";
    if (role === "technik") return "technik";
    return "zákazník";
}

document.getElementById("jmenoUzivatele").textContent = uzivatel.jmeno;
document.getElementById("znackaRole").textContent = nazevRole(uzivatel.role);

if (uzivatel.role === "technik") {
    kartaTechnik.classList.remove("skryto");
}
if (uzivatel.role === "admin") {
    kartaAdmin.classList.remove("skryto");
}

document.getElementById("tlacitkoOdhlasit").addEventListener("click", () => {
    odhlasit();
    window.location.href = "index.html";
});

function zobrazChybu(zprava) {
    boxChyba.textContent = zprava;
    boxChyba.classList.remove("skryto");
}

function skryjChybu() {
    boxChyba.classList.add("skryto");
}

function zobrazZpravu(text) {
    boxZprava.textContent = text;
    boxZprava.classList.remove("skryto");
}

function skryjZpravu() {
    boxZprava.classList.add("skryto");
}

async function obnovObrazovku() {
    const stav = nactiStav(uzivatel.id);

    if (stav.jizdaId) {
        kartaVozidla.classList.add("skryto");
        kartaRezervace.classList.add("skryto");
        kartaJizda.classList.remove("skryto");
        popisJizdy.textContent = `Jízda č. ${stav.jizdaId} (vozidlo č. ${stav.vozidloId}) probíhá.`;
    } else if (stav.rezervaceId) {
        kartaVozidla.classList.add("skryto");
        kartaJizda.classList.add("skryto");
        kartaRezervace.classList.remove("skryto");
        popisRezervace.textContent = `Rezervace č. ${stav.rezervaceId} na vozidlo č. ${stav.vozidloId}.`;
    } else {
        kartaRezervace.classList.add("skryto");
        kartaJizda.classList.add("skryto");
        kartaVozidla.classList.remove("skryto");
        await nactiVozidla();
    }

    await nactiHistorii();

    if (uzivatel.role === "technik") {
        await nactiServisniPrehled();
    }
    if (uzivatel.role === "admin") {
        await Promise.all([nactiUzivateleAdmin(), nactiFlotiluAdmin(), nactiVsechnyFakturyAdmin()]);
    }
}

async function nactiVozidla() {
    try {
        const vozidla = await Api.vozidla();
        seznamVozidel.innerHTML = "";
        if (vozidla.length === 0) {
            seznamVozidel.innerHTML = '<p class="poznamka">Momentálně není k dispozici žádné volné vozidlo.</p>';
            return;
        }
        for (const vozidlo of vozidla) {
            const radek = document.createElement("div");
            radek.className = "vozidlo";
            radek.innerHTML = `
                <span>${vozidlo.nazev} - nabito ${vozidlo.nabiti}&nbsp;%</span>
            `;
            const tlacitko = document.createElement("button");
            tlacitko.textContent = "Rezervovat";
            tlacitko.addEventListener("click", () => rezervovatVozidlo(vozidlo.id));
            radek.appendChild(tlacitko);
            seznamVozidel.appendChild(radek);
        }
    } catch (chyba) {
        zobrazChybu("Nepodařilo se načíst vozidla: " + chyba.message);
    }
}

async function rezervovatVozidlo(vozidloId) {
    skryjChybu();
    skryjZpravu();
    try {
        const vysledek = await Api.vytvorRezervaci(uzivatel.id, vozidloId);
        ulozStav(uzivatel.id, { rezervaceId: vysledek.rezervace_id, vozidloId, jizdaId: null });
        await obnovObrazovku();
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
}

document.getElementById("tlacitkoZahajitJizdu").addEventListener("click", async () => {
    skryjChybu();
    skryjZpravu();
    const stav = nactiStav(uzivatel.id);
    try {
        const vysledek = await Api.zahajJizdu(stav.rezervaceId);
        ulozStav(uzivatel.id, { ...stav, jizdaId: vysledek.jizda_id });
        await obnovObrazovku();
    } catch (chyba) {
        zobrazChybu(chyba.message);
        // Rezervace mohla mezitim vyprset - vratime se na seznam vozidel.
        vycistiStav(uzivatel.id);
        await obnovObrazovku();
    }
});

document.getElementById("tlacitkoZrusitRezervaci").addEventListener("click", async () => {
    skryjChybu();
    skryjZpravu();
    const stav = nactiStav(uzivatel.id);
    try {
        await Api.zrusRezervaci(stav.rezervaceId);
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
    vycistiStav(uzivatel.id);
    await obnovObrazovku();
});

document.getElementById("tlacitkoUkoncitJizdu").addEventListener("click", async () => {
    skryjChybu();
    skryjZpravu();
    const stav = nactiStav(uzivatel.id);
    const ujetoKm = parseFloat(document.getElementById("ujetoKm").value) || 0;
    try {
        const vysledek = await Api.ukonciJizdu(stav.jizdaId, ujetoKm);
        vycistiStav(uzivatel.id);
        zobrazZpravu(
            vysledek.faktura_id === null
                ? "Testovací jízda ukončena, bez fakturace."
                : `Jízda ukončena, vystavena faktura č. ${vysledek.faktura_id}.`
        );
        await obnovObrazovku();
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
});

async function nactiHistorii() {
    try {
        const historie = await Api.historie(uzivatel.id);
        tabulkaHistorieTelo.innerHTML = "";
        historiePrazdna.classList.toggle("skryto", historie.length > 0);
        for (const jizda of historie) {
            const radek = document.createElement("tr");
            radek.innerHTML = `
                <td>${jizda.jizda_id}</td>
                <td>${jizda.vozidlo_id}</td>
                <td>${jizda.ujeto_km ?? "-"}</td>
                <td>${jizda.cas_start}</td>
                <td>${jizda.cas_konec ?? "probíhá"}</td>
                <td>${jizda.ucel === "testovaci" ? "testovací" : "běžná"}</td>
            `;
            tabulkaHistorieTelo.appendChild(radek);
        }
    } catch (chyba) {
        zobrazChybu("Nepodařilo se načíst historii jízd: " + chyba.message);
    }
}

// ---------- Technik: servis vozidel ----------

async function nactiServisniPrehled() {
    const tabulka = document.querySelector("#tabulkaServis tbody");
    try {
        const vozidla = await Api.vsechnaVozidla(uzivatel.id);
        tabulka.innerHTML = "";
        for (const vozidlo of vozidla) {
            const radek = document.createElement("tr");
            radek.innerHTML = `
                <td>${vozidlo.nazev}</td>
                <td>${vozidlo.stav}</td>
                <td>${vozidlo.nabiti}&nbsp;%</td>
            `;
            const bunkaAkce = document.createElement("td");

            if (vozidlo.stav === "volne") {
                const tlacitko = document.createElement("button");
                tlacitko.textContent = "Dát do servisu";
                tlacitko.addEventListener("click", () => oznacitDoServisu(vozidlo.id));
                bunkaAkce.appendChild(tlacitko);
            } else if (vozidlo.stav === "udrzba") {
                const vstupNabiti = document.createElement("input");
                vstupNabiti.type = "number";
                vstupNabiti.min = "0";
                vstupNabiti.max = "100";
                vstupNabiti.value = vozidlo.nabiti;
                const tlacitko = document.createElement("button");
                tlacitko.textContent = "Ukončit servis";
                tlacitko.addEventListener("click", () =>
                    ukoncitServis(vozidlo.id, parseInt(vstupNabiti.value, 10) || 0));
                bunkaAkce.appendChild(vstupNabiti);
                bunkaAkce.appendChild(tlacitko);
            } else {
                bunkaAkce.textContent = "-";
            }

            radek.appendChild(bunkaAkce);
            tabulka.appendChild(radek);
        }
    } catch (chyba) {
        zobrazChybu("Nepodařilo se načíst přehled vozidel: " + chyba.message);
    }
}

async function oznacitDoServisu(vozidloId) {
    skryjChybu();
    skryjZpravu();
    try {
        await Api.oznacUdrzbu(uzivatel.id, vozidloId);
        await nactiServisniPrehled();
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
}

async function ukoncitServis(vozidloId, nabiti) {
    skryjChybu();
    skryjZpravu();
    try {
        const vysledek = await Api.ukonciServis(uzivatel.id, vozidloId, nabiti);
        zobrazZpravu(vysledek.zprava);
        await nactiServisniPrehled();
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
}

// ---------- Admin: sprava uzivatelu ----------

document.getElementById("tlacitkoVytvoritUzivatele").addEventListener("click", async () => {
    skryjChybu();
    skryjZpravu();
    const jmeno = document.getElementById("novyUzivatelJmeno").value.trim();
    const role = document.getElementById("novyUzivatelRole").value;
    try {
        await Api.vytvorUzivatele(uzivatel.id, jmeno, role);
        document.getElementById("novyUzivatelJmeno").value = "";
        zobrazZpravu("Uživatel byl vytvořen.");
        await nactiUzivateleAdmin();
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
});

async function nactiUzivateleAdmin() {
    const tabulka = document.querySelector("#tabulkaUzivatele tbody");
    try {
        const uzivatele = await Api.uzivatele();
        tabulka.innerHTML = "";
        for (const u of uzivatele) {
            const radek = document.createElement("tr");
            radek.innerHTML = `<td>${u.jmeno}</td>`;

            const bunkaRole = document.createElement("td");
            const vyberRole = document.createElement("select");
            for (const [hodnota, popisek] of [
                ["uzivatel", "zákazník"], ["technik", "technik"], ["admin", "admin"],
            ]) {
                const volba = document.createElement("option");
                volba.value = hodnota;
                volba.textContent = popisek;
                if (hodnota === u.role) volba.selected = true;
                vyberRole.appendChild(volba);
            }
            vyberRole.addEventListener("change", () => zmenitRoli(u.id, vyberRole.value));
            bunkaRole.appendChild(vyberRole);
            radek.appendChild(bunkaRole);

            const bunkaStav = document.createElement("td");
            bunkaStav.textContent = u.zablokovan ? "zablokován" : "aktivní";
            radek.appendChild(bunkaStav);

            const bunkaAkce = document.createElement("td");
            const tlacitko = document.createElement("button");
            tlacitko.className = "sekundarni";
            tlacitko.textContent = u.zablokovan ? "Odblokovat" : "Zablokovat";
            tlacitko.addEventListener("click", () => prepnoutZablokovani(u.id, !u.zablokovan));
            bunkaAkce.appendChild(tlacitko);
            radek.appendChild(bunkaAkce);

            tabulka.appendChild(radek);
        }
    } catch (chyba) {
        zobrazChybu("Nepodařilo se načíst uživatele: " + chyba.message);
    }
}

async function prepnoutZablokovani(uzivatelId, zablokovan) {
    skryjChybu();
    skryjZpravu();
    try {
        await Api.nastavZablokovani(uzivatel.id, uzivatelId, zablokovan);
        await nactiUzivateleAdmin();
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
}

async function zmenitRoli(uzivatelId, role) {
    skryjChybu();
    skryjZpravu();
    try {
        await Api.zmenRoli(uzivatel.id, uzivatelId, role);
        zobrazZpravu("Role byla změněna.");
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
    await nactiUzivateleAdmin();
}

// ---------- Admin: sprava vozidel ----------

document.getElementById("tlacitkoPridatVozidlo").addEventListener("click", async () => {
    skryjChybu();
    skryjZpravu();
    const nazev = document.getElementById("noveVozidloNazev").value.trim();
    const nabiti = parseInt(document.getElementById("noveVozidloNabiti").value, 10) || 0;
    const lat = parseFloat(document.getElementById("noveVozidloLat").value) || 0;
    const lon = parseFloat(document.getElementById("noveVozidloLon").value) || 0;
    try {
        await Api.pridejVozidlo(uzivatel.id, nazev, nabiti, lat, lon);
        document.getElementById("noveVozidloNazev").value = "";
        zobrazZpravu("Vozidlo bylo přidáno do floty.");
        await nactiFlotiluAdmin();
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
});

async function nactiFlotiluAdmin() {
    const tabulka = document.querySelector("#tabulkaFlotila tbody");
    try {
        const vozidla = await Api.vsechnaVozidla(uzivatel.id);
        tabulka.innerHTML = "";
        for (const vozidlo of vozidla) {
            const radek = document.createElement("tr");
            radek.innerHTML = `
                <td>${vozidlo.nazev}</td>
                <td>${vozidlo.stav}</td>
                <td>${vozidlo.nabiti}&nbsp;%</td>
            `;
            const bunkaAkce = document.createElement("td");
            const lzeOdebrat = vozidlo.stav === "volne" || vozidlo.stav === "udrzba";
            const tlacitko = document.createElement("button");
            tlacitko.className = "sekundarni";
            tlacitko.textContent = "Odebrat";
            tlacitko.disabled = !lzeOdebrat;
            tlacitko.title = lzeOdebrat ? "" : "Vozidlo má aktivní rezervaci nebo jízdu.";
            tlacitko.addEventListener("click", () => odebratVozidlo(vozidlo.id));
            bunkaAkce.appendChild(tlacitko);
            radek.appendChild(bunkaAkce);
            tabulka.appendChild(radek);
        }
    } catch (chyba) {
        zobrazChybu("Nepodařilo se načíst flotilu: " + chyba.message);
    }
}

async function odebratVozidlo(vozidloId) {
    skryjChybu();
    skryjZpravu();
    try {
        await Api.odeberVozidlo(uzivatel.id, vozidloId);
        await nactiFlotiluAdmin();
    } catch (chyba) {
        zobrazChybu(chyba.message);
    }
}

// ---------- Admin: prehled vsech faktur ----------

async function nactiVsechnyFakturyAdmin() {
    const tabulka = document.querySelector("#tabulkaVsechnyFaktury tbody");
    const prazdne = document.getElementById("fakturyPrazdne");
    try {
        const faktury = await Api.vsechnyFaktury(uzivatel.id);
        tabulka.innerHTML = "";
        prazdne.classList.toggle("skryto", faktury.length > 0);
        for (const faktura of faktury) {
            const radek = document.createElement("tr");
            radek.innerHTML = `
                <td>${faktura.faktura_id}</td>
                <td>${faktura.uzivatel_jmeno}</td>
                <td>${faktura.jizda_id}</td>
                <td>${faktura.castka}</td>
            `;
            tabulka.appendChild(radek);
        }
    } catch (chyba) {
        zobrazChybu("Nepodařilo se načíst faktury: " + chyba.message);
    }
}

obnovObrazovku();
