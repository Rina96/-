from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from config import settings

engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False, connect_args={"ssl": True}) if "postgres" in settings.DATABASE_URL else create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

from contextlib import asynccontextmanager
@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
