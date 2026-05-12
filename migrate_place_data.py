import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def migrate_data():
    # Adding statement_cache_size=0 to handle pgbouncer issues
    engine = create_async_engine(DATABASE_URL, connect_args={"statement_cache_size": 0})
    async with engine.begin() as conn:
        # First, count how many records we are about to change
        count_query = text("""
            SELECT count(*) 
            FROM dashboard_bookings 
            WHERE (place IS NULL OR place = '') 
              AND notes IS NOT NULL 
              AND notes != ''
        """)
        result = await conn.execute(count_query)
        count = result.scalar()
        print(f"Found {count} records to migrate.")

        if count > 0:
            # Update query: Move notes to place and clear notes
            update_query = text("""
                UPDATE dashboard_bookings 
                SET place = notes, 
                    notes = '' 
                WHERE (place IS NULL OR place = '') 
                  AND notes IS NOT NULL 
                  AND notes != ''
            """)
            await conn.execute(update_query)
            print(f"Successfully migrated {count} records.")
        else:
            print("No records found that need migration.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_data())
