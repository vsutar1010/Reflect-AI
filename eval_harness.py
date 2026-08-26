#!/usr/bin/env python3
"""
ReflectAI evaluation harness  --  WIRED TO THE REAL BACKEND
===========================================================
Verified against github.com/vsutar1010/Reflect-AI:

    app.services.communication_analyzer.CommunicationAnalyzer.analyze(messages)
    app.services.twin_engine.DigitalTwinEngine()            # no constructor args
    engine.build_twin_context(profile_id, force_reload=True) -> TwinContext
    engine.load_source_conversation(profile_id)             -> List[dict]
    app.adapters.ollama_adapter.build_messages(ctx)         -> List[dict]

Writes: data.tex, style.dat, consistency.dat, latency.dat, ablation.dat
(likert.dat comes from your CSV.)

Run from the paper folder with the backend venv active:

    python eval_harness.py --profile-id <id> --sessions 5

MONGODB_URI / OLLAMA_HOST / OLLAMA_MODEL are read from your backend's own
config module, so if the app runs, this runs.
"""

import argparse
import copy
import csv
import itertools
import json
import os
import statistics
import sys
import time
import urllib.request
from pathlib import Path

# ==========================================================================
# ADAPT: only this path should ever need changing
# ==========================================================================
BACKEND_PATH = os.environ.get(
    "REFLECTAI_BACKEND",
    os.path.expanduser(r"~\Reflect-AI\backend")   # Windows default
)
sys.path.insert(0, BACKEND_PATH)

# config.py calls load_dotenv(), which searches from the CURRENT directory.
# We run from the paper folder, so backend/.env would never be found and
# MONGODB_URI would be empty. Load it explicitly, before importing config.
try:
    from dotenv import load_dotenv
    _envfile = os.path.join(BACKEND_PATH, ".env")
    if os.path.exists(_envfile):
        load_dotenv(_envfile)
    else:
        print(f"[!] No .env at {_envfile} - MONGODB_URI may be unset")
except ImportError:
    print("[!] python-dotenv not installed; relying on shell environment")

try:
    from app.services.communication_analyzer import CommunicationAnalyzer
    from app.services.twin_engine import DigitalTwinEngine
    from app.adapters import ollama_adapter
    from app import config as app_config
except ImportError as e:                                    # pragma: no cover
    sys.exit(f"[!] Cannot import backend from {BACKEND_PATH}\n"
             f"    {e}\n"
             f"    Set REFLECTAI_BACKEND to your backend folder.")

OLLAMA_HOST = getattr(app_config, "OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = getattr(app_config, "OLLAMA_MODEL",
                       "mistral:7b-instruct-v0.3-q3_K_S")

# Fixed probes. Do NOT edit between runs or consistency becomes meaningless.
PROBES = [
    "Hey, how's your week been going?",
    "What do you usually do when you're stressed out?",
    "Tell me about something you're looking forward to.",
    "What's a hobby you could talk about for hours?",
    "How do you usually make a big decision?",
    "What's something you've changed your mind about recently?",
    "Describe your ideal weekend.",
    "What kind of humour do you like?",
]

FEATURES = ["Vocab", "SentLen", "Punct", "Caps", "Emoji", "Filler",
            "QRate", "RespLen"]


