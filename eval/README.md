# ReflectAI Evaluation Harness

Everything needed to turn the Results section from "not yet measured" into real
numbers, figures and tables. Drop this folder at `Reflect-AI/eval/`.

## Install

```bash
cd Reflect-AI/eval
pip install matplotlib numpy
```

`emoji`, `pymongo` and `python-dotenv` come from the backend venv — run these
scripts with the backend venv activated so `app.services.communication_analyzer`
and `app.database` import cleanly.

## The five-minute version

```bash
# 1. backend running, Ollama running, MongoDB reachable
python collect.py --all --sessions 3          # ~25 min for 15 profiles
python analyze.py --run <printed-run-name>    # instant
python figures.py --run <printed-run-name>    # instant
python human_sheets.py --run <printed-run-name>
```

`analyze.py` prints the headline numbers. Those go directly into the paper.

---

## Data collection protocol

### Before you start

Fix these and do not change them mid-study, or the two halves of your dataset
stop being comparable:

- `OLLAMA_MODEL` (currently `mistral:7b-instruct-v0.3-q3_K_S`)
- `VAPI_LLM_PROVIDER` and `VAPI_NATIVE_MODEL`
- the machine you collect on (record CPU/GPU/RAM — latency is meaningless without it)
- the contents of `probes.py`

Write these into the paper's Experimental Setup section verbatim.

### Step 1 — recruit and build profiles (target: 15+)

Each participant completes the 10-question interview through the normal
`/analyze` flow. Two things matter:

- **They must answer as themselves, at normal length.** One-word answers give
  the analyzer nothing to fingerprint and will show up as an outlier.
- **Get consent in writing.** Ask reviewers-proof questions: can their interview
  text be quoted in a paper? Can an acquaintance read their twin's replies? A
  paper that models real people and says nothing about consent gets desk-rejected
  in the ethics check.

Record for each participant: an anonymous ID (P1, P2, …), whether they consented
to quotation, and who their nominated acquaintance is.

### Step 2 — automated collection

```bash
python collect.py --all --sessions 3
```

Runs 3 cold-started sessions × 12 probes per participant, plus a 28-turn
contextual-consistency script. Each session uses a fresh MongoDB thread, so
sessions genuinely start cold rather than inheriting each other's memory.

Budget roughly `profiles × (3 × 12 + 28) × latency`. At 15 profiles and 4 s per
turn that is about 65 minutes. Run it once, overnight if needed.

### Step 3 — human judgment

```bash
python human_sheets.py --run <run>
```

For each participant you get two sheets:

| Sheet | Who fills it | What it measures |
|---|---|---|
| `likert_<P>.csv` | 2–3 raters | relevance, coherence, personalisation (1–5) |
| `identify_<P>.csv` | the participant's **acquaintance** | can they tell twin from real? |

Get at least two independent raters per participant on the Likert sheet so you
can report inter-rater agreement — a single rater's scores are an opinion, two
raters' agreement is a measurement.

The identification test is the one reviewers will care about most. Report the
distance from 50%, not raw accuracy: 50% means indistinguishable, 100% means
obvious. Have strangers do a subset too — the stranger/acquaintance gap is a
finding in itself.

### Step 4 — analyse and plot

```bash
python analyze.py --run <run>
python figures.py --run <run>
```

---

## What each metric measures, and its honest limitation

| Metric | File | Limitation to state in the paper |
|---|---|---|
| Style Similarity Score (SSS) | `style_similarity.csv` | surface features only; says nothing about meaning |
| Vocabulary Jaccard | `style_similarity.csv` | top-50 words; sensitive to topic drift between interview and probes |
| Cross-twin discriminability | `cross_matrix.csv` | needs n ≥ 5 to mean anything; with n = 1 there is no off-diagonal |
| Cross-session consistency | `consistency.csv` | consistency ≠ accuracy; a twin can be consistently wrong |
| Contextual recall | `context.csv` | keyword matching, not semantic — undercounts paraphrased recall |
| Latency | `latency.csv` | hardware-specific; useless without the machine spec |

Put these in the Limitations section. Reviewers trust a paper that names its own
weaknesses far more than one that does not.

## Figure → paper mapping

| Figure | Section | What it shows |
|---|---|---|
| `fig_cross_matrix.pdf` | Results | **the key result** — twins match their own source more than others' |
| `fig_style_heatmap.pdf` | Results | which style features transfer well and which fail |
| `fig_feature_bars.pdf` | Results | person vs twin, aggregated |
| `fig_consistency.pdf` | Results | stability across cold-started sessions |
| `fig_latency.pdf` | Results | practical responsiveness |

## Reproducibility

`collect.py` writes `_manifest.json` into every run: timestamp, API base, probe
set, voice configuration. Keep run directories — if a reviewer asks how a number
was produced, the answer is in there. Add the hardware spec by hand.

## Ethics checklist

- [ ] Written consent from every participant, covering quotation and acquaintance review
- [ ] Anonymous IDs in all published tables and figures — never real names
- [ ] No verbatim interview quotes in the paper without that participant's explicit sign-off
- [ ] Participants can withdraw and have their profile and conversations deleted
- [ ] Institutional ethics approval if your department requires it for human-subject work
