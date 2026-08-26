"""
One-time (or per-fix) maintenance: rebuild identity_prompt for existing
profiles from already-stored data, without re-running the interview.

build_identity_prompt() is only called once, inside
PersonalityAnalyzer._build_and_save_profile(), and its output is baked into
the profile document at analysis time. Fixing the builder therefore does
nothing for profiles that already exist until this script re-derives their
prompt from the communication fingerprint and llm_analysis already sitting
in MongoDB — both are already on the profile document, so no re-interview is
needed, and the raw interview transcript / conversation history are never
touched.

Usage (from the backend/ directory, with the venv active and MONGODB_URI set
in backend/.env):

    python scripts/rebuild_identity_prompts.py --profile <id> --dry-run
    python scripts/rebuild_identity_prompts.py --profile <id>
    python scripts/rebuild_identity_prompts.py --all

After a real (non-dry-run) write, this also best-effort pokes a running
backend at --api (default http://localhost:8000) to drop that profile from
DigitalTwinEngine's in-memory cache — see _notify_running_backend() below for
why a local invalidate_cache() call in this standalone process isn't enough
on its own.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import profiles_collection  # noqa: E402
from app.services.analyzer import PersonalityAnalyzer  # noqa: E402
from app.services.twin_engine import DigitalTwinEngine  # noqa: E402

DEFAULT_API = "http://localhost:8000"


def _notify_running_backend(api: str, profile_id: str) -> None:
    """
    This script runs as its own process, separate from the uvicorn worker
    serving live chat traffic — so calling engine.invalidate_cache() on the
    DigitalTwinEngine instance created below only clears a cache that was
    never populated in the first place; it does nothing for the live
    server's already-cached TwinContext. Hitting this reload endpoint runs
    the same invalidate_cache() call, but inside the live process, the way
    profiles.delete_profile() already does for deletions. Best-effort: if
    the backend isn't reachable (e.g. this is being run against a profile
    export with no server up), that's fine, the write to Mongo already
    happened and the next server start will read the fresh prompt anyway.
    """
    req = urllib.request.Request(
        f"{api}/api/profiles/{profile_id}/reload",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            print(f"  notified running backend at {api} to drop its cached copy")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"  [note] could not reach {api} to invalidate its cache ({e}); "
              f"restart the backend (or wait for uvicorn --reload) to pick this up")


def rebuild_one(analyzer: PersonalityAnalyzer, engine: DigitalTwinEngine, doc: dict, dry_run: bool, api: str) -> bool:
    profile_id = doc["_id"]
    profile = doc.get("profile") or {}
    communication = profile.get("communication") or {}
    llm_analysis = profile.get("llm_analysis") or {}

    if not communication:
        print(f"[skip] {profile_id}: no stored communication fingerprint, nothing to rebuild from")
        return False

    new_prompt = analyzer.build_identity_prompt(communication, llm_analysis)
    old_prompt = profile.get("identity_prompt", "")

    print(f"\n{'=' * 70}\n{doc.get('name', profile_id)}  ({profile_id})\n{'=' * 70}")

    if dry_run:
        print(new_prompt)
        print(f"\n[dry-run] {len(old_prompt)} -> {len(new_prompt)} chars, nothing written")
        return True

    profiles_collection.update_one(
        {"_id": profile_id},
        {"$set": {"profile.identity_prompt": new_prompt}},
    )
    # Interview transcript (`conversation`) and conversation history
    # (the `conversations` collection) are never touched above — only
    # `profile.identity_prompt` is written.
    engine.invalidate_cache(profile_id)
    print(f"  rebuilt identity_prompt ({len(old_prompt)} -> {len(new_prompt)} chars)")
    _notify_running_backend(api, profile_id)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild identity_prompt for existing profiles from already-stored communication/LLM data."
    )
    parser.add_argument("--profile", help="single profile id")
    parser.add_argument("--all", action="store_true", help="every profile in the collection")
    parser.add_argument("--dry-run", action="store_true", help="print the new prompt for each profile, write nothing")
    parser.add_argument("--api", default=DEFAULT_API, help=f"running backend base URL for cache invalidation (default {DEFAULT_API})")
    args = parser.parse_args()

    if not args.profile and not args.all:
        parser.error("pass --profile <id> or --all")

    if args.profile and args.all:
        parser.error("pass --profile or --all, not both")

    analyzer = PersonalityAnalyzer()
    engine = DigitalTwinEngine()

    if args.all:
        docs = list(profiles_collection.find({}))
        if not docs:
            raise SystemExit("No profiles found.")
    else:
        doc = profiles_collection.find_one({"_id": args.profile})
        if not doc:
            raise SystemExit(f"No such profile: {args.profile}")
        docs = [doc]

    rebuilt = sum(rebuild_one(analyzer, engine, doc, args.dry_run, args.api) for doc in docs)

    if args.dry_run:
        print(f"\n[dry-run] {rebuilt}/{len(docs)} profile(s) would be rebuilt. Nothing written.")
    else:
        print(f"\nRebuilt {rebuilt}/{len(docs)} profile(s).")


if __name__ == "__main__":
    main()
