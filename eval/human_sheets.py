"""
human_sheets.py — builds the two human-judgment instruments the automated
metrics cannot replace.

    python human_sheets.py --run 20260815-143022

Produces, under sheets/<run>/:
  likert_<label>.csv       response-quality ratings (relevance / coherence /
                           personalisation), one row per sampled twin turn
  identify_<label>.csv     acquaintance-anchored identification test, following
                           Guo et al.'s Individual Turing Test design
  ANSWER_KEY.csv           which identification items were real vs twin

Why the identification test is built this way
---------------------------------------------
Each item pairs the person's OWN answer to an interview question with the
twin's answer to a similar probe, shuffled, and the rater picks which is real.
A rater scoring 50% means the twin is indistinguishable; scoring near 100%
means it is obvious. Reporting distance from 50% rather than raw accuracy is
what makes the number interpretable — and note that the informative rater is
someone who KNOWS the participant. Strangers pass systems that acquaintances
see straight through, which is the central finding this design is built on.

Hand out only the likert_/identify_ files. Keep ANSWER_KEY.csv yourself.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Dict, List

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

RUNS_DIR = Path(__file__).resolve().parent / "runs"
SHEETS_DIR = Path(__file__).resolve().parent / "sheets"

LIKERT_HEADER = [
    "item",
    "prompt_shown_to_twin",
    "twin_reply",
    "relevance_1_5",
    "coherence_1_5",
    "personalisation_1_5",
    "comments",
]

IDENTIFY_HEADER = ["item", "question", "option_A", "option_B", "which_is_the_real_person_A_or_B", "confidence_1_5"]


def load_sources() -> Dict[str, dict]:
    try:
        from app.database import profiles_collection

        out = {}
        for doc in profiles_collection.find({}, {"_id": 1, "name": 1, "conversation": 1}):
            out[doc["_id"]] = {"name": doc.get("name") or doc["_id"][:8], "messages": doc.get("conversation", [])}
        if out:
            return out
    except Exception as e:
        print(f"[warn] MongoDB unavailable ({e}); falling back to backend/profiles/")

    out = {}
    legacy = _BACKEND / "profiles"
    if legacy.is_dir():
        for d in legacy.iterdir():
            conv = d / "conversation.json"
            if conv.is_file():
                name = d.name[:8]
                meta = d / "metadata.json"
                if meta.is_file():
                    name = json.loads(meta.read_text(encoding="utf-8")).get("name", name)
                out[d.name] = {
                    "name": name,
                    "messages": json.loads(conv.read_text(encoding="utf-8")).get("messages", []),
                }
    return out


def safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate human evaluation sheets.")
    parser.add_argument("--run", required=True)
    parser.add_argument("--likert-items", type=int, default=10)
    parser.add_argument("--identify-items", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42, help="fixed so sheets are reproducible")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run
    if not run_dir.is_dir():
        raise SystemExit(f"No such run: {run_dir}")

    rng = random.Random(args.seed)
    sources = load_sources()
    out_dir = SHEETS_DIR / args.run
    out_dir.mkdir(parents=True, exist_ok=True)

    answer_key: List[List] = []

    for f in sorted(run_dir.glob("*.json")):
        if f.name.startswith("_"):
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        pid = rec["profile_id"]
        src = sources.get(pid)
        if not src:
            print(f"[skip] {pid}: no source transcript")
            continue
        label = safe(src["name"])

        # ---- Likert sheet -------------------------------------------------
        turns = [
            t
            for s in rec.get("style_sessions", [])
            for t in s.get("turns", [])
            if t.get("reply") and not t.get("error")
        ]
        if not turns:
            print(f"[skip] {pid}: no twin replies")
            continue

        sampled = rng.sample(turns, min(args.likert_items, len(turns)))
        rows = [[i + 1, t["user"], t["reply"].strip(), "", "", "", ""] for i, t in enumerate(sampled)]
        path = out_dir / f"likert_{label}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(LIKERT_HEADER)
            w.writerows(rows)
        print(f"  wrote {path.name}  ({len(rows)} items)")

        # ---- Identification sheet ----------------------------------------
        real_answers = [
            m["content"].strip()
            for m in src["messages"]
            if m.get("role") == "user" and len((m.get("content") or "").split()) > 6
        ]
        questions = [m["content"].strip() for m in src["messages"] if m.get("role") == "assistant"]

        n_items = min(args.identify_items, len(real_answers), len(turns))
        if n_items < 2:
            print(f"[skip] {pid}: not enough material for an identification sheet")
            continue

        idx_real = rng.sample(range(len(real_answers)), n_items)
        idx_twin = rng.sample(range(len(turns)), n_items)

        rows = []
        for i, (ri, ti) in enumerate(zip(idx_real, idx_twin), start=1):
            real = real_answers[ri]
            twin = turns[ti]["reply"].strip()
            question = questions[ri] if ri < len(questions) else "(general conversation)"
            real_is_a = rng.random() < 0.5
            a, b = (real, twin) if real_is_a else (twin, real)
            rows.append([i, question, a, b, "", ""])
            answer_key.append([label, i, "A" if real_is_a else "B"])

        path = out_dir / f"identify_{label}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(IDENTIFY_HEADER)
            w.writerows(rows)
        print(f"  wrote {path.name}  ({len(rows)} items)")

    key_path = out_dir / "ANSWER_KEY.csv"
    with key_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["participant", "item", "real_person_is"])
        w.writerows(answer_key)

    print(f"\nSheets in {out_dir}")
    print("Hand out likert_*.csv and identify_*.csv only. Keep ANSWER_KEY.csv.\n")


if __name__ == "__main__":
    main()
