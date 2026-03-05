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
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
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
