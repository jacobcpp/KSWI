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

function nazevRole(role) {
    if (role === "admin") return "admin";
    if (role === "technik") return "technik";
    return "zákazník";
}

document.getElementById("jmenoUzivatele").textContent = uzivatel.jmeno;
document.getElementById("znackaRole").textContent = nazevRole(uzivatel.role);

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
            `;
            tabulkaHistorieTelo.appendChild(radek);
        }
    } catch (chyba) {
        zobrazChybu("Nepodařilo se načíst historii jízd: " + chyba.message);
    }
}

obnovObrazovku();
