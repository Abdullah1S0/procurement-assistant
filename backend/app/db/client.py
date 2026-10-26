"""MongoDB connection helpers."""
from functools import lru_cache
from typing import Any

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


def sample_documents(n: int = 3, projection: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """The first `n` real documents (read-only, no aggregation) - a cheap, truthful preview for
    "what do your rows/columns look like?" questions. Never fabricated."""
    return list(get_collection().find({}, projection).limit(n))
