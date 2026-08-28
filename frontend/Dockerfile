# Dockerfile pro frontend - staticke soubory servirovane pres nginx.
# js/config.js se pri startu kontejneru prepise podle promenne
# prostredi API_BASE_URL (viz docker-entrypoint.sh a docker-compose.yml).

FROM nginx:alpine

COPY index.html app.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

COPY docker-entrypoint.sh /docker-entrypoint.d/50-config.sh
RUN chmod +x /docker-entrypoint.d/50-config.sh

EXPOSE 80
