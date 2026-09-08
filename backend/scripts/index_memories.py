"""
Backfills the RAG memory index (the `memories` collection — see
app/services/rag/) from data that already exists in MongoDB: each
profile's interview/WhatsApp transcript, its live conversation history,
and its running summary.

Needed for profiles created before this feature existed — new profiles
are indexed automatically at creation time (see
PersonalityAnalyzer._build_and_save_profile), and new chat turns are
indexed live (see TextChatService/VoiceChatService). This script never
modifies `profiles` or `conversations` — it only reads them and writes
derived rows into the separate `memories` collection.

Usage (from the backend/ directory, with the venv active and
MONGODB_URI set in backend/.env):

    python scripts/index_memories.py --profile <id>
    python scripts/index_memories.py --all
    python scripts/index_memories.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import conversations_collection, profiles_collection  # noqa: E402
from app.services.rag.embedding_service import get_embedding_provider  # noqa: E402
from app.services.rag.indexer import MemoryIndexer  # noqa: E402
from app.services.rag.memory_store import MemoryStore  # noqa: E402


def index_one(indexer: MemoryIndexer, profile_doc: dict, dry_run: bool) -> dict:
    profile_id = profile_doc["_id"]
    owner_id = profile_doc.get("owner_id")
    name = profile_doc.get("name", profile_id)
    messages = profile_doc.get("conversation") or []

    counts = {"transcript": 0, "conversation": 0, "summary": 0}

    if not owner_id:
        print(f"[skip] {profile_id} ({name}): no owner_id on this profile document")
        return counts

    print(f"\n{'=' * 70}\n{name}  ({profile_id})\n{'=' * 70}")

    if dry_run:
        thread_doc = conversations_collection.find_one({"_id": f"{profile_id}:default"}) or {}
        print(f"  would index: {len(messages)} transcript message(s), "
              f"{len(thread_doc.get('messages', []))} conversation turn(s), "
              f"summary={'yes' if thread_doc.get('summary') else 'no'}")
        return counts

    # Interview transcripts alternate assistant/user; a WhatsApp-import
    # transcript is 100% role="user". Either shape is handled correctly
    # by whichever indexer method is called — detect which one this is
    # by checking for any assistant-authored message.
    is_interview = any(m.get("role") == "assistant" for m in messages)
    if messages:
        if is_interview:
            counts["transcript"] = indexer.index_interview(profile_id, owner_id, messages)
        else:
            counts["transcript"] = indexer.index_whatsapp(profile_id, owner_id, messages)
        print(f"  indexed {counts['transcript']} transcript chunk(s) "
              f"({'interview' if is_interview else 'whatsapp'})")

    thread_doc = conversations_collection.find_one({"_id": f"{profile_id}:default"})
    if thread_doc:
        turns = thread_doc.get("messages") or []
        for i, turn in enumerate(turns):
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            indexer.index_conversation_turn(
                profile_id, owner_id, turn.get("role", "user"), content,
                thread="default", turn_index=i, channel=turn.get("channel", "text"),
            )
            counts["conversation"] += 1
        print(f"  indexed {counts['conversation']} conversation turn(s)")

        summary = thread_doc.get("summary")
        if summary:
            indexer.index_conversation_summary(profile_id, owner_id, summary, "default")
            counts["summary"] = 1
            print("  indexed conversation summary")

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill the RAG memory index from existing MongoDB data.")
    parser.add_argument("--profile", help="single profile id")
    parser.add_argument("--all", action="store_true", help="every profile in the collection")
    parser.add_argument("--dry-run", action="store_true", help="print what would be indexed, write nothing")
    args = parser.parse_args()

    if not args.profile and not args.all:
        parser.error("pass --profile <id> or --all")
    if args.profile and args.all:
        parser.error("pass --profile or --all, not both")

    if args.all:
        docs = list(profiles_collection.find({}))
        if not docs:
            raise SystemExit("No profiles found.")
    else:
        doc = profiles_collection.find_one({"_id": args.profile})
        if not doc:
            raise SystemExit(f"No such profile: {args.profile}")
        docs = [doc]

    indexer = MemoryIndexer(MemoryStore(), get_embedding_provider())
    print(f"Embedding provider: {indexer.embedder.name} (dimensions={indexer.embedder.dimensions})")

    totals = {"transcript": 0, "conversation": 0, "summary": 0}
    for doc in docs:
        counts = index_one(indexer, doc, args.dry_run)
        for k in totals:
            totals[k] += counts[k]

    if args.dry_run:
        print(f"\n[dry-run] {len(docs)} profile(s) scanned. Nothing written.")
    else:
        print(
            f"\nDone. {len(docs)} profile(s) processed — "
            f"{totals['transcript']} transcript chunk(s), "
            f"{totals['conversation']} conversation turn(s), "
            f"{totals['summary']} summary/summaries indexed."
        )


if __name__ == "__main__":
    main()
