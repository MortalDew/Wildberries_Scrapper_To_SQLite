# Wildberries Categories & Subjects Scraper

Collects all categories (with levels) from the Wildberries main menu and, for leaf categories, fetches all subject variations via the filters API. Subjects are appended as level-99 entries in the same categories dataset. Saves results to SQLite with per-top-level categories tables.

## Quick start (local)

Requirements: Python 3.11+

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Optional env overrides
$env:WB_MENU_URL="https://static-basket-01.wb.ru/vol0/data/main-menu-ru-ru-v3.json"
$env:DB_PATH="wb_categories.sqlite3"
$env:TIMEOUT_SECONDS="55"
$env:CONCURRENCY="16"

python -m src.main
```

Output database path is shown at the end (default `wb_categories.sqlite3`).

## Docker

Build and run:

```bash
docker compose -f docker-compose-app.yml up --build
```

The SQLite DB will be at `./data/wb_categories.sqlite3` on the host.

## Schema

For each top-level category (e.g., `Одежда`), one table is created with normalized names:
- `<cat>_categories`: id, name, level

Subjects are the same but level - 99, as a symbol of the fact, that there 
are no more levels after them
