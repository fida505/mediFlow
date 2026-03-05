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
    from app.config import settings
    import socket
    
    # Mask URL for security
    url = settings.DATABASE_URL
    host = "no-host"
    if "@" in url:
        host_port = url.split("@")[-1].split("/")[0]
        host = host_port.split(":")[0]
    
    resolved_ip = "unknown"
    try:
        resolved_ip = socket.gethostbyname(host)
    except:
        pass
        
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "resolved_ip": resolved_ip}
    except Exception as e:
        return {"status": "error", "database": str(e), "resolved_ip": resolved_ip}

from fastapi.responses import FileResponse

@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")

# startup/shutdown events
@app.on_event("startup")
async def startup_event():
    # init database, cache, celery, etc.
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # cleanup
    pass
