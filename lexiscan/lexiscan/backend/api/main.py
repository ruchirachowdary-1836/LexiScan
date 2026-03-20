"""
LexiScan — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from backend.api.routes import contracts, health
from backend.utils.config import settings
from backend.utils.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("🚀 LexiScan API starting up...")
    # Create DB tables
    try:
        create_tables()
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.warning(f"DB init failed (will retry on first request): {e}")

    # Warm up models in background (optional)
    # asyncio.create_task(warmup_models())

    yield

    logger.info("👋 LexiScan API shutting down")


app = FastAPI(
    title="LexiScan API",
    description="Legal Document Risk Analyzer — AI-powered contract review",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(contracts.router, prefix="/api/v1/contracts", tags=["Contracts"])


# ── Root ──────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "LexiScan Legal Document Risk Analyzer",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running",
    }