# ==========================================================================
def ollama_chat(messages, stream_ttft=False):
    """Returns (text, ttft_seconds, total_seconds)."""
    payload = {"model": OLLAMA_MODEL, "messages": messages,
               "stream": bool(stream_ttft)}
    req = urllib.request.Request(
        f"{OLLAMA_HOST.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft, chunks = None, []
    with urllib.request.urlopen(req, timeout=300) as resp:
        if stream_ttft:
            for raw in resp:
                if not raw.strip():
                    continue
                obj = json.loads(raw)
                piece = obj.get("message", {}).get("content", "")
                if piece and ttft is None:
                    ttft = time.perf_counter() - t0
                chunks.append(piece)
                if obj.get("done"):
                    break
            text = "".join(chunks)
        else:
            text = json.loads(resp.read()).get("message", {}).get("content", "")
    total = time.perf_counter() - t0
    return text, (ttft if ttft is not None else total), total


def as_messages(texts):
    """analyze() expects [{'role':..,'content':..}] and reads only 'user'."""
    return [{"role": "user", "content": t} for t in texts if t and t.strip()]


# ==========================================================================
# Feature vector -- keys verified against communication_fingerprint()
# ==========================================================================
def feature_vector(fp):
    stats = fp.get("statistics", {}) or {}
    ws = fp.get("writing_style", {}) or {}
    wp = fp.get("writing_patterns", {}) or {}
    vocab = fp.get("vocabulary", {}) or {}
    conv = fp.get("conversation_style", {}) or {}

    words = max(stats.get("words", 0), 1)
    sents = max(stats.get("sentences", 0), 1)

    raw = {
        "Vocab":   (wp.get("vocabulary", {}) or {}).get("lexical_diversity", 0.0),
        "SentLen": (ws.get("sentence_statistics", {}) or {}).get("average_words", 0.0) / 40.0,
        "Punct":   sum((ws.get("punctuation", {}) or {}).values()) / words,
        "Caps":    (ws.get("capitalization", {}) or {}).get("mostly_lowercase", 0.0),
        "Emoji":   sum((ws.get("emoji_usage", {}) or {}).values()) / words * 20,
        "Filler":  sum((vocab.get("fillers", {}) or {}).values()) / words * 20,
        "QRate":   (ws.get("question_style", {}) or {}).get("question_marks", 0) / sents,
        "RespLen": (conv.get("response_length", {}) or {}).get("average", 0.0) / 50.0,
    }
    return {k: max(0.0, min(1.0, float(v or 0.0))) for k, v in raw.items()}


def cosine(a, b):
    keys = sorted(set(a) | set(b))
    va = [a.get(k, 0.0) for k in keys]
    vb = [b.get(k, 0.0) for k in keys]
    num = sum(x * y for x, y in zip(va, vb))
    da = sum(x * x for x in va) ** 0.5
    db = sum(y * y for y in vb) ** 0.5
    return num / (da * db) if da and db else 0.0


# ==========================================================================
# Prompt configurations. build_messages() reads exactly two TwinContext
# fields -- identity_prompt and voice_grounding_quotes -- so these are the
# ablations the architecture actually supports.
# ==========================================================================
FINGERPRINT_MARKER = os.environ.get("FINGERPRINT_MARKER", "")


def cfg_full(ctx):
    return ollama_adapter.build_messages(ctx)


def cfg_noquotes(ctx):
    c = copy.deepcopy(ctx)
    c.voice_grounding_quotes = []
    return ollama_adapter.build_messages(c)


def cfg_nofingerprint(ctx):
    """Strips the fingerprint section from identity_prompt by heading.
    Set FINGERPRINT_MARKER to the exact heading your analyzer emits
    (open a profile's identity_prompt and copy it). Skipped if unset."""
    if not FINGERPRINT_MARKER:
        return None
    c = copy.deepcopy(ctx)
    text = c.identity_prompt
    i = text.find(FINGERPRINT_MARKER)
    if i == -1:
        return None
    j = text.find("\n\n", text.find("\n", i))
    c.identity_prompt = text[:i] + (text[j:] if j != -1 else "")
    return ollama_adapter.build_messages(c)


def cfg_generic(ctx):
    return [{"role": "system", "content": "You are a helpful assistant."}]


CONFIGS = [("Full", cfg_full), ("NoQuotes", cfg_noquotes),
           ("NoFinger", cfg_nofingerprint), ("Generic", cfg_generic)]


def run_probes(seed_messages, analyzer):
    """One cold session: seed prompt + each probe, no carry-over."""
    outputs = []
    for probe in PROBES:
        msgs = list(seed_messages) + [{"role": "user", "content": probe}]
        out, _, _ = ollama_chat(msgs)
        outputs.append(out)
    return feature_vector(analyzer.analyze(as_messages(outputs))), outputs



# ==========================================================================
# Dimension VII-D: contextual consistency across the 20-turn window boundary
# ==========================================================================
# Each probe plants a fact, buries it under filler turns until it falls out
# of the 20-turn window, then asks for it back. A miss AFTER the boundary
# that was a hit BEFORE the boundary is exactly the cost of having no
# retrieval layer -- which is what Section VII-D reports.
FACT_PROBES = [
    {"plant": "Quick thing so you know me: my dog is called Rex.",
     "ask":   "What's my dog called?",          "expect": ["rex"]},
    {"plant": "By the way, I work as a dentist in Pune.",
     "ask":   "What do I do for work?",         "expect": ["dentist"]},
    {"plant": "My younger sister Meera is getting married in December.",
     "ask":   "What's my sister's name?",       "expect": ["meera"]},
    {"plant": "I'm allergic to peanuts, pretty badly actually.",
     "ask":   "What am I allergic to?",         "expect": ["peanut"]},
    {"plant": "I drive a blue Swift, had it since college.",
     "ask":   "What car do I drive?",           "expect": ["swift"]},
]

FILLER = [
    "What's the weather like where you are?", "Do you like mornings?",
    "What's your take on long walks?", "Any good films lately?",
    "Do you cook much?", "Tea or coffee?", "Do you like winter?",
    "What music are you into?", "Do you read much?", "Early bird or night owl?",
    "Do you play any sport?", "Favourite season?", "City or countryside?",
    "Do you travel often?", "What's a good weekend for you?",
    "Do you use social media?", "Are you a planner?", "Do you like crowds?",
    "What's your comfort food?", "Do you keep a journal?",
    "Do you like surprises?", "What relaxes you?",
]


def hit(reply, expect):
    low = reply.lower()
    return any(e in low for e in expect)


def measure_contextual(engine, profile_id, window=20):
    """Returns (pre_pct, post_pct) contradiction rates."""
    ctx = engine.build_twin_context(profile_id, force_reload=True)
    seed = cfg_full(ctx)
    pre_miss = post_miss = 0

    for n, probe in enumerate(FACT_PROBES, 1):
        history = [{"role": "user", "content": probe["plant"]}]
        reply, _, _ = ollama_chat(seed + history)
        history.append({"role": "assistant", "content": reply})

        # --- ask immediately: still well inside the window
        ask = history + [{"role": "user", "content": probe["ask"]}]
        early, _, _ = ollama_chat(seed + ask)
        if not hit(early, probe["expect"]):
            pre_miss += 1

        # --- bury it past the window boundary
        for f in FILLER:
            history.append({"role": "user", "content": f})
            r, _, _ = ollama_chat(seed + history[-window:])
            history.append({"role": "assistant", "content": r})

        late_ctx = history[-window:] + [{"role": "user",
                                         "content": probe["ask"]}]
        late, _, _ = ollama_chat(seed + late_ctx)
        if not hit(late, probe["expect"]):
            post_miss += 1
        print(f"  probe {n}/{len(FACT_PROBES)}: "
              f"pre={'hit' if pre_miss==0 or n-pre_miss>0 else 'miss'} "
              f"post={'hit' if hit(late, probe['expect']) else 'miss'}")

    total = len(FACT_PROBES)
    return 100.0 * pre_miss / total, 100.0 * post_miss / total


# ==========================================================================
def read_likert(path):
    counts = {d: [0] * 5 for d in ("Relevance", "Coherence", "Personalisation")}
    raw = {d: [] for d in counts}
    if not Path(path).exists():
        print(f"  [!] {path} not found - Likert left at 0")
        return None, None, None
    with open(path, newline="", encoding="utf8") as f:
        for row in csv.DictReader(f):
            d = row["dimension"].strip().capitalize()
            if d in counts:
                r = int(row["rating"])
                counts[d][r - 1] += 1
                raw[d].append(r)
    pct, means, sds = {}, {}, {}
    for d, c in counts.items():
        tot = sum(c) or 1
        pct[d] = [round(100 * x / tot) for x in c]
        means[d] = statistics.mean(raw[d]) if raw[d] else 0.0
        sds[d] = statistics.pstdev(raw[d]) if len(raw[d]) > 1 else 0.0
    return pct, means, sds


def read_discrimination(path):
    if not Path(path).exists():
        print(f"  [!] {path} not found - detection rates left at 0")
        return None, None
    tally = {"acquaintance": [0, 0], "stranger": [0, 0]}
    with open(path, newline="", encoding="utf8") as f:
        for row in csv.DictReader(f):
            t = row["rater_type"].strip().lower()
            if t in tally:
                tally[t][1] += 1
                tally[t][0] += int(row["correct"])

    def pct(t):
        hit, tot = tally[t]
        return round(100 * hit / tot) if tot else 0
    return pct("acquaintance"), pct("stranger")


def write_dat(path, header, rows):
    with open(path, "w", encoding="utf8") as f:
        f.write(" ".join(header) + "\n")
        for r in rows:
            f.write(" ".join(str(x) for x in r) + "\n")
    print(f"  wrote {path}")


def write_data_tex(vals, path="data.tex"):
    lines = ["% AUTO-GENERATED by eval_harness.py -- do not hand-edit",
             "% Generated: " + time.strftime("%Y-%m-%d %H:%M:%S"),
             "% Model: " + OLLAMA_MODEL, "",
             r"\newif\ifplaceholder", r"\placeholderfalse", ""]
    lines += [r"\newcommand{\%s}{%s}" % (k, v) for k, v in sorted(vals.items())]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf8")
    print(f"  wrote {path} ({len(vals)} macros)")


# ==========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile-id")
    ap.add_argument("--list-profiles", action="store_true",
                    help="print available profile IDs and exit")
    ap.add_argument("--sessions", type=int, default=5)
    ap.add_argument("--latency-reps", type=int, default=10)
    ap.add_argument("--contextual", action="store_true",
                    help="run the 20-turn window probes (slow, ~30 min)")
    ap.add_argument("--likert-csv", default="likert_ratings.csv")
    ap.add_argument("--discrim-csv", default="discrimination.csv")
    args = ap.parse_args()

    if args.list_profiles:
        from app.database import profiles_collection
        docs = list(profiles_collection.find({}, {"name": 1, "created_at": 1}))
        if not docs:
            sys.exit("No profiles found. Create one in the app first.")
        print(f"\n{len(docs)} profile(s):\n")
        for d in docs:
            print(f"  {d['_id']}   {d.get('name','(unnamed)')}"
                  f"   created {d.get('created_at','?')}")
        print("\nRe-run with:  --profile-id <one of the ids above>")
        return
    if not args.profile_id:
        sys.exit("--profile-id is required (or use --list-profiles)")

    analyzer = CommunicationAnalyzer()
    engine = DigitalTwinEngine()
    vals = {}

    print(f"Model: {OLLAMA_MODEL}   Host: {OLLAMA_HOST}")

    print("[1/6] source communication fingerprint")
    source_msgs = engine.load_source_conversation(args.profile_id)
    src_vec = feature_vector(analyzer.analyze(source_msgs))
    print("  source:", {k: round(v, 3) for k, v in src_vec.items()})

    print(f"[2/6] cross-session consistency ({args.sessions} cold sessions)")
    ctx = engine.build_twin_context(args.profile_id, force_reload=True)
    seed = cfg_full(ctx)
    vectors = []
    for i in range(args.sessions):
        vec, _ = run_probes(seed, analyzer)
        vectors.append(vec)
        print(f"  session {i+1}/{args.sessions}")
    k = args.sessions
    matrix = [[cosine(vectors[r], vectors[c]) for c in range(k)]
              for r in range(k)]
    off = [matrix[r][c] for r, c in itertools.combinations(range(k), 2)]
    write_dat("consistency.dat", ["x", "y", "c"],
              [[c + 1, r + 1, round(matrix[r][c], 3)]
               for r in range(k) for c in range(k)])
    vals["ConsistencyMean"] = f"{statistics.mean(off):.2f}"
    vals["ConsistencySD"] = f"{statistics.pstdev(off):.2f}"
    vals["ConsistencyMin"] = f"{min(off):.2f}"
    vals["NSessions"] = str(k)

    print("[3/6] communication-style similarity")
    twin_vec = {f: statistics.mean(v[f] for v in vectors) for f in FEATURES}
    sim = cosine(src_vec, twin_vec)
    write_dat("style.dat", ["feature", "src", "twin"],
              [[f, round(src_vec[f], 3), round(twin_vec[f], 3)]
               for f in FEATURES])
    vals["StyleSimOverall"] = f"{sim:.2f}"

    # Control: is a generic assistant ALSO self-consistent across cold
    # sessions? If it is, consistency alone proves nothing about the
    # profile -- this baseline is what makes VII-A interpretable.
    print(f"[3b/6] generic-prompt consistency baseline ({k} sessions)")
    gen_vectors = []
    for i in range(k):
        gvec, _ = run_probes(cfg_generic(ctx), analyzer)
        gen_vectors.append(gvec)
        print(f"  generic session {i+1}/{k}")
    gen_off = [cosine(gen_vectors[r], gen_vectors[c])
               for r, c in itertools.combinations(range(k), 2)]
    vals["ConsistencyBaseline"] = f"{statistics.mean(gen_off):.2f}"
    print(f"  baseline consistency: {statistics.mean(gen_off):.3f}"
          f"  (twin: {statistics.mean(off):.3f})")

    print("[4/6] prompt-component ablation")
    abl, base_sim = {}, None
    for name, fn in CONFIGS:
        seed_msgs = fn(ctx)
        if seed_msgs is None:
            print(f"  {name}: skipped (set FINGERPRINT_MARKER to enable)")
            continue
        vec, _ = run_probes(seed_msgs, analyzer)
        s = cosine(src_vec, vec)
        abl[name] = s
        if name == "Generic":
            base_sim = s
        print(f"  {name}: style={s:.3f}")
    write_dat("ablation.dat", ["config", "style", "qual", "cons"],
              [[n, f"{abl[n]:.2f}", "0.00", "0.00"]
               for n, _ in CONFIGS if n in abl])
    full = abl.get("Full") or 1.0

    def drop(n):
        return str(round(100 * (full - abl[n]) / full)) if n in abl else "0"
    vals["AblationQuotesDrop"] = drop("NoQuotes")
    vals["AblationFingerprintDrop"] = drop("NoFinger")
    vals["StyleSimBaseline"] = f"{(base_sim or 0):.2f}"
    vals["StyleGainPct"] = (str(round(100 * (sim - base_sim) / base_sim))
                            if base_sim else "0")

    print(f"[5/6] latency ({args.latency_reps} reps)")
    ttfts, totals = [], []
    for i in range(args.latency_reps):
        msgs = list(seed) + [{"role": "user",
                              "content": PROBES[i % len(PROBES)]}]
        _, t, tot = ollama_chat(msgs, stream_ttft=True)
        ttfts.append(t)
        totals.append(tot)
    ttft, e2e = statistics.median(ttfts), statistics.median(totals)
    vals["TTFTtext"], vals["EtoEtext"] = f"{ttft:.1f}", f"{e2e:.1f}"
    for key in ("TTFTcustom", "EtoEcustom", "TTFTnative", "EtoEnative"):
        vals[key] = "0.0"
    write_dat("latency.dat", ["mode", "ttft", "e2e"],
              [["Text", f"{ttft:.1f}", f"{e2e:.1f}"],
               ["VoiceCustom", "0.0", "0.0"],
               ["VoiceNative", "0.0", "0.0"]])
    vals["LatencyReductionPct"] = "0"
    vals["UptimePct"] = "0.0"
    vals["JSONParseSuccessPct"] = "0.0"

    print("[6/6] human ratings")
    pct, means, sds = read_likert(args.likert_csv)
    dims = ("Relevance", "Coherence", "Personalisation")
    if pct:
        write_dat("likert.dat", ["dim", "r1", "r2", "r3", "r4", "r5"],
                  [[d] + pct[d] for d in dims])
        for d, key in zip(dims, ("QualRelevance", "QualCoherence",
                                 "QualPersonalisation")):
            vals[key] = f"{means[d]:.2f}"
            vals[key + "SD"] = f"{sds[d]:.2f}"
    else:
        for key in ("QualRelevance", "QualCoherence", "QualPersonalisation"):
            vals[key] = vals[key + "SD"] = "0.00"
    vals["KappaAgreement"] = "0.00"
    acq, stranger = read_discrimination(args.discrim_csv)
    vals["AcqDetectRate"] = str(acq or 0)
    vals["StrangerDetectRate"] = str(stranger or 0)
    vals["ChanceRate"] = "50"

    if args.contextual:
        print("[7/7] contextual consistency across window boundary")
        pre, post = measure_contextual(engine, args.profile_id)
        vals["ContradictionPre"] = f"{pre:.1f}"
        vals["ContradictionPost"] = f"{post:.1f}"
        vals["ContradictionDelta"] = f"{post - pre:.1f}"
        print(f"  pre={pre:.1f}%  post={post:.1f}%  delta={post-pre:.1f}pp")
    else:
        print("[7/7] contextual consistency SKIPPED (add --contextual)")
        vals["ContradictionPre"] = vals["ContradictionPost"] = "0.0"
        vals["ContradictionDelta"] = "0.0"

    vals.update({"NParticipants": "1", "NAcquaintances": "0",
                 "NTurns": str(k * len(PROBES)),
                 "NProbes": str(len(FACT_PROBES))})

    write_data_tex(vals)
    print("\nDone. Rebuild: pdflatex main && pdflatex main")


if __name__ == "__main__":
    main()
