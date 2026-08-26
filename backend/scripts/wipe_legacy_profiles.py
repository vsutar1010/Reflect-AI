"""
One-time migration: delete every twin created before per-user ownership
existed. Profiles created before this change have no `owner_id`, so they'd
otherwise be invisible-but-orphaned forever (no account can list, chat with,
or delete them through the API anymore).

This is a destructive, irreversible wipe of the `profiles` and
`conversations` collections — it does not filter by owner_id, it clears
both collections entirely. Only run it once, before anyone creates a real
account on this deployment.

Usage (from the backend/ directory, with the venv active and MONGODB_URI set
in backend/.env):

    python scripts/wipe_legacy_profiles.py --dry-run
    python scripts/wipe_legacy_profiles.py --yes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import conversations_collection, profiles_collection  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print counts, delete nothing")
    parser.add_argument("--yes", action="store_true", help="required to actually delete")
    args = parser.parse_args()

    profile_count = profiles_collection.count_documents({})
    conversation_count = conversations_collection.count_documents({})

    print(f"profiles: {profile_count} document(s)")
    print(f"conversations: {conversation_count} document(s)")

    if args.dry_run:
        print("\n[dry-run] nothing deleted.")
        return

    if not args.yes:
        raise SystemExit("\nRefusing to delete without --yes (use --dry-run to preview first).")

    profiles_collection.delete_many({})
    conversations_collection.delete_many({})
    print("\nDeleted all documents from profiles and conversations.")


if __name__ == "__main__":
    main()
