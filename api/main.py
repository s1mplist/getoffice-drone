import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.router import router
from core.settings import get_settings

settings = get_settings()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=settings.log_level,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    debug=settings.log_level == "DEBUG",
    title="GetOffice Drone API",
    description="API for GetOffice Drone application",
    version="1.0.0",
)
logger.info("FastAPI application initialized.")
logger.debug(f"API settings: {settings}")

# Serve static assets (e.g., styles) from the templates directory
BASE_DIR = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "templates")), name="static")

app.include_router(router)
logger.info("Routes have been included in the FastAPI application.")
logger.debug("API routes: " + ", ".join(route.path for route in app.router.routes))


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify that the API is running."""
    logger.debug("Health check endpoint called")
    return {"status": "ok"}
