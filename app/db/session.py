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
else:
    # 1. Clean up "postgres://" to "postgresql://"
    if settings.DATABASE_URL.startswith("postgres://"):
        settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # 2. Extract and clean query parameters (asyncpg doesn't like 'sslmode')
    base_url = settings.DATABASE_URL
    query_params = ""
    if "?" in base_url:
        base_url, query_params = base_url.split("?", 1)
    
    # Remove 'sslmode' from parameters
    params_list = [p for p in query_params.split("&") if p and not p.startswith("sslmode=")]
    
    # 3. Ensure asyncpg driver is used
    if "postgresql" in base_url and "+asyncpg" not in base_url:
        base_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # 4. Handle SSL for production
    if settings.ENV == "production":
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        if not any(p.startswith("ssl=") for p in params_list):
            params_list.append("ssl=require")
    
    # 5. Reconstruct URL
    settings.DATABASE_URL = base_url
    if params_list:
        settings.DATABASE_URL += "?" + "&".join(params_list)

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
