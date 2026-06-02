"""CortexBrain FastAPI application — extends Cognee's API with novel endpoints.

Cognee's own API runs separately (cognee-cli -ui or cognee's FastAPI).
CortexBrain exposes its own API for query, correct, history, and health.
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()  # Load .env before any service init
from fastapi.middleware.cors import CORSMiddleware

from cortexbrain.api.v1 import router as v1_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Cognee and CortexBrain services on startup."""
    # Initialize Cognee's database engines
    try:
        from cognee.run_migrations import run_migrations
        await run_migrations()
        logger.info("Cognee migrations completed successfully")
    except SystemExit:
        logger.warning("Cognee migrations called sys.exit — ignoring (services may still be starting)")
    except Exception as e:
        logger.warning("Cognee migrations skipped (services may still be starting): %s", e)

    # Initialize CortexBrain's PostgreSQL tables (M_meta)
    try:
        from cortexbrain.memory.meta import MetaMemoryStore
        meta = MetaMemoryStore()
        await meta._get_session_factory()
        logger.info("CortexBrain M_meta tables initialized")
    except Exception as e:
        logger.warning("M_meta initialization skipped: %s", e)

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CortexBrain API",
        description="Auditable AI Knowledge System built by Abhisek Bose",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    return app


# App instance for uvicorn
app = create_app()
