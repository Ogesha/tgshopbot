from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from .scraper import scrape_products_multi
from .categorizer import pick_category_name
from .dynamic_products import replace_all_categories_and_products
from .db import get_sessionmaker
from .config import AppConfig

def _parse_hhmm(s: str) -> tuple[int,int]:
    hh, mm = s.strip().split(":")
    return int(hh), int(mm)

def setup_scheduler(cfg: AppConfig, bot: Bot) -> AsyncIOScheduler:
    tz = ZoneInfo(cfg.tz)
    scheduler = AsyncIOScheduler(timezone=tz)

    hh, mm = _parse_hhmm(cfg.scrape.daily_time)
    scheduler.add_job(
        func=_daily_scrape_full_replace,
        trigger="cron",
        hour=hh, minute=mm,
        args=[cfg],
        id="daily_scrape_replace",
        replace_existing=True,
    )

    if cfg.broadcast.autosend_daily_time:
        bh, bm = _parse_hhmm(cfg.broadcast.autosend_daily_time)
        scheduler.add_job(
            func=_autosend_job,
            trigger="cron",
            hour=bh, minute=bm,
            args=[cfg, bot],
            id="daily_autosend",
            replace_existing=True,
        )

    return scheduler

async def _daily_scrape_full_replace(cfg: AppConfig):
    Session = get_sessionmaker()
    items = scrape_products_multi(cfg.scrape.urls, {
        "card": cfg.scrape.selectors.card,
        "title": cfg.scrape.selectors.title,
        "price": cfg.scrape.selectors.price,
        "link_from_title": cfg.scrape.selectors.link_from_title
    })

    categorized: dict[str, list[dict]] = {}
    for it in items:
        cat_name = pick_category_name(it["title"], cfg.categories) or "Прочее"
        categorized.setdefault(cat_name, []).append(it)

    async with Session() as s:  # type: AsyncSession
        await replace_all_categories_and_products(s, categorized)

async def _autosend_job(cfg: AppConfig, bot: Bot):
    from sqlalchemy import select
    from .models import User
    Session = get_sessionmaker()
    async with Session() as s:
        res = await s.execute(select(User).where(User.subscribed == True))
        users = list(res.scalars().all())
    text = "🔔 Каталог обновлён! Зайдите в бота и посмотрите категории."
    for u in users:
        try:
            await bot.send_message(u.tg_id, text)
        except Exception:
            pass
