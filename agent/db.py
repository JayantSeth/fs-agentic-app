import os
from typing import AsyncGenerator

from sqlalchemy import Column, Integer, JSON, String, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Fallbacks provided for local SQLite file DB if environment variables are unset
db_url = "sqlite:///./chat.db"
async_db_url = "sqlite+aiosqlite:///./chat.db"

# Sync Engine
engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})

# Async Engine
async_engine = create_async_engine(async_db_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class ChatHistory(Base):
    __tablename__ = "chat_history"

    session_id = Column(String(150), primary_key=True, index=True)
    
    # SQLite uses generic JSON instead of Postgres-specific JSONB
    messages = Column(JSON, default=dict, nullable=False)

    tokens_used = Column(Integer, nullable=False, server_default=text("0"))