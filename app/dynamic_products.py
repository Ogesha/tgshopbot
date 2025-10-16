import re
from typing import Dict, List
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import CursorResult

PRODUCTS_PREFIX = "products_"

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "misc"

def table_name_for_category(cat_name: str) -> str:
    return f"{PRODUCTS_PREFIX}{slugify(cat_name)}"

async def list_existing_category_tables(session: AsyncSession) -> List[str]:
    dialect = session.bind.dialect.name
    if "mysql" in dialect:
        q = text("SHOW TABLES")
        res: CursorResult = await session.execute(q)
        rows = [r[0] for r in res.fetchall() if r[0].startswith(PRODUCTS_PREFIX)]
        return rows
    else:
        q = text("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename LIKE :prefix
        """)
        res = await session.execute(q, {"prefix": f"{PRODUCTS_PREFIX}%"})
        return [r[0] for r in res.fetchall()]

async def drop_table(session: AsyncSession, table_name: str):
    await session.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
    await session.commit()

async def ensure_category_table(session: AsyncSession, table_name: str):
    await session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            price VARCHAR(64) NOT NULL,
            url TEXT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    await session.execute(text(f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_title" ON "{table_name}"(title)'))
    await session.commit()

async def truncate_table(session: AsyncSession, table_name: str):
    await session.execute(text(f'TRUNCATE TABLE "{table_name}"'))
    await session.commit()

async def bulk_insert_products(session: AsyncSession, table_name: str, items: List[Dict]):
    if not items:
        return
    values = [
        {
            "title": it.get("title") or "",
            "price": it.get("price") or "",
            "url": it.get("url"),
            "updated_at": datetime.utcnow()
        } for it in items
    ]
    await session.execute(
        text(f"""
            INSERT INTO "{table_name}" (title, price, url, updated_at)
            VALUES (:title, :price, :url, :updated_at)
        """),
        values
    )
    await session.commit()

async def replace_all_categories_and_products(session: AsyncSession, categorized_items: Dict[str, List[Dict]]):
    existing = set(await list_existing_category_tables(session))
    new_tables = {table_name_for_category(cat) for cat in categorized_items.keys()}

    for t in (existing - new_tables):
        await drop_table(session, t)

    for cat_name, items in categorized_items.items():
        tname = table_name_for_category(cat_name)
        await ensure_category_table(session, tname)
        await truncate_table(session, tname)
        await bulk_insert_products(session, tname, items)
