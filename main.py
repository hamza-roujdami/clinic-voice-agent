"""FastAPI server for Clinic Voice Agent.

Usage:
    python main.py
    
    # Or with uvicorn directly:
    uvicorn main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import router
from config import config
from agents.factory import AgentFactory
from sessions import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Enable DEBUG for agent_framework to see tool call errors
logging.getLogger("agent_framework").setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Validate config
    missing = config.validate()
    if missing:
        logger.warning("Missing environment variables: %s", missing)
        logger.warning("Some features may not work. Copy .env.example to .env and configure.")
        app.state.factory = None
        app.state.sessions = None
    else:
        # Initialize agent factory
        logger.info("Starting Clinic Voice Agent...")
        factory = AgentFactory(
            project_endpoint=config.project_endpoint,
            model=config.model_primary,
        )
        await factory.__aenter__()
        app.state.factory = factory
        logger.info("Agent factory initialized successfully")
        
        # Initialize session manager (Cosmos + Memory)
        sessions = SessionManager(
            cosmos_endpoint=config.cosmos_endpoint,
            cosmos_database=config.cosmos_database,
            cosmos_container=config.cosmos_container,
            project_endpoint=config.project_endpoint,
        )
        await sessions.__aenter__()
        app.state.sessions = sessions
        logger.info("Session manager initialized: %s", sessions.get_stats())

    yield

    # Cleanup on shutdown
    if hasattr(app.state, "sessions") and app.state.sessions is not None:
        await app.state.sessions.__aexit__(None, None, None)
    if hasattr(app.state, "factory") and app.state.factory is not None:
        await app.state.factory.__aexit__(None, None, None)
    logger.info("Shutting down...")


app = FastAPI(
    title="Clinic Voice Agent",
    description="Voice Scheduling Assistant for Hospital Call Centers",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(router)

# Serve static files (if exists)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass


@app.get("/")
async def root():
    """Serve the main UI."""
    try:
        return FileResponse("static/index.html")
    except Exception:
        return {"status": "healthy", "service": "clinic-voice-agent"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    factory_ok = hasattr(app.state, "factory") and app.state.factory is not None
    return {"status": "healthy", "factory_initialized": factory_ok}


if __name__ == "__main__":
    import uvicorn

    print(f"\n🎯 Clinic Voice Agent")
    print(f"   http://{config.host}:{config.port}\n")

    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=True,
    )
