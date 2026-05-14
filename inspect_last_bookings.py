import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def inspect_data():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        query = text("SELECT id, patient_name, place, date FROM dashboard_bookings ORDER BY date DESC LIMIT 5")
        result = await conn.execute(query)
        rows = result.mappings().all()
        print("Last 5 Bookings:")
        for row in rows:
            print(f"ID: {row['id']} | Name: {row['patient_name']} | Place: '{row['place']}' | Date: {row['date']}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect_data())
