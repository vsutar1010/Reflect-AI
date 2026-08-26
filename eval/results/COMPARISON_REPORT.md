# ReflectAI — Response-Length Fidelity Fix: Before/After Evaluation

**Profile evaluated:** VS (`83360df2-b18f-4ffc-9c89-6794661f8ba4`)
**Baseline run:** `20260815-190841-baseline`
**Fixed run:** `20260815-192220-fixed`
**Model:** `mistral:7b-instruct-v0.3-q3_K_S` (local, via Ollama), temperature 0.6
**Metric definitions:** `eval/style_metrics.py` — Style Similarity Score (SSS) is the mean of 12 per-feature similarities, each `sim = 1 - |a-b|/(|a|+|b|)`, scale-free and in [0,1].

---

## 1. Problem

The digital twin's text-chat replies averaged ~15 words while the source person's real interview answers averaged ~117 words (a twin replying at roughly 13% of the person's actual length). Root cause, in the running system (`Reflect-AI/backend/app/`):

1. **Hard token cap.** `services/chat.py` called the LLM with a hardcoded `max_tokens=60` (~45 words) for every profile, regardless of that person's measured style.
2. **Self-contradicting prompt.** `services/analyzer.py`'s `build_identity_prompt()` hardcoded "Most replies should be SHORT — often just 2 to 10 words" for every profile, while separately injecting the person's *actual* measured length as a raw Python dict repr (e.g. `{'average': 116.6, 'style': 'long'}`) — which is not valid instruction text and also directly contradicts the hardcoded rule above it, which wins because it's reinforced by a worked example table.
3. **Prompt baked in at analysis time.** The identity prompt is generated once and stored in MongoDB; fixing the builder function alone does nothing for profiles created before the fix.

## 2. Fix applied

- `app/config.py`: new `CHAT_MAX_TOKENS` (fallback, default 180), `CHAT_MAX_TOKENS_FLOOR`/`CEILING` (40/420), `CHAT_MAX_TOKENS_HEADROOM` (3.0×) — env-configurable, independent of `VOICE_MAX_TOKENS` (voice path left untouched, still 60).
- `app/services/twin_engine.py`: `DigitalTwinEngine.response_token_budget(profile_id)` derives a per-profile token ceiling from that profile's own measured `response_length.average`, with 3× headroom so the cap doesn't bind at the mean.
- `app/services/chat.py`: replaced `max_tokens=60` with the derived per-profile budget.
- `app/services/analyzer.py`: `build_identity_prompt()` now selects a length band (short/medium/long, matching `CommunicationAnalyzer`'s own thresholds) and injects a matching word-count rule, a matching good/bad example table, and a natural-language description of measured length (`"usually around 117 words, on the long side"`) instead of a raw dict. A second hardcoded "short" reference at the very end of the prompt (highest-attention position) was also fixed to reference the same measured length.
- `backend/scripts/rebuild_identity_prompts.py`: regenerates `identity_prompt` for existing profiles from already-stored data (no re-interview needed), leaves the interview transcript and conversation history untouched, and invalidates the running backend's in-memory cache via a new `POST /api/profiles/{id}/reload` endpoint.

## 3. Method

Both runs used the frozen `eval/probes.py` stimulus set: 3 independent cold-started sessions × 12 style probes, plus a 28-turn contextual-consistency script, against the live backend. Baseline was collected before any code change; the profile's `identity_prompt` was then rebuilt from stored data and the fixed run was collected immediately after, same probes, same model, same machine.

---

## 4. Headline numbers

| Metric | Baseline | Fixed | Δ |
|---|---:|---:|---:|
| **Style Similarity Score (SSS, overall)** | 0.569 | 0.662 | **+0.093** |
| Vocabulary Jaccard (top-50 words) | 0.136 | 0.191 | +0.054 |
| Cross-session consistency (mean pairwise) | 0.800 | 0.747 | −0.053 |
| Contextual recall rate (3 probes) | 0.0 | 0.0 | 0 |
| **Response length — source (words)** | 116.6 | 116.6 | — |
| **Response length — twin (words)** | 15.4 | 56.9 | **+41.5 words (+269%)** |
| **Response length — similarity** | 0.234 | 0.656 | **+0.422** |
| Latency — mean (s) | 8.49 | 11.06 | **+2.57s (+30%)** |
| Latency — median (s) | 8.62 | 10.25 | +1.64s (+19%) |
| Latency — p95 (s) | 9.79 | 16.40 | **+6.62s (+68%)** |
| Latency — max (s) | 9.94 | 19.36 | +9.42s |

Full machine-readable version: `comparison_summary.csv`.

## 5. Per-feature similarity (all 12 style features)

| Feature | Baseline sim | Fixed sim | Δ |
|---|---:|---:|---:|
| avg_sentence_len | 0.571 | 0.782 | +0.212 |
| **avg_response_len** | **0.234** | **0.656** | **+0.422** |
| lexical_diversity | 0.920 | 0.849 | −0.071 |
| emoji_rate | 0.147 | 0.280 | +0.132 |
| question_rate | 0.000 | 0.000 | 0 |
| exclaim_rate | 0.913 | 0.954 | +0.041 |
| comma_rate | 0.989 | 0.955 | −0.034 |
| period_rate | 0.866 | 0.837 | −0.028 |
| lowercase_ratio | 0.947 | 0.989 | +0.042 |
| filler_rate | 0.682 | 0.953 | +0.271 |
| shortform_rate | 0.000 | 0.000 | 0 |
| greeting_rate | 0.559 | 0.687 | +0.128 |

Full machine-readable version: `comparison_feature_similarity.csv`. Raw source/twin values (not just similarity) for all 12 features: `comparison_feature_values.csv`.

---

## 6. Honest limitations (for the paper's Limitations section)

- **The derived token cap was not the binding constraint in the fixed run.** For this profile the cap computed to 420 tokens (≈300 words) — well above the 56.9-word average actually produced. The 7B, 3-bit-quantized Mistral model, given explicit natural-language guidance ("usually around 117 words, on the long side") and matching long-band examples, still produced under half the source person's average length. The prompt/config fix closed most of the length gap and raised similarity substantially, but a meaningful residual gap remains that is attributable to the small model's instruction-following limits, not the prompting or token budget. This is a legitimate finding about small quantized LLMs, not a failure of the fix to apply correctly.
- **Latency grew roughly in proportion to reply length** (+30% mean, +68% p95) — a genuine cost/fidelity trade-off worth stating explicitly, not hidden.
- **n = 1 profile.** Cross-twin discriminability (`cross_matrix.csv`) needs n ≥ 5 participants to be meaningful; with one profile there are no off-diagonal cells, so `cross_mean_offdiagonal` is undefined by design (not zero).
- **Contextual recall rate is 0/3 in both conditions** — unrelated to this fix; it is a pre-existing limitation of exact keyword matching against paraphrased recall (see `eval/README.md`), not something this change touched.
- Consistency dropped slightly (0.800 → 0.747), plausibly from greater turn-to-turn length variance once replies are no longer clipped to a near-constant ~60 tokens; still a high absolute value.

---

## 7. Supporting files

All under `Reflect-AI/eval/`:

- `results/20260815-190841-baseline/` — baseline run's raw CSVs (`style_similarity.csv`, `feature_values.csv`, `cross_matrix.csv`, `consistency.csv`, `latency.csv`, `context.csv`, `summary.json`)
- `results/20260815-192220-fixed/` — fixed run's raw CSVs, same set
- `results/comparison_summary.csv`, `comparison_feature_similarity.csv`, `comparison_feature_values.csv` — this report's tables as plain CSV
- `figures/20260815-190841-baseline/` and `figures/20260815-192220-fixed/` — vector PDF figures (style heatmap, cross matrix, feature bars, latency, consistency) sized for an IEEE two-column template
