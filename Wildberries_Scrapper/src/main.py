import asyncio
import json
import os
from typing import Any, Dict, List, Optional
import logging

from .scraper import (
    fetch_main_menu_categories,
    iter_all_categories_with_levels,
    fetch_subjects_for_leaf,
)
from .storage import SQLiteStorage

import aiohttp
from aiohttp import TCPConnector


DEFAULT_MENU_URL = "https://static-basket-01.wb.ru/vol0/data/main-menu-ru-ru-v3.json"

logger = logging.getLogger(__name__)


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    return value if value not in (None, "") else default


async def gather_subjects_for_leaves(
    session: aiohttp.ClientSession,
    categories: List[Dict[str, Any]],
    concurrency: int = 16,
) -> List[Dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)

    results: List[Dict[str, Any]] = []

    async def worker(cat: Dict[str, Any]) -> None:
        async with semaphore:
            try:
                subjects = await fetch_subjects_for_leaf(session, cat)
                for subject in subjects:
                    results.append(
                        {
                            "top_level": cat.get("top_level_name"),
                            "category_id": cat.get("id"),
                            "category_name": cat.get("name"),
                            "level": cat.get("level"),
                            "subject_id": subject.get("id"),
                            "subject_name": subject.get("name"),
                            "subject_level": cat.get("level", 0) + 1,
                        }
                    )
            except Exception as exc:
                # Swallow per-task errors to keep the run resilient
                logger.warning(
                    f"Failed to fetch subjects for {cat.get('name')} ({cat.get('id')}): {exc}"
                )

    tasks = [
        asyncio.create_task(worker(cat)) for cat in categories if cat.get("is_leaf")
    ]
    if tasks:
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.warning(
                "gather_subjects_for_leaves cancelled - returning partial results"
            )
            return results
    return results


async def main() -> None:
    # Configure logging
    log_level_name = (get_env("LOG_LEVEL", "INFO") or "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    menu_url = get_env("WB_MENU_URL", DEFAULT_MENU_URL) or DEFAULT_MENU_URL
    db_path = get_env("DB_PATH", os.path.join(os.getcwd(), "wb_categories.sqlite3"))
    timeout_s = float(
        get_env("TIMEOUT_SECONDS", "113")
    )  # keep under 1 minute total where possible
    concurrency = int(get_env("CONCURRENCY", "16"))
    tcp_limit = int(get_env("TCP_LIMIT", str(concurrency * 2)))
    tcp_limit_per_host = int(get_env("TCP_LIMIT_PER_HOST", str(concurrency)))
    total_timeout = aiohttp.ClientTimeout(total=None, sock_connect=20, sock_read=20)

    connector = TCPConnector(
        limit=tcp_limit, limit_per_host=tcp_limit_per_host, ttl_dns_cache=300
    )
    async with aiohttp.ClientSession(
        connector=connector, timeout=total_timeout
    ) as session:
        logger.info(f"Fetching main menu from: {menu_url}")
        menu = await fetch_main_menu_categories(session, menu_url)

        logger.info("Traversing categories...")
        all_cats = list(iter_all_categories_with_levels(menu))

        # Fetch subjects for leaves without global wait_for to preserve partial results
        logger.info("Fetching subjects for leaf categories asynchronously...")
        subjects = await gather_subjects_for_leaves(
            session, all_cats, concurrency=concurrency
        )

        # Transform subjects into category-like rows (level+1 under their parent) and append
        if subjects:
            subject_categories: List[Dict[str, Any]] = []
            for s in subjects:
                subject_categories.append(
                    {
                        "id": s.get("subject_id"),
                        "name": s.get("subject_name"),
                        "shard": None,
                        "query": None,
                        "url": None,
                        "level": 99,
                        "is_leaf": True,
                        "top_level_name": s.get("top_level"),
                    }
                )
            all_cats.extend(subject_categories)

    # Persist categories grouped by top-level
    storage = SQLiteStorage(db_path)
    storage.init_db()

    logger.info("Saving categories (including expanded subjects)...")
    storage.save_categories(all_cats)

    logger.info(f"Done. SQLite at: {db_path}")


if __name__ == "__main__":
    asyncio.run(main())
