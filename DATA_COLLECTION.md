# Getting the data — command by command

Everything below runs on Windows with your backend venv active. Work from
your paper folder; the scripts reach into the backend by path.

---

## Before anything

```bat
cd C:\Users\<you>\Documents\ReflectAI_Paper
set REFLECTAI_BACKEND=C:\Users\<you>\Reflect-AI\backend
%REFLECTAI_BACKEND%\..\venv\Scripts\activate
```

Ollama must be running with your model pulled:

```bat
ollama list
ollama serve
```

**Why `REFLECTAI_BACKEND` matters.** Your `config.py` calls `load_dotenv()`,
which searches from the *current* directory. Since you're running from the
paper folder, it would never find `backend\.env` and `MONGODB_URI` would be
empty — the scripts now load that file explicitly, but they need this variable
to know where it is.

---

## Step 1 — find your profile ID (10 seconds)

```bat
python eval_harness.py --list-profiles
```

Prints every twin in your `profiles` collection with its UUID and name. Copy
the ID of the profile you want to evaluate. If nothing prints, create a twin in
the app first.

---

## Step 2 — the automatic numbers (~30–40 min, unattended)

```bat
python eval_harness.py --profile-id <paste-id-here> --sessions 5
```

This fills **16 of your 36 numbers** and rewrites four `.dat` files:

| What it measures | Fills |
|---|---|
| 5 cold sessions, pairwise agreement | Fig. 4 heatmap, ConsistencyMean/SD/Min |
| Generic-prompt control | ConsistencyBaseline |
| Source vs twin features | Fig. 5, StyleSimOverall |
| 4 prompt configurations | Fig. 8, Table III, both ablation drops |
| 10 timed text turns | Fig. 7 text bar, TTFTtext, EtoEtext |

Recompile after it finishes. Figures 4, 5, 7 (partly) and 8 plus Table III
become real.

**To also enable the fingerprint ablation**, open any profile's
`identity_prompt` in MongoDB, find the heading above the communication-style
section, and set it:

```bat
set FINGERPRINT_MARKER=HOW THEY WRITE
```

Without it, the `NoFinger` bar stays at zero and the harness says so.

---

## Step 3 — contextual consistency (~30 min, unattended)

```bat
python eval_harness.py --profile-id <id> --sessions 5 --contextual
```

Adds five scripted probes. Each plants a fact ("my dog is called Rex"), asks
for it back immediately, then buries it under 22 filler turns so it falls out
of your 20-turn window, then asks again. The gap between the two is exactly
what Section VII-D reports — the measured cost of having no retrieval layer.

Fills ContradictionPre, ContradictionPost, ContradictionDelta.

---

## Step 4 — the human study (the slow one — start now)

**Build blinded sheets:**

```bat
python make_rating_sheets.py --profile-id <id> --items 12
```

Produces `rating_sheet.csv` (12 twin responses shuffled with 12 of the
person's real interview answers, unlabelled), `answer_key.csv` (**keep this
private**), and `INSTRUCTIONS.txt`.

**Send** `rating_sheet.csv` + `INSTRUCTIONS.txt` to each rater. They fill four
columns: three Likert scores and a twin/real guess.

**Naming matters.** Returned files go in a `sheets\` folder. Put `acq` in the
filename for anyone who *knows the source person* —
`rating_sheet_acq_priya.csv` — and anything else for strangers. That single
convention is what splits AcqDetectRate from StrangerDetectRate.

**Score them:**

```bat
python make_rating_sheets.py --score sheets/*.csv
python eval_harness.py --profile-id <id> --sessions 5 --contextual
```

Fills 10 more numbers plus Fig. 6.

**How many people?** 3–5 participants, each with 1–2 acquaintances, is
defensible for a student conference as long as you report `n` honestly — the
paper already does, via `NParticipants` and `NAcquaintances`. Set those two by
hand in `data.tex` to match reality.

---

## Step 5 — voice latency (manual, needs working voice)

The harness can't place a Vapi call. Open browser devtools, time 10 turns in
each mode, take the median, and set these in `data.tex` by hand:

```
TTFTcustom  EtoEcustom  TTFTnative  EtoEnative  LatencyReductionPct
```

Also update the two voice rows in `latency.dat`.

**This is blocked on your `Call.start.error get resources validation` bug.**
That error is now on the critical path to submission, not just a missing
feature.

**If you can't fix it in time**, that's survivable — report the text channel
only, delete the two voice rows from `latency.dat`, and change the Section
VII-E sentence to say voice latency was not measured in this build. An
honestly scoped result beats a fabricated one, and reviewers accept scope
limits far more readily than they forgive invented numbers.

---

## Step 6 — three numbers you count yourself

- **UptimePct** — failed requests ÷ total, from your backend logs
- **JSONParseSuccessPct** — how often the Personality Analyzer returned valid
  JSON without hitting the regex fallback. Add a counter, or create 10 profiles
  and count.
- **KappaAgreement** — Cohen's kappa between any two raters on the same items.
  Report `0.00` and drop the clause if you only have one rater per item.

---

## Order of operations if time is short

Steps 1 and 2 tonight — that alone makes four of six dimensions real. Step 4
started tomorrow, since it depends on other people. Steps 3, 5 and 6 last.

When real data is in, `data.tex` is regenerated with `\placeholderfalse` and
the red banner disappears on its own.
