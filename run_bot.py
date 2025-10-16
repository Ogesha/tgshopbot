import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import load_config
from app.db import init_engine
from app.models import Base
from app.repositories import admins_bootstrap
from app.scheduler import setup_scheduler
from bot.handlers import router as bot_router

async def main():
    cfg = load_config()

    engine, Session = init_engine(cfg.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as s:
        await admins_bootstrap(s, cfg.admin_ids)

    bot = Bot(cfg.bot_token, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(bot_router)

    @dp.update.outer_middleware()
    async def db_session_mw(handler, event: Update, data: dict):
        async with Session() as s:
            data["session"] = s  # AsyncSession для хендлеров
            return await handler(event, data)

    scheduler = setup_scheduler(cfg, bot)
    scheduler.start()

    print("Bot started. Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
