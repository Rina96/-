import asyncio
from database import engine, Base
import models # Убеждаемся, что модели загружены

async def init_db():
    print("🧹 Очистка и создание таблиц...")
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # На всякий случай не удаляем, если там что-то есть
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных готова!")

if __name__ == "__main__":
    asyncio.run(init_db())
