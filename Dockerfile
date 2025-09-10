FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WB_MENU_URL=https://static-basket-01.wb.ru/vol0/data/main-menu-ru-ru-v3.json \
    DB_PATH=/data/wb_categories.sqlite3 \
    TIMEOUT_SECONDS=55 \
    CONCURRENCY=16

WORKDIR /app

# Install system deps if needed (none for sqlite3 stdlib)

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Create data directory
RUN mkdir -p /data
VOLUME ["/data"]

CMD ["python", "-m", "src.main"] 