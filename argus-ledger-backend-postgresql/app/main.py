"""ARGUS Ledger API application factory.

Thin composition root: wire settings, CORS, routers and error handling. All
persistence logic lives in ``app.services``; all model generation lives behind
``app.ai_service``.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# app/config.py reads .env through pydantic-settings, which does NOT populate
# os.environ. The integration layer (app/integrations/*, and EngineAIProvider in
# app/ai_service.py) reads os.getenv directly and at call time, on purpose — see
# app/integrations/engines/settings.py. Load .env into the process environment
# here, before those modules are imported, so both mechanisms see the same file.
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .config import get_settings
from .database import Base, engine
from .integrations.engines_router import router as engines_router
from .integrations.router import router as verification_router
from .routers import dashboard, decisions, health

logger = logging.getLogger("argus")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Local-dev convenience only. database/init.sql is authoritative for the
    # Docker/production database; create_all is a no-op when tables exist.
    Base.metadata.create_all(bind=engine)
    logger.info("ARGUS Ledger API %s ready", settings.version)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    summary="Audit-grade ledger for AI decisions (PS19 ARGUS Ledger).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(decisions.router)
app.include_router(dashboard.router)

# Integration layer. These adapters call external services (teammate AI engines,
# Tavily, OCR); each degrades to a warning in the response when its provider is
# unconfigured, so mounting them is safe with an empty .env.
app.include_router(verification_router)  # POST /verification/{text,url,image}
app.include_router(engines_router)       # GET /engines/status, POST /engines/{name}/infer


@app.exception_handler(IntegrityError)
async def _integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("integrity error: %s", exc)
    return JSONResponse(status_code=409, content={"detail": "conflicting or invalid data"})


@app.exception_handler(SQLAlchemyError)
async def _db_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("database error: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})
