"""FastAPI entrypoint: mounts API routers and serves the static frontend."""
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routes import ai, places, trips

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Travel Planner API", version="1.0.0")
app.include_router(trips.router)
app.include_router(places.router)
app.include_router(ai.router)


@app.get("/api/config")
async def public_config():
    """Only exposes what the browser needs (Maps JS key is a browser key by design)."""
    return {
        "maps_provider": "google" if settings.GOOGLE_MAPS_API_KEY else "osm",
        "google_maps_key": settings.GOOGLE_MAPS_API_KEY,
        "ai_provider": "gemini" if settings.GEMINI_API_KEY else "rules",
        "database": "mongodb" if settings.MONGODB_URI else "in-memory",
    }


app.mount("/", StaticFiles(directory=settings.FRONTEND_DIR, html=True), name="frontend")
