from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.repositories import (
    get_or_create_user, set_user_name, set_subscribed, log_message
)
from app.dynamic_products import list_existing_category_tables, PRODUCTS_PREFIX, table_name_for_category
from .keyboards import main_kb

router = Router()

class NameState(StatesGroup):
    waiting = State()

class CatState(StatesGroup):
    waiting = State()

def pretty_cat_from_table(t: str) -> str:
    return t[len(PRODUCTS_PREFIX):].replace("_", " ").title()

@router.message(CommandStart())
async def start(message: Message, state: FSMContext, session: AsyncSession):
    u = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    await log_message(session, message.from_user.id, "in", message.text or "")
    if not u.display_name:
        await message.answer("Привет! Напишите, как к вам обращаться.")
        await state.set_state(NameState.waiting)
        return
    await message.answer(f"Привет, {u.display_name}! ✨", reply_markup=main_kb(u.subscribed))

@router.message(NameState.waiting)
async def set_name(message: Message, state: FSMContext, session: AsyncSession):
    nm = (message.text or "").strip()
    if len(nm) < 2:
        await message.answer("Имя слишком короткое. Введите ещё раз:")
        return
    await set_user_name(session, message.from_user.id, nm)
    await state.clear()
    await message.answer(f"Буду звать вас: <b>{nm}</b>.")

@router.message(F.text == "🛒 Показать товары")
async def show_last_from_all(message: Message, session: AsyncSession):
    tables = await list_existing_category_tables(session)
    if not tables:
        return await message.answer("Каталог пуст. Нажмите «🔁 Обновить каталог (парсинг)».")
    lines = []
    for t in sorted(tables):
        res = await session.execute(text(f'SELECT title, price, url FROM "{t}" ORDER BY id DESC LIMIT 5'))
        rows = res.fetchall()
        if not rows:
            continue
        lines.append(f"🔹 <b>{pretty_cat_from_table(t)}</b>")
        for title, price, url in rows:
            part = f"• <b>{title}</b>\n   Цена: {price}"
            if url: part += f"\n   {url}"
            lines.append(part)
        lines.append("")
    await message.answer("\n".join(lines)[:4096] if lines else "Товаров нет.")

@router.message(F.text == "📂 Показать по категории")
async def ask_category(message: Message, state: FSMContext, session: AsyncSession):
    tables = await list_existing_category_tables(session)
    if not tables:
        return await message.answer("Каталог пуст.")
    cats = [pretty_cat_from_table(t) for t in sorted(tables)]
    await message.answer("Доступные категории:\n\n" + "\n".join(f"• {c}" for c in cats) + "\n\nВведите название категории:")
    await state.set_state(CatState.waiting)

@router.message(CatState.waiting)
async def show_by_category(message: Message, state: FSMContext, session: AsyncSession):
    name = (message.text or "").strip()
    await state.clear()
    tname = table_name_for_category(name)
    tables = await list_existing_category_tables(session)
    if tname not in tables:
        return await message.answer("Такой категории нет.")
    res = await session.execute(text(f'SELECT title, price, url FROM "{tname}" ORDER BY id DESC LIMIT 20'))
    rows = res.fetchall()
    if not rows:
        return await message.answer("Товаров нет.")
    lines = [f"Категория: <b>{name}</b>", ""]
    for title, price, url in rows:
        part = f"• <b>{title}</b>\n   Цена: {price}"
        if url: part += f"\n   {url}"
        lines.append(part)
    await message.answer("\n\n".join(lines)[:4096])

@router.message(F.text == "✏️ Изменить имя")
async def rename(message: Message, state: FSMContext):
    await message.answer("Как к вам обращаться?")
    await state.set_state(NameState.waiting)

@router.message(F.text == "🔔 Подписаться")
async def sub(message: Message, session: AsyncSession):
    await set_subscribed(session, message.from_user.id, True)
    await message.answer("Вы подписались на авторассылку ✅")

@router.message(F.text == "🔕 Отписаться")
async def unsub(message: Message, session: AsyncSession):
    await set_subscribed(session, message.from_user.id, False)
    await message.answer("Вы отписались от авторассылки ❌")

@router.message(F.text == "🔁 Обновить каталог (парсинг)")
async def manual_refresh(message: Message, session: AsyncSession):
    from app.scheduler import _daily_scrape_full_replace
    from app.config import load_config
    await message.answer("⏳ Обновляем каталог (полная замена)…")
    try:
        cfg = load_config()
        await _daily_scrape_full_replace(cfg)
        await message.answer("Готово! Каталог обновлён.")
    except Exception:
        await message.answer("Ошибка при обновлении. Проверьте config.yaml.")
