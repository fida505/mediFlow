# MediFlow Main Application - Updated 2026-03-11 22:45
from fastapi import FastAPI
from app.core.logging import configure_logging
from app.core.exceptions import register_exception_handlers
from app.routers import clinics, admin, bookings, auth
from fastapi.staticfiles import StaticFiles
from app.db.session import AsyncSessionLocal
from app.routers.bookings import init_db

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
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok", "version": "v3-auth-debug"}

@app.post("/test-login")
async def test_login():
    return {"message": "Test login works", "version": "v3-auth-debug"}

from fastapi.responses import FileResponse

@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")

# startup/shutdown events
@app.on_event("startup")
async def startup_event():
    print(">>> Starting MediFlow application...")
    try:
        async with AsyncSessionLocal() as db:
            print(">>> Initializing database tables and migrations...")
            await bookings.init_db(db)
            print(">>> Database initialization complete.")
    except Exception as e:
        print(f"!!! CRITICAL ERROR: Database initialization failed: {e}")
        # We catch the exception to allow the app to start and respond to health checks, 
        # providing better visibility into the failure through logs.
    print(">>> Application is ready to serve requests.")

@app.on_event("shutdown")
async def shutdown_event():
    # cleanup
    pass
