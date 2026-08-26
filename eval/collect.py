"""
collect.py — drives the LIVE ReflectAI backend and records everything the
Results section needs. Run this on the machine where the backend, Ollama and
MongoDB are already running.

    # every profile, 3 cold sessions each, style + latency + context
    python collect.py --all --sessions 3

    # one profile only
    python collect.py --profile 83360df2-b18f-4ffc-9c89-6794661f8ba4 --sessions 3

    # skip the long contextual run while iterating
    python collect.py --all --sessions 3 --no-context

Output: runs/<timestamp>/*.json — raw, untouched. analyze.py reads these.
Nothing here computes a metric; collection and analysis are kept separate so a
change to a metric definition never requires re-running data collection against
volunteers.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import probes

DEFAULT_API = "http://localhost:8000/api"
RUNS_DIR = Path(__file__).resolve().parent / "runs"


class APIError(RuntimeError):
    pass


def _post(base: str, path: str, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise APIError(f"POST {path} -> {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e
    except urllib.error.URLError as e:
        raise APIError(f"Cannot reach backend at {base}. Is uvicorn running? ({e})") from e


def _get(base: str, path: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(f"{base}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise APIError(f"GET {path} -> {e.code}") from e
    except urllib.error.URLError as e:
        raise APIError(f"Cannot reach backend at {base}. Is uvicorn running? ({e})") from e


# ---------------------------------------------------------------------------
# Text-chat session runner
# ---------------------------------------------------------------------------

def run_text_session(
    base: str,
    profile_id: str,
    messages: List[str],
    thread: str,
) -> Dict:
    """
    Runs one cold-started text-chat session end to end.

    A UNIQUE `thread` per session is what makes "cold-started" true. Reusing
    the default thread would load the previous session's history from MongoDB,
    so sessions would share context and any consistency measured between them
    would be inflated — the twin would be agreeing with itself by memory rather
    than by personality.
    """
    start = _post(base, "/chat/start", {"profile_id": profile_id, "thread": thread})
    session_id = start["session_id"]

    turns = []
    for msg in messages:
        t0 = time.perf_counter()
        try:
            res = _post(base, "/chat/message", {"session_id": session_id, "message": msg})
            latency = time.perf_counter() - t0
            reply = res.get("reply", "")
            error = None
        except APIError as e:
            latency = time.perf_counter() - t0
            reply = ""
            error = str(e)

        turns.append(
            {
                "user": msg,
                "reply": reply,
                "latency_s": round(latency, 4),
                "error": error,
            }
        )
        print(f"      [{latency:6.2f}s] {msg[:32]:<34} -> {reply.strip()[:48]}")

    return {
        "session_id": session_id,
        "thread": thread,
        "opening_line": start.get("message", ""),
        "turns": turns,
    }


def run_context_session(base: str, profile_id: str, thread: str) -> Dict:
    """Runs the plant -> filler -> probe script for contextual consistency."""
    script = probes.context_script()
    start = _post(base, "/chat/start", {"profile_id": profile_id, "thread": thread})
    session_id = start["session_id"]

    turns = []
    for step in script:
        t0 = time.perf_counter()
        try:
            res = _post(base, "/chat/message", {"session_id": session_id, "message": step["message"]})
            reply = res.get("reply", "")
            error = None
        except APIError as e:
            reply = ""
            error = str(e)
        latency = time.perf_counter() - t0

        turns.append(
            {
                "kind": step["kind"],
                "id": step.get("id", ""),
                "expect": step.get("expect"),
                "fact": step.get("fact"),
                "user": step["message"],
                "reply": reply,
                "latency_s": round(latency, 4),
                "error": error,
            }
        )
        if step["kind"] == "probe":
            print(f"      PROBE  {step['message'][:32]:<34} -> {reply.strip()[:48]}")

    return {"session_id": session_id, "thread": thread, "turns": turns}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Collect ReflectAI evaluation data from the live backend.")
    parser.add_argument("--api", default=DEFAULT_API, help=f"API base (default {DEFAULT_API})")
    parser.add_argument("--profile", action="append", dest="profiles", help="profile id (repeatable)")
    parser.add_argument("--all", action="store_true", help="use every profile the backend knows about")
    parser.add_argument("--sessions", type=int, default=3, help="cold sessions per profile (default 3)")
    parser.add_argument("--no-context", action="store_true", help="skip the contextual-consistency run")
    parser.add_argument("--label", default="", help="optional label for this run directory")
    args = parser.parse_args()

    if args.all:
        listing = _get(args.api, "/profiles")
        items = listing if isinstance(listing, list) else listing.get("profiles", [])
        profile_ids = [p.get("id") or p.get("_id") for p in items]
        profile_ids = [p for p in profile_ids if p]
    elif args.profiles:
        profile_ids = args.profiles
    else:
        parser.error("pass --all or at least one --profile")

    if not profile_ids:
        raise SystemExit("No profiles found. Create at least one via the analysis flow first.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = RUNS_DIR / (f"{stamp}-{args.label}" if args.label else stamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nReflectAI evaluation collection")
    print(f"  api      : {args.api}")
    print(f"  profiles : {len(profile_ids)}")
    print(f"  sessions : {args.sessions} per profile")
    print(f"  output   : {out_dir}\n")

    for idx, profile_id in enumerate(profile_ids, start=1):
        print(f"[{idx}/{len(profile_ids)}] profile {profile_id}")

        record: Dict = {"profile_id": profile_id, "style_sessions": [], "context_session": None}

        for k in range(args.sessions):
            thread = f"eval-style-{stamp}-{k}"
            print(f"   session {k + 1}/{args.sessions}  (thread={thread})")
            try:
                record["style_sessions"].append(
                    run_text_session(args.api, profile_id, probes.STYLE_PROBES, thread)
                )
            except APIError as e:
                print(f"   !! session failed: {e}")

        if not args.no_context:
            thread = f"eval-context-{stamp}"
            print(f"   contextual run  (thread={thread})")
            try:
                record["context_session"] = run_context_session(args.api, profile_id, thread)
            except APIError as e:
                print(f"   !! contextual run failed: {e}")

        (out_dir / f"{profile_id}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print()

    # Record the configuration this data was collected under. Latency numbers
    # are meaningless without the model and provider that produced them, and
    # this is the detail that is always missing when someone tries to reproduce
    # a result three weeks later.
    try:
        voice_cfg = _get(args.api, "/voice/config")
    except APIError:
        voice_cfg = {}

    (out_dir / "_manifest.json").write_text(
        json.dumps(
            {
                "collected_at": datetime.now().isoformat(),
                "api": args.api,
                "profiles": profile_ids,
                "sessions_per_profile": args.sessions,
                "style_probes": probes.STYLE_PROBES,
                "voice_config": voice_cfg,
                "note": "Record CPU/GPU, RAM and OLLAMA_MODEL manually in the paper's setup section.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Done. Now run:  python analyze.py --run {out_dir.name}")


if __name__ == "__main__":
    main()
