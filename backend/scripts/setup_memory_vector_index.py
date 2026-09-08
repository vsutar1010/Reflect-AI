"""
Creates the MongoDB Atlas Vector Search index used by
MemoryStore._vector_search (app/services/rag/memory_store.py) on the
`memories` collection.

This is entirely optional. Memory search always tries $vectorSearch
first and transparently falls back to an in-process brute-force cosine
scan when the index doesn't exist (see MemoryStore.search) — so RAG is
fully functional before this script is ever run. Run it once your data
volume makes the brute-force scan worth avoiding, or any time you
change EMBEDDING_DIMENSIONS / LOCAL_EMBEDDING_DIMENSIONS (the index's
vector dimension must match whatever's actually stored, so changing
embedding providers/dimensions requires re-creating it — and
re-indexing existing memories, since old vectors won't match the new
dimension either).

Requires an Atlas cluster with Atlas Search enabled (self-hosted /
non-Atlas MongoDB, and some shared-tier clusters, don't support this —
the script reports a clear error and instructions instead of crashing
if creation fails; brute-force search keeps working either way).

Usage (from the backend/ directory, with the venv active and
MONGODB_URI set in backend/.env):

    python scripts/setup_memory_vector_index.py
    python scripts/setup_memory_vector_index.py --dimensions 1536
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app import config  # noqa: E402
from app.database import memories_collection  # noqa: E402


def build_index_definition(dimensions: int) -> dict:
    return {
        "fields": [
            {"type": "vector", "path": "embedding", "numDimensions": dimensions, "similarity": "cosine"},
            {"type": "filter", "path": "user_id"},
            {"type": "filter", "path": "profile_id"},
            {"type": "filter", "path": "source_type"},
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the Atlas Vector Search index for RAG memory search.")
    parser.add_argument(
        "--dimensions",
        type=int,
        default=None,
        help=(
            "Embedding vector dimension to index. Defaults to config.EMBEDDING_DIMENSIONS "
            "if an API embedding provider is configured, otherwise config.LOCAL_EMBEDDING_DIMENSIONS."
        ),
    )
    parser.add_argument("--name", default=config.MEMORY_VECTOR_INDEX_NAME, help="index name (must match MEMORY_VECTOR_INDEX_NAME)")
    args = parser.parse_args()

    dimensions = args.dimensions or (
        config.EMBEDDING_DIMENSIONS if config.EMBEDDING_API_KEY else config.LOCAL_EMBEDDING_DIMENSIONS
    )

    print(f"Creating Atlas Vector Search index {args.name!r} on memories.embedding (dimensions={dimensions})...")

    try:
        from pymongo.operations import SearchIndexModel

        model = SearchIndexModel(definition=build_index_definition(dimensions), name=args.name, type="vectorSearch")
        memories_collection.create_search_index(model)
    except Exception as e:
        print(
            f"\n[error] Could not create the index via the driver: {e}\n\n"
            "This usually means the cluster tier doesn't support Atlas Search "
            "index management via the driver, or Atlas Search isn't available at all "
            "on this cluster. RAG memory search still works without this index — it "
            "automatically falls back to an in-process brute-force cosine search — "
            "so this is a performance optimization, not a requirement.\n\n"
            "To create it manually instead: Atlas dashboard -> your cluster -> "
            "Search -> Create Search Index -> Atlas Vector Search -> JSON Editor, "
            f"database {config.MONGODB_DB_NAME!r}, collection 'memories', index name "
            f"{args.name!r}, and paste:\n\n{build_index_definition(dimensions)}"
        )
        raise SystemExit(1)

    print("Index creation requested. Waiting for it to become queryable (this can take a minute)...")
    for _ in range(30):
        indexes = list(memories_collection.list_search_indexes(args.name))
        if indexes and indexes[0].get("queryable"):
            print("Index is ready.")
            return
        time.sleep(5)

    print(
        "[note] Index was created but hasn't finished building yet — check "
        "Atlas dashboard -> Search for status. Brute-force search covers "
        "queries until it's ready."
    )


if __name__ == "__main__":
    main()
