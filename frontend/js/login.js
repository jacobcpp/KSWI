// login.js
// Naplni vyberovy seznam uzivateli z API a po potvrzeni ulozi zvoleneho
// uzivatele do localStorage (viz state.js) a presmeruje na app.html.

const selectUzivatel = document.getElementById("vyberUzivatele");
const tlacitkoPrihlasit = document.getElementById("tlacitkoPrihlasit");
const boxChyba = document.getElementById("chyba");

let nacteniUzivatele = [];

function zobrazChybu(zprava) {
    boxChyba.textContent = zprava;
    boxChyba.classList.remove("skryto");
}

function nazevRole(role) {
    if (role === "admin") return "admin";
    if (role === "technik") return "technik";
    return "zákazník";
}

async function nacti() {
    // Pokud uz je nekdo prihlasen, rovnou ho posleme do aplikace.
    if (nactiPrihlasenehoUzivatele()) {
        window.location.href = "app.html";
        return;
    }

    try {
        nacteniUzivatele = await Api.uzivatele();
    } catch (chyba) {
        zobrazChybu("Nepodařilo se načíst seznam uživatelů: " + chyba.message);
        return;
    }

    selectUzivatel.innerHTML = "";
    for (const uzivatel of nacteniUzivatele) {
        const volba = document.createElement("option");
        volba.value = uzivatel.id;
        volba.textContent = `${uzivatel.jmeno} (${nazevRole(uzivatel.role)})`
            + (uzivatel.zablokovan ? " - zablokován" : "");
        selectUzivatel.appendChild(volba);
    }
}

tlacitkoPrihlasit.addEventListener("click", () => {
    const uzivatel = nacteniUzivatele.find(u => String(u.id) === selectUzivatel.value);
    if (!uzivatel) {
        return;
    }
    ulozPrihlaseniUzivatele(uzivatel);
    window.location.href = "app.html";
});

nacti();
