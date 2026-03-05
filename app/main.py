from fastapi import FastAPI
from app.core.logging import configure_logging
from app.core.exceptions import register_exception_handlers
from app.routers import clinics, admin, bookings
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MediFlow SaaS Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_logging()
register_exception_handlers(app)

# include routers
app.include_router(clinics.router, prefix="/clinics", tags=["clinics"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])

@app.get("/health")
async def health_check():
    from sqlalchemy import text
    from app.db.session import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}

# serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# startup/shutdown events
@app.on_event("startup")
async def startup_event():
    # init database, cache, celery, etc.
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # cleanup
    pass
