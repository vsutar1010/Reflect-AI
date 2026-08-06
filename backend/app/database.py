"""
MongoDB connection — the single place that owns the database client.

Replaces the old flat-file storage under backend/profiles/{uuid}/*.json.
A MongoClient is thread-safe and pools connections internally, so creating
it once here at import time (mirroring the service singletons in
dependencies.py) means every request reuses pooled connections instead of
opening a new one — this is what actually keeps read/write latency low
under load, not just "using a database" by itself.

Two collections, mirroring the previous four-file-per-profile layout:
  profiles       — one document per twin (was profile.json + metadata.json
                    + conversation.json), _id = profile UUID
  conversations   — one document per chat thread (was
                    conversations/{thread}.json), _id = "{profile_id}:{thread}"
"""

from __future__ import annotations

import certifi
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app import config

if not config.MONGODB_URI:
    raise RuntimeError(
        "MONGODB_URI is not set. Add it to backend/.env — see backend/.env.example "
        "for the expected format (e.g. a MongoDB Atlas connection string)."
    )

try:
    # For mongodb+srv:// URIs (Atlas), pymongo resolves the DNS SRV record
    # right here at construction time — so a wrong cluster hostname or no
    # network fails immediately, not lazily on first query.
    client: MongoClient = MongoClient(config.MONGODB_URI, tlsCAFile=certifi.where())
except PyMongoError as e:
    raise RuntimeError(
        f"Could not parse/resolve MONGODB_URI: {e}. Check the connection string "
        "in backend/.env against your MongoDB Atlas dashboard."
    ) from e

db: Database = client[config.MONGODB_DB_NAME]

profiles_collection: Collection = db["profiles"]
conversations_collection: Collection = db["conversations"]


def ping() -> None:
    """
    Verifies the MongoDB connection works, raising a clear error at startup
    instead of letting a bad MONGODB_URI surface later as a confusing 500 on
    someone's first chat message.
    """
    client.admin.command("ping")


def init_indexes() -> None:
    conversations_collection.create_index([("profile_id", ASCENDING)])
