import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.services.queue import get_job_queue

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage directories exist
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    os.makedirs(settings.YT_DLP_STORAGE_PATH, exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "clips"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "uploads"), exist_ok=True)

    # Initialize tables if SQLite is used
    if "sqlite" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Start background job queue worker
    job_queue = get_job_queue()
    job_queue.start()

    yield

    # Cleanup resources
    await job_queue.stop()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Viral Moment Clipping API with YouTube Shorts Direct Publishing",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router, prefix="/api")
app.include_router(upload_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Welcome to ClipViral API",
        "docs_url": "/docs",
        "health_check": "/api/health"
    }
