import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List


class SQLiteStorage:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            # Pragmas for faster bulk writes while keeping reasonable durability
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute(
                "PRAGMA cache_size=-20000"
            )  # ~20k pages in memory (~20MB if 1KB pages)
            conn.execute("PRAGMA foreign_keys=OFF")
            yield conn
        finally:
            conn.commit()
            conn.close()

    def _normalize_table_name(self, name: str) -> str:
        safe = "".join(
            ch if ch.isalnum() or ch == "_" else "_" for ch in (name or "wb").lower()
        )
        safe = "_".join(filter(None, safe.split("_")))
        if not safe:
            safe = "wb"
        return f"cat_{safe}"

    def _ensure_tables(self, conn: sqlite3.Connection, top_level_name: str) -> str:
        table = self._normalize_table_name(top_level_name)
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table}_categories (
                id INTEGER,
                name TEXT,
                level INTEGER
            )
            """
        )
        return table

    def save_categories(self, categories: Iterable[Dict[str, Any]]) -> None:
        by_top: Dict[str, List[Dict[str, Any]]] = {}
        for cat in categories:
            top = cat.get("top_level_name") or "wb"
            by_top.setdefault(top, []).append(cat)

        with self.connect() as conn:
            for top_name, items in by_top.items():
                table = self._ensure_tables(conn, top_name)
                conn.execute("BEGIN")
                conn.executemany(
                    f"INSERT INTO {table}_categories (id, name, level) VALUES (?, ?, ?)",
                    [(it.get("id"), it.get("name"), it.get("level")) for it in items],
                )
                conn.execute("COMMIT")
