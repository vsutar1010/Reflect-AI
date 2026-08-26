"""
analyze.py — turns raw collection output into the tables and matrices the
paper reports. Reads runs/<name>/*.json, writes results/<name>/*.csv.

    python analyze.py --run 20260815-143022
    python analyze.py --run 20260815-143022 --list-runs

Source transcripts (the person's own interview answers) are read straight from
MongoDB, because the REST API deliberately does not expose the raw `conversation`
field. This script therefore has to run on a machine that can reach the same
MONGODB_URI the backend uses.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional

import style_metrics as sm

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

RUNS_DIR = Path(__file__).resolve().parent / "runs"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_sources() -> Dict[str, dict]:
    """
    Fetches every profile's verbatim interview transcript and display name.
    Falls back to the legacy on-disk profiles/ layout if MongoDB is unreachable,
    so the pipeline still runs against an older export.
    """
    try:
        from app.database import profiles_collection

        out = {}
        for doc in profiles_collection.find({}, {"_id": 1, "name": 1, "conversation": 1}):
            out[doc["_id"]] = {
                "name": doc.get("name") or doc["_id"][:8],
                "messages": doc.get("conversation", []),
            }
        if out:
            return out
    except Exception as e:
        print(f"[warn] MongoDB unavailable ({e}); falling back to backend/profiles/")

    out = {}
    legacy = _BACKEND / "profiles"
    if legacy.is_dir():
        for d in legacy.iterdir():
            conv = d / "conversation.json"
            meta = d / "metadata.json"
            if conv.is_file():
                name = d.name[:8]
                if meta.is_file():
                    name = json.loads(meta.read_text(encoding="utf-8")).get("name", name)
                out[d.name] = {
                    "name": name,
                    "messages": json.loads(conv.read_text(encoding="utf-8")).get("messages", []),
                }
    return out


def session_to_messages(session: dict) -> List[dict]:
    """Flattens a collected session into analyzer-shaped messages."""
    messages = []
    for turn in session.get("turns", []):
        messages.append({"role": "user", "content": turn["user"]})
        if turn.get("reply"):
            messages.append({"role": "assistant", "content": turn["reply"]})
    return messages


def write_csv(path: Path, header: List[str], rows: List[List]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  wrote {path.name}  ({len(rows)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse a ReflectAI evaluation run.")
    parser.add_argument("--run", help="run directory name under runs/")
    parser.add_argument("--list-runs", action="store_true")
    args = parser.parse_args()

    if args.list_runs or not args.run:
        if not RUNS_DIR.is_dir():
            raise SystemExit("No runs/ directory yet. Run collect.py first.")
        for d in sorted(RUNS_DIR.iterdir()):
            if d.is_dir():
                print(d.name)
        return

    run_dir = RUNS_DIR / args.run
    if not run_dir.is_dir():
        raise SystemExit(f"No such run: {run_dir}")

    out_dir = RESULTS_DIR / args.run
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = load_sources()
    records = []
    for f in sorted(run_dir.glob("*.json")):
        if f.name.startswith("_"):
            continue
        records.append(json.loads(f.read_text(encoding="utf-8")))

    if not records:
        raise SystemExit(f"No profile records in {run_dir}")

    print(f"\nAnalysing {len(records)} profiles from run {args.run}\n")

    # ------------------------------------------------------------------
    # Per-profile style vectors (pooled across all cold sessions)
    # ------------------------------------------------------------------
    profile_ids: List[str] = []
    labels: List[str] = []
    source_vecs: Dict[str, Dict[str, float]] = {}
    twin_vecs: Dict[str, Dict[str, float]] = {}
    source_fps: Dict[str, dict] = {}
    twin_fps: Dict[str, dict] = {}

    for rec in records:
        pid = rec["profile_id"]
        src = sources.get(pid)
        if not src or not src["messages"]:
            print(f"[skip] {pid}: no source interview transcript found")
            continue

        pooled: List[dict] = []
        for session in rec.get("style_sessions", []):
            pooled.extend(session_to_messages(session))
        if not pooled:
            print(f"[skip] {pid}: no successful sessions")
            continue

        fp_src = sm.fingerprint(src["messages"], role="user")
        fp_twin = sm.fingerprint(pooled, role="assistant")

        profile_ids.append(pid)
        labels.append(src["name"])
        source_fps[pid] = fp_src
        twin_fps[pid] = fp_twin
        source_vecs[pid] = sm.feature_vector(fp_src)
        twin_vecs[pid] = sm.feature_vector(fp_twin)

    if not profile_ids:
        raise SystemExit("No analysable profiles — check that interviews and sessions both exist.")

    # ------------------------------------------------------------------
    # TABLE: per-feature style similarity  (Fig. heatmap 1)
    # ------------------------------------------------------------------
    rows = []
    sss_values = []
    for pid, label in zip(profile_ids, labels):
        per_feat = sm.per_feature_similarity(source_vecs[pid], twin_vecs[pid])
        sss = sm.style_similarity_score(source_vecs[pid], twin_vecs[pid])
        jac = sm.vocabulary_jaccard(source_fps[pid], twin_fps[pid])
        sss_values.append(sss)
        rows.append(
            [label, pid, round(sss, 4), round(jac, 4)]
            + [round(per_feat[n], 4) for n in sm.FEATURE_NAMES]
        )
    write_csv(
        out_dir / "style_similarity.csv",
        ["label", "profile_id", "sss", "vocab_jaccard"] + sm.FEATURE_NAMES,
        rows,
    )

    # ------------------------------------------------------------------
    # TABLE: raw feature values, person vs twin  (Fig. grouped bars)
    # ------------------------------------------------------------------
    rows = []
    for pid, label in zip(profile_ids, labels):
        for name in sm.FEATURE_NAMES:
            rows.append([label, pid, name, round(source_vecs[pid][name], 4), round(twin_vecs[pid][name], 4)])
    write_csv(out_dir / "feature_values.csv", ["label", "profile_id", "feature", "source", "twin"], rows)

    # ------------------------------------------------------------------
    # MATRIX: cross-twin discriminability  (Fig. heatmap 2 — the key result)
    # ------------------------------------------------------------------
    # M[i][j] = similarity(twin_i output, source_j). If personalisation works
    # at all, each row's maximum should sit on the diagonal: twin i should
    # resemble person i more than it resembles any other participant. This is
    # the figure that separates "the twin writes like a person" from "the twin
    # writes like THIS person", and it is the single strongest empirical claim
    # a prompt-only system of this kind can make.
    matrix_rows = []
    diagonal_wins = 0
    diag_vals, offdiag_vals = [], []

    for i, pid_i in enumerate(profile_ids):
        row = []
        for j, pid_j in enumerate(profile_ids):
            score = sm.style_similarity_score(twin_vecs[pid_i], source_vecs[pid_j])
            row.append(score)
            (diag_vals if i == j else offdiag_vals).append(score)
        if row and max(row) == row[i]:
            diagonal_wins += 1
        matrix_rows.append([labels[i]] + [round(v, 4) for v in row])

    write_csv(out_dir / "cross_matrix.csv", ["twin\\source"] + labels, matrix_rows)

    n = len(profile_ids)
    diagonal_rate = diagonal_wins / n if n else 0.0
    mean_diag = statistics.mean(diag_vals) if diag_vals else None
    # With a single participant there are no off-diagonal cells at all. Report
    # None rather than 0.0 — a zero here would read as "the twin matched other
    # people not at all", which is a strong claim the data cannot support.
    mean_off = statistics.mean(offdiag_vals) if offdiag_vals else None

    # ------------------------------------------------------------------
    # TABLE: personality consistency across cold-started sessions
    # ------------------------------------------------------------------
    rows = []
    consistency_values = []
    for rec in records:
        pid = rec["profile_id"]
        if pid not in source_vecs:
            continue
        vecs = []
        for session in rec.get("style_sessions", []):
            msgs = session_to_messages(session)
            fp = sm.fingerprint(msgs, role="assistant")
            if fp:
                vecs.append(sm.feature_vector(fp))
        if len(vecs) < 2:
            continue
        pairwise = [
            sm.style_similarity_score(vecs[a], vecs[b])
            for a in range(len(vecs))
            for b in range(a + 1, len(vecs))
        ]
        mean_pair = statistics.mean(pairwise)
        consistency_values.append(mean_pair)
        label = sources.get(pid, {}).get("name", pid[:8])
        rows.append([label, pid, len(vecs), round(mean_pair, 4), round(min(pairwise), 4), round(max(pairwise), 4)])
    write_csv(out_dir / "consistency.csv", ["label", "profile_id", "n_sessions", "mean_pairwise", "min", "max"], rows)

    # ------------------------------------------------------------------
    # TABLE: latency
    # ------------------------------------------------------------------
    rows = []
    all_latencies = []
    for rec in records:
        pid = rec["profile_id"]
        label = sources.get(pid, {}).get("name", pid[:8])
        lats = [
            t["latency_s"]
            for s in rec.get("style_sessions", [])
            for t in s.get("turns", [])
            if not t.get("error")
        ]
        if not lats:
            continue
        all_latencies.extend(lats)
        ordered = sorted(lats)
        rows.append(
            [
                label,
                pid,
                len(lats),
                round(statistics.mean(lats), 3),
                round(statistics.median(lats), 3),
                round(ordered[int(len(ordered) * 0.95) - 1], 3),
                round(min(lats), 3),
                round(max(lats), 3),
            ]
        )
    write_csv(out_dir / "latency.csv", ["label", "profile_id", "n_turns", "mean_s", "median_s", "p95_s", "min_s", "max_s"], rows)

    # ------------------------------------------------------------------
    # TABLE: contextual consistency across the 20-message window boundary
    # ------------------------------------------------------------------
    rows = []
    recalled_total = probes_total = 0
    for rec in records:
        pid = rec["profile_id"]
        label = sources.get(pid, {}).get("name", pid[:8])
        ctx = rec.get("context_session")
        if not ctx:
            continue
        for turn in ctx.get("turns", []):
            if turn.get("kind") != "probe":
                continue
            expect = (turn.get("expect") or "").lower()
            reply = (turn.get("reply") or "").lower()
            recalled = bool(expect) and expect in reply
            probes_total += 1
            recalled_total += int(recalled)
            rows.append([label, pid, turn.get("fact", ""), turn.get("user", ""), turn.get("reply", ""), int(recalled)])
    write_csv(out_dir / "context.csv", ["label", "profile_id", "fact", "probe", "reply", "recalled"], rows)

    # ------------------------------------------------------------------
    # Headline numbers for the paper
    # ------------------------------------------------------------------
    recall_rate = recalled_total / probes_total if probes_total else 0.0
    summary = {
        "run": args.run,
        "n_profiles": n,
        "style_similarity_mean": round(statistics.mean(sss_values), 4) if sss_values else None,
        "style_similarity_sd": round(statistics.stdev(sss_values), 4) if len(sss_values) > 1 else None,
        "cross_diagonal_dominance_rate": round(diagonal_rate, 4),
        "cross_mean_diagonal": round(mean_diag, 4) if mean_diag is not None else None,
        "cross_mean_offdiagonal": round(mean_off, 4) if mean_off is not None else None,
        "cross_margin": (
            round(mean_diag - mean_off, 4) if (mean_diag is not None and mean_off is not None) else None
        ),
        "consistency_mean": round(statistics.mean(consistency_values), 4) if consistency_values else None,
        "consistency_sd": round(statistics.stdev(consistency_values), 4) if len(consistency_values) > 1 else None,
        "latency_mean_s": round(statistics.mean(all_latencies), 3) if all_latencies else None,
        "latency_median_s": round(statistics.median(all_latencies), 3) if all_latencies else None,
        "context_recall_rate": round(recall_rate, 4),
        "context_probes": probes_total,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 58)
    print("HEADLINE NUMBERS  (these go straight into the paper)")
    print("=" * 58)
    for k, v in summary.items():
        print(f"  {k:<34} {v}")
    print("=" * 58)
    print(f"\nCSVs in {out_dir}\nNext:  python figures.py --run {args.run}\n")


if __name__ == "__main__":
    main()
