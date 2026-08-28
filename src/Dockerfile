# Dockerfile pro backend (REST API).
# Build se spousti z korene repozitare (potrebuje pristup k requirements.txt):
#   docker build -f src/Dockerfile -t carsharing-api .
# V praxi se pouziva pres docker-compose.yml v korene repozitare.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src
WORKDIR /app/src

# Databaze zije mimo /app/src, aby na ni sel pripojit Docker volume, aniz by
# to zastinilo kod pri rebuildu (issue #6). Bez volume mountu ma i tak
# rozumnou vychozi hodnotu.
RUN mkdir -p /app/data
ENV DB_CESTA=/app/data/carsharing_api.db

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
