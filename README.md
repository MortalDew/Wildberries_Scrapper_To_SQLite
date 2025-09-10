# Wildberries Categories & Subjects Scraper

Collects all categories (with levels) from the Wildberries main menu and, for leaf categories, fetches all subject variations via the filters API. Subjects are appended as level+1 entries in the same categories dataset. Saves results to SQLite with per-top-level categories tables.

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

python -m Wildberries_Scrapper.src.main
```

Output database path is shown at the end (default `wb_categories.sqlite3`).

## Docker

Build and run:

```bash
docker build -t wb-scraper .

# Mount a host directory to persist SQLite
mkdir data

docker run --rm -e TIMEOUT_SECONDS=55 -e CONCURRENCY=16 -v %cd%/data:/data wb-scraper
```

The SQLite DB will be at `./data/wb_categories.sqlite3` on the host.

## Schema

For each top-level category (e.g., `Одежда`), one table is created with normalized names:
- `<cat>_categories`: id, name, level, is_leaf, shard, query, url

Notes:
- Leaf categories get their `subjects` appended as new rows with `level = parent.level + 1`, `is_leaf = True`, and empty `shard/query/url`.
- This keeps a single hierarchy chain within one table per top-level.

## Notes
- Async HTTP via `aiohttp`.
- Global timeout for subject fetching can be controlled with `TIMEOUT_SECONDS`.
- Concurrency can be tuned via `CONCURRENCY`. 