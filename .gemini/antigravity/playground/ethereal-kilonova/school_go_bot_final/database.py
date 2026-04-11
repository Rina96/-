from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
import ssl
from loguru import logger
from config import settings

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

is_postgres = "postgres" in settings.DATABASE_URL
logger.info(f"🔌 Initializing Database [Postgres={is_postgres}, SSL_Skip=True]")

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL, 
    echo=False, 
    connect_args={"ssl": get_ssl_context()} if is_postgres else {}
)
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
