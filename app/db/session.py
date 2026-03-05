from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine_kwargs = {"future": True}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    # Ensure aiosqlite is used for async sqlite
    if "aiosqlite" not in settings.DATABASE_URL:
        settings.DATABASE_URL = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
else:
    # Use standard postgresql dialect if postgres:// is used
    if settings.DATABASE_URL.startswith("postgres://"):
        settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Ensure async driver is used
    if "postgresql" in settings.DATABASE_URL and "+asyncpg" not in settings.DATABASE_URL:
        settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Production optimizations and SSL
    if settings.ENV == "production":
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        # Supabase and Render often need SSL
        if "sslmode" not in settings.DATABASE_URL and "sqlite" not in settings.DATABASE_URL:
             if "?" in settings.DATABASE_URL:
                 settings.DATABASE_URL += "&sslmode=require"
             else:
                 settings.DATABASE_URL += "?sslmode=require"

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
