// footer.js
// Zobrazi verzi frontendu (znama rovnou) a backendu (nactena pres API) ve
// footeru - pouziva se na obou strankach (login i app). Viz issue #21.

async function zobrazVerze() {
    const footer = document.getElementById("footerVerze");
    if (!footer) {
        return;
    }

    let backendVerze = "nedostupný";
    try {
        const odpoved = await Api.verze();
        backendVerze = odpoved.verze;
    } catch (chyba) {
        // Backend nemusi bezet - footer se pak zobrazi jen s verzi frontendu.
    }

    footer.textContent = `Frontend v${window.FRONTEND_VERZE} · Backend v${backendVerze}`;
}

zobrazVerze();
