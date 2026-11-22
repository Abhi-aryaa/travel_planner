"""MongoDB connection. Falls back to an in-memory mock when MONGODB_URI is not set."""
import logging

from .config import settings

log = logging.getLogger("db")
_client = None


def get_client():
    global _client
    if _client is None:
        if settings.MONGODB_URI:
            from motor.motor_asyncio import AsyncIOMotorClient

            _client = AsyncIOMotorClient(settings.MONGODB_URI)
            log.info("Connected to MongoDB")
        else:
            from mongomock_motor import AsyncMongoMockClient

            _client = AsyncMongoMockClient()
            log.warning("MONGODB_URI not set - using in-memory mock database")
    return _client


def trips_collection():
    return get_client()[settings.MONGODB_DB]["trips"]
