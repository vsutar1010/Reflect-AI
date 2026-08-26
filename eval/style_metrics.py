"""
style_metrics.py — turns ReflectAI's CommunicationAnalyzer fingerprint into a
fixed-length, length-normalised feature vector, and defines the similarity
measures used in the paper's Results section.

Why this file exists
--------------------
CommunicationAnalyzer already produces 20+ surface features, but they are raw
counts nested in a dict. Raw counts are dominated by text length: a 1,200-word
interview and a 200-word chat log are not comparable on "number of commas".
Every feature below is therefore expressed as a RATE (per 100 tokens, or per
sentence, or already a ratio), so a source transcript and a twin transcript of
very different lengths can be compared directly.

Run standalone to sanity-check against a profile directory:
    python style_metrics.py --profile-dir ../backend/profiles/<uuid>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence

# Make the backend package importable so we reuse the EXACT analyzer the
# running system uses. Re-implementing the feature extraction here would mean
# the paper measures something subtly different from what the system does.
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.communication_analyzer import CommunicationAnalyzer  # noqa: E402

EPS = 1e-9

# Order matters: this is the column order of every matrix and heatmap.
FEATURE_NAMES: List[str] = [
    "avg_sentence_len",
    "avg_response_len",
    "lexical_diversity",
    "emoji_rate",
    "question_rate",
    "exclaim_rate",
    "comma_rate",
    "period_rate",
    "lowercase_ratio",
    "filler_rate",
    "shortform_rate",
    "greeting_rate",
]

# Human-readable labels for figure axes.
FEATURE_LABELS: Dict[str, str] = {
    "avg_sentence_len": "Sentence length",
    "avg_response_len": "Response length",
    "lexical_diversity": "Lexical diversity",
    "emoji_rate": "Emoji rate",
    "question_rate": "Question rate",
    "exclaim_rate": "Exclamation rate",
    "comma_rate": "Comma rate",
    "period_rate": "Period rate",
    "lowercase_ratio": "Lowercase ratio",
    "filler_rate": "Filler rate",
    "shortform_rate": "Short-form rate",
    "greeting_rate": "Greeting rate",
}


def _sum(d) -> float:
    if not isinstance(d, dict):
        return 0.0
    return float(sum(v for v in d.values() if isinstance(v, (int, float))))


def fingerprint(messages: Sequence[dict], role: str = "user") -> dict:
    """
    Runs the project's own CommunicationAnalyzer over one side of a transcript.

    `role` selects whose text is analysed. The analyzer's own message-level
    helpers (response_length, endings) only count role=="user" entries, so twin
    output must be re-labelled to "user" before analysis — otherwise those two
    features silently come back empty and the comparison is quietly wrong on
    two of twelve dimensions.
    """
    selected = [m for m in messages if m.get("role") == role and (m.get("content") or "").strip()]
    relabelled = [{"role": "user", "content": m["content"]} for m in selected]
    if not relabelled:
        return {}
    return CommunicationAnalyzer().analyze(relabelled)


def feature_vector(fp: dict) -> Dict[str, float]:
    """
    Collapses a fingerprint dict into the 12 length-normalised features.

    Returns zeros for an empty fingerprint rather than raising, so a
    participant who produced too little text shows up as an outlier in the
    results instead of crashing the analysis run.
    """
    if not fp:
        return {name: 0.0 for name in FEATURE_NAMES}

    stats = fp.get("statistics", {})
    words = max(float(stats.get("words", 0)), 1.0)
    sentences = max(float(stats.get("sentences", 0)), 1.0)

    conv = fp.get("conversation_style", {})
    style = fp.get("writing_style", {})
    patterns = fp.get("writing_patterns", {})
    vocab = fp.get("vocabulary", {})

    punct = style.get("punctuation", {})
    caps = style.get("capitalization", {})

    return {
        "avg_sentence_len": float(stats.get("average_sentence_length", 0.0)),
        "avg_response_len": float(conv.get("response_length", {}).get("average", 0.0)),
        "lexical_diversity": float(patterns.get("vocabulary", {}).get("lexical_diversity", 0.0)),
        "emoji_rate": _sum(style.get("emoji_usage", {})) / words * 100.0,
        "question_rate": float(punct.get("?", 0)) / sentences,
        "exclaim_rate": float(punct.get("!", 0)) / sentences,
        "comma_rate": float(punct.get(",", 0)) / words * 100.0,
        "period_rate": float(punct.get(".", 0)) / sentences,
        "lowercase_ratio": float(caps.get("mostly_lowercase", 0.0)),
        "filler_rate": _sum(vocab.get("fillers", {})) / words * 100.0,
        "shortform_rate": _sum(vocab.get("short_forms", {})) / words * 100.0,
        "greeting_rate": _sum(conv.get("greetings", {})) / words * 100.0,
    }


def feature_similarity(a: float, b: float) -> float:
    """
    Symmetric, scale-free similarity in [0, 1] for a single feature.

        sim = 1 - |a - b| / (|a| + |b|)

    Chosen over a raw normalised difference because features live on wildly
    different scales (sentence length ~17, lexical diversity ~0.36) and no
    global normalisation constant would be defensible across participants.
    Two zeros count as a perfect match: if neither the person nor their twin
    ever uses an emoji, that IS stylistic agreement, not missing data.
    """
    denom = abs(a) + abs(b)
    if denom < EPS:
        return 1.0
    return 1.0 - abs(a - b) / denom


def per_feature_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> Dict[str, float]:
    return {name: feature_similarity(vec_a.get(name, 0.0), vec_b.get(name, 0.0)) for name in FEATURE_NAMES}


def style_similarity_score(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """The aggregate Style Similarity Score (SSS) reported in the paper."""
    sims = per_feature_similarity(vec_a, vec_b)
    return sum(sims.values()) / len(FEATURE_NAMES)


def vocabulary_jaccard(fp_a: dict, fp_b: dict, top_k: int = 50) -> float:
    """
    Jaccard overlap of the top-k most frequent content words.

    Reported separately from SSS rather than folded into it: SSS measures HOW
    someone writes (structure, punctuation, length), this measures WHAT words
    they reach for. A twin can score well on one and badly on the other, and
    collapsing them into a single number would hide exactly that distinction.
    """
    def top_words(fp: dict) -> set:
        freq = fp.get("vocabulary", {}).get("word_frequency", {})
        return set(list(freq.keys())[:top_k])

    a, b = top_words(fp_a), top_words(fp_b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compare(source_messages: Sequence[dict], twin_messages: Sequence[dict]) -> dict:
    """
    Full comparison between a person's own words and their twin's output.

    source_messages: the interview transcript (person's answers are role=user)
    twin_messages:   a chat/voice log (twin replies are role=assistant)
    """
    fp_src = fingerprint(source_messages, role="user")
    fp_twin = fingerprint(twin_messages, role="assistant")

    vec_src = feature_vector(fp_src)
    vec_twin = feature_vector(fp_twin)

    return {
        "source_vector": vec_src,
        "twin_vector": vec_twin,
        "per_feature": per_feature_similarity(vec_src, vec_twin),
        "sss": style_similarity_score(vec_src, vec_twin),
        "vocab_jaccard": vocabulary_jaccard(fp_src, fp_twin),
        "source_words": fp_src.get("statistics", {}).get("words", 0),
        "twin_words": fp_twin.get("statistics", {}).get("words", 0),
    }


def _load(path: Path) -> List[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data.get("messages", [])
    return data


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Sanity-check style metrics on one profile directory.")
    parser.add_argument("--profile-dir", required=True, help="e.g. backend/profiles/<uuid>")
    args = parser.parse_args()

    root = Path(args.profile_dir)
    source = _load(root / "conversation.json")
    twin = _load(root / "conversations" / "default.json")

    result = compare(source, twin)

    print(f"source words: {result['source_words']}   twin words: {result['twin_words']}")
    print(f"\nSSS  = {result['sss']:.3f}")
    print(f"Jacc = {result['vocab_jaccard']:.3f}\n")
    print(f"{'feature':<20} {'source':>10} {'twin':>10} {'sim':>7}")
    print("-" * 50)
    for name in FEATURE_NAMES:
        print(
            f"{FEATURE_LABELS[name]:<20} "
            f"{result['source_vector'][name]:>10.3f} "
            f"{result['twin_vector'][name]:>10.3f} "
            f"{result['per_feature'][name]:>7.3f}"
        )


if __name__ == "__main__":
    main()
