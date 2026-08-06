"""
One-time migration: import existing backend/profiles/{uuid}/*.json data
into MongoDB.

Usage (from the backend/ directory, with the venv/conda env active and
MONGODB_URI set in backend/.env):

    python scripts/migrate_to_mongodb.py

Safe to re-run — every write is an upsert keyed by the same _id the app
itself will use, so running this twice just re-imports the same documents
instead of duplicating them. Does NOT delete anything from disk; the
original backend/profiles/ directory is left untouched as a backup.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import conversations_collection, profiles_collection  # noqa: E402

PROFILES_DIR = BACKEND_DIR / "profiles"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ! could not read {path}: {e}")
        return default


def migrate_profile(profile_dir: Path) -> None:
    profile_id = profile_dir.name
    print(f"Migrating profile {profile_id}...")

    metadata = _read_json(profile_dir / "metadata.json", {})
    profile = _read_json(profile_dir / "profile.json", {})
    conversation = _read_json(profile_dir / "conversation.json", {}).get("messages", [])

    if not profile:
        print(f"  ! skipping {profile_id}: no profile.json found")
        return

    profiles_collection.update_one(
        {"_id": profile_id},
        {
            "$set": {
                "name": metadata.get("name", "My Twin"),
                "created_at": metadata.get("created_at", ""),
                "last_used": metadata.get("last_used", ""),
                "version": metadata.get("version", 1),
                "profile": profile,
                "conversation": conversation,
            }
        },
        upsert=True,
    )
    print(f"  - profile document upserted (name={metadata.get('name')!r})")

    conversations_dir = profile_dir / "conversations"
    if conversations_dir.exists():
        for thread_file in conversations_dir.glob("*.json"):
            thread = thread_file.stem
            data = _read_json(thread_file, {})
            messages = data.get("messages", [])
            updated_at = _read_json(profile_dir / "metadata.json", {}).get("last_used", "")

            conversations_collection.update_one(
                {"_id": f"{profile_id}:{thread}"},
                {
                    "$set": {
                        "profile_id": profile_id,
                        "thread": thread,
                        "messages": messages,
                        "updated_at": updated_at,
                    }
                },
                upsert=True,
            )
            print(f"  - conversation thread '{thread}' upserted ({len(messages)} messages)")


def main() -> None:
    if not PROFILES_DIR.exists():
        print(f"No profiles directory found at {PROFILES_DIR} — nothing to migrate.")
        return

    profile_dirs = [p for p in PROFILES_DIR.iterdir() if p.is_dir()]
    if not profile_dirs:
        print("No profiles found — nothing to migrate.")
        return

    for profile_dir in profile_dirs:
        migrate_profile(profile_dir)

    print(f"\nDone. Migrated {len(profile_dirs)} profile(s) into MongoDB.")
    print("backend/profiles/ was left untouched — verify the data in MongoDB before deleting it.")


if __name__ == "__main__":
    main()
