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

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    # Lightweight ping — no DB hit, accepts GET and HEAD (UptimeRobot uses HEAD)
    return {"status": "ok"}

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
