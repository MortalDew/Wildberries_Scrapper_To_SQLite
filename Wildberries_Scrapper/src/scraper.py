import asyncio
from typing import Any, Dict, Generator, Iterable, List, Optional

import aiohttp


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


async def fetch_json(
    session: aiohttp.ClientSession, url: str, *, timeout: int = 20
) -> Any:
    async with session.get(url, timeout=timeout, headers=HEADERS) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


async def fetch_main_menu_categories(
    session: aiohttp.ClientSession, url: str
) -> List[Dict[str, Any]]:
    data = await fetch_json(session, url)
    return data  # list of top-level categories


def iter_all_categories_with_levels(
    menu: Iterable[Dict[str, Any]],
) -> Generator[Dict[str, Any], None, None]:
    stack: List[Dict[str, Any]] = []

    for top in menu:
        top_copy = {
            "id": top.get("id"),
            "name": top.get("name"),
            "shard": top.get("shard"),
            "query": top.get("query"),
            "url": top.get("url"),
            "level": 0,
            "is_leaf": not bool(top.get("childs")),
            "top_level_name": top.get("name"),
        }
        yield top_copy

        childs = top.get("childs") or []
        for child in childs:
            stack.append((child, 1, top.get("name")))

        while stack:
            node, level, root_name = stack.pop()
            item = {
                "id": node.get("id"),
                "name": node.get("name"),
                "shard": node.get("shard"),
                "query": node.get("query"),
                "url": node.get("url"),
                "level": level,
                "is_leaf": not bool(node.get("childs")),
                "top_level_name": root_name,
            }
            yield item

            for sub in node.get("childs") or []:
                stack.append((sub, level + 1, root_name))


async def fetch_subjects_for_leaf(
    session: aiohttp.ClientSession, category: Dict[str, Any]
) -> List[Dict[str, Any]]:
    shard = category.get("shard")
    query = category.get("query")
    if not shard or not query:
        return []

    url = f"https://catalog.wb.ru/catalog/{shard}/v4/filters?appType=1&{query}&curr=rub&dest=-8144334&spp=30"

    data = await fetch_json(session, url)

    filters = (data or {}).get("data", {}).get("filters", [])
    for f in filters:
        if f.get("key") == "xsubject":
            items = f.get("items") or []
            return [{"id": i.get("id"), "name": i.get("name")} for i in items]
    return []
