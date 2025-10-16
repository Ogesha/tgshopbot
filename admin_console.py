import asyncio, typer
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import load_config
from app.db import init_engine
from app.models import Base, User, ChatLog
from app.repositories import list_users
from app.dynamic_products import list_existing_category_tables

app = typer.Typer(help="Админ-панель (консоль)")

@app.command("init-db")
def init_db():
    cfg = load_config()
    engine, _Session = init_engine(cfg.database_url)
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
    asyncio.run(_run())
    typer.echo("OK")

@app.command("users")
def users(limit: int = 50):
    cfg = load_config()
    engine, Session = init_engine(cfg.database_url)
    async def _run():
        async with Session() as s:
            arr = await list_users(s, limit=limit)
            for u in arr:
                print(f"id={u.tg_id} username=@{u.username or '-'} name={u.display_name or '-'} subscribed={u.subscribed}")
        await engine.dispose()
    asyncio.run(_run())

@app.command("chats")
def chats(limit: int = 50):
    cfg = load_config()
    engine, Session = init_engine(cfg.database_url)
    async def _run():
        async with Session() as s:
            res = await s.execute(select(ChatLog).order_by(ChatLog.created_at.desc()).limit(limit))
            for r in res.scalars().all():
                print(f"[{r.created_at}] {r.tg_id} {r.direction}: {r.text}")
        await engine.dispose()
    asyncio.run(_run())

@app.command("categories")
def categories():
    cfg = load_config()
    engine, Session = init_engine(cfg.database_url)
    async def _run():
        async with Session() as s:
            tabs = await list_existing_category_tables(s)
            if not tabs:
                print("Категорий нет.")
            else:
                for t in sorted(tabs):
                    print(t)
        await engine.dispose()
    asyncio.run(_run())

@app.command("broadcast")
def broadcast(message: str):
    cfg = load_config()
    engine, Session = init_engine(cfg.database_url)
    bot = Bot(cfg.bot_token, parse_mode="HTML")
    async def _run():
        sent = failed = 0
        async with Session() as s:
            res = await s.execute(select(User))
            users = list(res.scalars().all())
        for u in users:
            try:
                await bot.send_message(u.tg_id, message)
                sent += 1
            except Exception:
                failed += 1
        await bot.session.close()
        await engine.dispose()
        print(f"Отправлено: {sent}, ошибок: {failed}")
    asyncio.run(_run())

@app.command("scrape-now")
def scrape_now():
    from app.scheduler import _daily_scrape_full_replace
    cfg = load_config()
    asyncio.run(_daily_scrape_full_replace(cfg))
    typer.echo("Готово.")

if __name__ == "__main__":
    app()
