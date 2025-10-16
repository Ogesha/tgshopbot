from typing import Iterable, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, ChatLog

async def get_or_create_user(s: AsyncSession, tg_id: int, username: str | None) -> User:
    res = await s.execute(select(User).where(User.tg_id == tg_id))
    u = res.scalar_one_or_none()
    if u: return u
    u = User(tg_id=tg_id, username=username)
    s.add(u)
    await s.commit()
    return u

async def set_user_name(s: AsyncSession, tg_id: int, name: str):
    await s.execute(update(User).where(User.tg_id == tg_id).values(display_name=name))
    await s.commit()

async def set_subscribed(s: AsyncSession, tg_id: int, value: bool):
    await s.execute(update(User).where(User.tg_id == tg_id).values(subscribed=value))
    await s.commit()

async def list_users(s: AsyncSession, limit: int = 100) -> List[User]:
    res = await s.execute(select(User).order_by(User.created_at.desc()).limit(limit))
    return list(res.scalars().all())

async def admins_bootstrap(s: AsyncSession, admin_ids: Iterable[int]):
    res = await s.execute(select(User))
    existing = {u.tg_id for u in res.scalars().all()}
    for aid in admin_ids:
        if aid not in existing:
            s.add(User(tg_id=aid, username=None, is_admin=True))
    await s.commit()
    await s.execute(update(User).where(User.tg_id.in_(list(admin_ids))).values(is_admin=True))
    await s.commit()

async def log_message(s: AsyncSession, tg_id: int, direction: str, text: str):
    s.add(ChatLog(tg_id=tg_id, direction=direction, text=(text or "")[:4096]))
    await s.commit()
