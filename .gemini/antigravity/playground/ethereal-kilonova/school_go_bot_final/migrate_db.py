import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base
from config import settings
from loguru import logger

async def run_migration():
    logger.info("🛠 Starting Database Schema Migration...")
    
    # Use the async URL
    DATABASE_URL = settings.ASYNC_DATABASE_URL
    if "postgres" in DATABASE_URL:
        engine = create_async_engine(DATABASE_URL, connect_args={"ssl": True})
    else:
        engine = create_async_engine(DATABASE_URL)
        
    async with engine.begin() as conn:
        # This will create tables if they don't exist
        # NOTE: In production, we'd use Alembic, but for this rapid upgrade, 
        # we ensure the schema matches the models.
        logger.info("🔄 Syncing tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    logger.success("✅ Database Schema Synced Successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
