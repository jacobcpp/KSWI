// config.js
// Adresa backend REST API. V Dockeru se tento soubor pri startu kontejneru
// prepise podle promenne prostredi API_BASE_URL (viz docker-entrypoint.sh).
// Bez Dockeru (staticky server nad slozkou frontend/) se pouzije tato vychozi hodnota.
window.API_BASE = "http://127.0.0.1:8000";
