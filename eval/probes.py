"""
probes.py — the fixed stimulus sets for every evaluation run.

These are frozen on purpose. Personality consistency is measured by comparing
independent cold-started sessions of the same twin, which is only meaningful if
every session was asked the identical questions in the identical order. Editing
this file after data collection begins invalidates any comparison across the
two halves of the dataset, so treat it as write-once per study.
"""

from __future__ import annotations

from typing import Dict, List

# ---------------------------------------------------------------------------
# CONSISTENCY / STYLE PROBES  (Sections VII-A, VII-B)
# ---------------------------------------------------------------------------
# Twelve everyday conversational openers. Deliberately NOT about the interview
# topics: asking the twin to restate what it was told measures recall, not
# style. These invite the twin to talk the way the person talks about anything.
STYLE_PROBES: List[str] = [
    "hey what's up",
    "how was your day",
    "i'm kinda stressed about exams",
    "what are you up to this weekend",
    "do you think i should take that internship",
    "lol that's so random",
    "tell me something interesting",
    "i'm bored",
    "what do you do when you can't sleep",
    "my friend is being annoying",
    "any good movie recommendations",
    "ok i gotta go, talk later",
]

# ---------------------------------------------------------------------------
# CONTEXTUAL CONSISTENCY PROBES  (Section VII-D)
# ---------------------------------------------------------------------------
# MAX_HISTORY = 20 in twin_engine.py, so a fact planted at turn 1 has fallen
# out of the context window by turn 24. PLANTS establish three facts, FILLER
# pushes past the boundary, and PROBES ask about each planted fact afterwards.
# The contradiction rate is how often the twin answers a probe inconsistently
# with what it was told — measured across the window cut-point, which is
# exactly where the draft claims consistency but has never tested it.
CONTEXT_PLANTS: List[Dict[str, str]] = [
    {
        "message": "btw i just adopted a dog, named him Rocky",
        "fact": "the user's dog is named Rocky",
        "probe": "what was my dog's name again",
        "expect": "rocky",
    },
    {
        "message": "also i'm moving to Pune next month for work",
        "fact": "the user is moving to Pune",
        "probe": "remind me which city i said i'm moving to",
        "expect": "pune",
    },
    {
        "message": "oh and my exam is on the 14th, kinda nervous",
        "fact": "the user's exam is on the 14th",
        "probe": "when did i say my exam was",
        "expect": "14",
    },
]

# 22 neutral turns — enough to push all three plants out of a 20-message window.
CONTEXT_FILLER: List[str] = [
    "so what else is new",
    "yeah fair enough",
    "how's the weather where you are",
    "i had chai this morning",
    "did you watch anything good lately",
    "hmm interesting",
    "i should probably sleep earlier",
    "traffic was terrible today",
    "what's your favourite food",
    "same honestly",
    "i've been listening to a lot of music",
    "do you like travelling",
    "that makes sense",
    "i want to learn something new",
    "coding is fun but tiring",
    "yeah true",
    "i need a break tbh",
    "what do you think about ai",
    "hah nice",
    "i'm getting hungry",
    "anyway",
    "so yeah that's about it",
]


def context_script() -> List[Dict[str, str]]:
    """
    Builds the full contextual-consistency turn script:
    plants first, then filler, then probes. Each entry is tagged with its
    kind so the analysis step knows which replies to grade.
    """
    script: List[Dict[str, str]] = []

    for i, plant in enumerate(CONTEXT_PLANTS):
        script.append({"kind": "plant", "id": str(i), "message": plant["message"]})

    for msg in CONTEXT_FILLER:
        script.append({"kind": "filler", "id": "", "message": msg})

    for i, plant in enumerate(CONTEXT_PLANTS):
        script.append(
            {
                "kind": "probe",
                "id": str(i),
                "message": plant["probe"],
                "expect": plant["expect"],
                "fact": plant["fact"],
            }
        )

    return script
