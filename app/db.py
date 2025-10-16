from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession
from sqlalchemy.orm import declarative_base

Base = declarative_base()

_engine: AsyncEngine | None = None
Session: async_sessionmaker[AsyncSession] | None = None

def init_engine(db_url: str):
    global _engine, Session
    _engine = create_async_engine(db_url, echo=False, future=True)
    Session = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine, Session

def get_sessionmaker():
    if Session is None:
        raise RuntimeError("Session не инициализирован")
    return Session
