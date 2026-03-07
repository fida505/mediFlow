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
    # 1. Standardize for asyncpg
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # 2. Production SSL handling
    if settings.ENV == "production":
        engine_kwargs["pool_size"] = 4          # Increased from 2 for better startup resilience
        engine_kwargs["max_overflow"] = 6        # Increased from 3 for burst handling
        engine_kwargs["pool_timeout"] = 30       # Fail fast, don't hang forever
        engine_kwargs["pool_pre_ping"] = True    # Auto-recover dead connections
        # Supabase pooler (pgBouncer) transaction mode requires statement_cache_size=0 for asyncpg
        engine_kwargs["connect_args"] = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "timeout": 20                        # DB connect timeout (seconds)
        }
        # Simple query param addition
        if "ssl=" not in url:
            sep = "&" if "?" in url else "?"
            url += f"{sep}ssl=require"
    
    settings.DATABASE_URL = url

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
