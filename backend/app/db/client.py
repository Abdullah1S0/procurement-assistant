"""MongoDB connection helpers."""
from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection

from app.config import get_settings


@lru_cache
def get_client() -> MongoClient:
    """Return a process-wide MongoClient."""
    return MongoClient(get_settings().mongo_uri, serverSelectionTimeoutMS=5000, tz_aware=False)


def get_collection() -> Collection:
    """Return the `purchases` collection (the only collection the agent may query)."""
    s = get_settings()
    return get_client()[s.mongo_db][s.mongo_collection]
