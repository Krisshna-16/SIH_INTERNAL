import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.reports import router as reports_router
from app.api.v1.extraction import router as extraction_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.symbolic import router as symbolic_router
from app.api.v1.timeline import router as timeline_router
from app.api.v1.graph import router as graph_router
from app.api.v1.query import router as query_router
from app.api.v1.answer import router as answer_router
from app.auth.dependencies import get_current_user

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.session import engine, Base, ensure_sqlite_schema_up_to_date
import app.models  # Ensure all SQLAlchemy models are registered for metadata creation

from scripts.seed_demo_user import seed_demo_user
from scripts.seed_demo_data import seed_demo_data

logger = logging.getLogger(__name__)

# Initialize structured logging
setup_logging()

# Create DB tables if they don't exist
Base.metadata.create_all(bind=engine)

# Safely check and add any missing columns to SQLite schema
ensure_sqlite_schema_up_to_date(engine)

# Automatically seed default demo user and report data on startup if missing
try:
    seed_demo_user()
    seed_demo_data()
    logger.info("Automatic database seeding check completed successfully.")
except Exception as e:
    logger.warning(f"Automatic database seeding encountered warning: {e}")

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware to allow all localhost/127.0.0.1 ports dynamically
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unprotected Public Routers
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)

# Protected Forensic API Routers (Requires Bearer JWT Token)
authenticated_dep = [Depends(get_current_user)]

app.include_router(reports_router, prefix=settings.API_V1_PREFIX, dependencies=authenticated_dep)
app.include_router(extraction_router, prefix=settings.API_V1_PREFIX, dependencies=authenticated_dep)
app.include_router(evidence_router, prefix=settings.API_V1_PREFIX, dependencies=authenticated_dep)
app.include_router(symbolic_router, prefix=settings.API_V1_PREFIX, dependencies=authenticated_dep)
app.include_router(timeline_router, prefix=settings.API_V1_PREFIX, dependencies=authenticated_dep)
app.include_router(graph_router, prefix=settings.API_V1_PREFIX, dependencies=authenticated_dep)
app.include_router(query_router, prefix=settings.API_V1_PREFIX, dependencies=authenticated_dep)
app.include_router(answer_router, prefix=settings.API_V1_PREFIX, dependencies=authenticated_dep)


@app.get("/")
def read_root():
    """Root endpoint returning basic system information and API documentation links."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
