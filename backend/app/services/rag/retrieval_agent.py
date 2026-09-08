"""
RetrievalAgent — the "agentic" piece of Agentic RAG.

Scope is deliberately narrow: this agent's only job is deciding whether
memory retrieval is needed for a given message and, if so, running a
small bounded search-evaluate-refine loop. It never decides what the
twin says, never calls the main chat LLM, and never runs more than
RAG_MAX_ITERATIONS search rounds — this is a retrieval helper, not an
open-ended autonomous agent.

Pipeline (mirrors the flow the RAG feature was designed around):

  question
    -> needs_retrieval()          cheap, deterministic gate; skips
                                   greetings/small talk with no memory
                                   cues, and skips entirely if this
                                   profile has no indexed memories yet
    -> understand_query()         light normalization (iteration 0);
                                   an LLM-assisted rewrite only kicks in
                                   once refinement is needed, so the
                                   common case costs no extra LLM call
    -> embed + search              MemoryStore.search (vector search,
                                   falling back to brute force)
    -> evaluate()                  keep hits clearing RAG_MIN_RELEVANCE_SCORE
    -> insufficient? refine query, search again (bounded by
       RAG_MAX_ITERATIONS) : return what was found

Any failure at any step (embedding down, Mongo down, LLM down) is
caught and treated as "no memory available" — the caller always falls
back to ReflectAI's existing (pre-RAG) behavior, never raises.

No internal reasoning/scratch text from this agent is ever returned to
the caller or surfaced to the end user — only the final memories (or
none) and small bookkeeping fields (iteration count, a short
server-log-only reason string).
"""

from __future__ import annotations

import re
from typing import List, Optional

from app import config
from app.services.rag.embedding_service import EmbeddingError, EmbeddingProvider
from app.services.rag.memory_store import MemoryStore
from app.services.rag.models import MemoryHit, RetrievalResult

# Short, low-signal messages that never warrant a memory search on their
# own — the classic "Hello" / "How are you?" case the feature spec calls
# out explicitly. Checked only when the message is also short (see
# needs_retrieval) so a longer message that happens to start with "hey"
# still gets evaluated normally.
_SMALL_TALK_PATTERNS = re.compile(
    r"^(hi|hey|hello|yo|sup|hola|howdy|hiya|good\s?(morning|afternoon|evening|night)|"
    r"how(\s+are|'s|s)\s+(you|it going|things)|what'?s\s+up|wyd|ok|okay|k|kk|lol|lmao|"
    r"haha+|thanks|thank\s+you|thx|ty|bye|goodbye|see\s+ya|nice|cool|great|nvm)[\s!.?]*$",
    re.IGNORECASE,
)

# Phrases that strongly signal the user is asking about something from
# the past — retrieval is attempted for these even if short, overriding
# the small-talk gate above.
_MEMORY_CUE_PATTERNS = re.compile(
    r"\b(remember|recall|last time|before|previously|you said|i told you|"
    r"we (talked|discussed)|what did i|when did i|do you know|remind me|"
    r"my (name|job|favorite|birthday)|earlier)\b",
    re.IGNORECASE,
)

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "do", "does", "did", "i", "you",
    "me", "my", "to", "of", "in", "on", "at", "for", "and", "or", "it", "that",
    "this", "what", "how", "please", "can", "could", "would",
}


class RetrievalAgent:
    def __init__(self, store: MemoryStore, embedding_provider: EmbeddingProvider, llm_client=None):
        self.store = store
        self.embedder = embedding_provider
        # Optional: reused OllamaClient (OpenRouter-backed, see
        # ollama_client.py) for LLM-assisted query refinement only.
        # Retrieval works fine without it — refinement just falls back
        # to a heuristic keyword-broadening rewrite.
        self.llm_client = llm_client

    # ============================================================
    # Step 1: decide whether to retrieve at all
    # ============================================================

    def needs_retrieval(self, query: str, profile_id: str) -> bool:
        query = (query or "").strip()
        if not query:
            return False

        if _MEMORY_CUE_PATTERNS.search(query):
            return True

        word_count = len(query.split())
        if word_count <= 6 and _SMALL_TALK_PATTERNS.match(query.strip()):
            return False

        # Cheap short-circuit: nothing indexed for this twin yet, so a
        # search would always come back empty — skip straight to "no".
        if self.store.count_for_profile(profile_id) == 0:
            return False

        return True

    # ============================================================
    # Step 2: query understanding (cheap, non-LLM by default)
    # ============================================================

    def understand_query(self, query: str) -> str:
        """Iteration-0 query understanding: trim + collapse whitespace.
        Deliberately not an LLM call — this runs on every retrieval, so
        keeping it free/instant matters more than a rewrite would help
        for a first pass; refine_query() below is where an LLM-assisted
        rewrite is actually worth the round trip (only reached when the
        first pass wasn't good enough)."""
        return " ".join(query.split())

    def refine_query(self, original_query: str, previous_query: str) -> str:
        """Called only when a search round came back insufficient.
        Tries an LLM-assisted broadening first (if an LLM client was
        provided); falls back to a simple stopword-stripped keyword
        query on any failure so refinement never blocks the loop."""
        if self.llm_client is not None:
            try:
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "Rewrite the user's question into a short search query "
                            "(under 12 words) that would find related personal memories "
                            "or past messages. Return ONLY the rewritten query, nothing else."
                        ),
                    },
                    {"role": "user", "content": original_query},
                ]
                rewritten = self.llm_client.chat(messages, temperature=0.2, max_tokens=40, timeout=8).strip()
                if rewritten and rewritten.lower() != previous_query.lower():
                    return rewritten
            except Exception:
                pass  # fall through to the heuristic broadening below

        tokens = [t for t in re.findall(r"[a-zA-Z0-9']+", original_query.lower()) if t not in _STOPWORDS]
        broadened = " ".join(tokens) if tokens else original_query
        if broadened.lower() == previous_query.lower():
            return original_query  # nothing left to try
        return broadened

    # ============================================================
    # Step 3: evaluate relevance
    # ============================================================

    def evaluate(self, hits: List[MemoryHit]) -> List[MemoryHit]:
        return [h for h in hits if h.score >= config.RAG_MIN_RELEVANCE_SCORE]

    # ============================================================
    # Orchestration
    # ============================================================

    def retrieve(self, user_id: str, profile_id: str, query: str) -> RetrievalResult:
        if not config.RAG_ENABLED:
            return RetrievalResult(used_retrieval=False, reason="rag_disabled")

        try:
            if not self.needs_retrieval(query, profile_id):
                return RetrievalResult(used_retrieval=False, reason="not_needed")
        except Exception as e:
            print(f"[rag] needs_retrieval check failed, skipping retrieval: {e}")
            return RetrievalResult(used_retrieval=False, reason="gate_error")

        search_query = self.understand_query(query)
        best_hits: List[MemoryHit] = []
        iterations = 0
        max_iterations = max(1, config.RAG_MAX_ITERATIONS)

        for iteration in range(max_iterations):
            iterations = iteration + 1
            try:
                query_embedding = self.embedder.embed_one(search_query)
            except EmbeddingError as e:
                print(f"[rag] embedding failed during retrieval: {e}")
                break
            except Exception as e:
                print(f"[rag] unexpected embedding failure during retrieval: {e}")
                break

            try:
                hits = self.store.search(user_id, profile_id, query_embedding, top_k=config.RAG_TOP_K)
            except Exception as e:
                print(f"[rag] memory search failed: {e}")
                break

            relevant = self.evaluate(hits)
            if relevant:
                best_hits = relevant
                break

            # Nothing cleared the relevance bar this round — below-
            # threshold hits are never returned (see evaluate()); try
            # again with a refined query if iterations remain.
            if iteration + 1 < max_iterations:
                try:
                    search_query = self.refine_query(query, search_query)
                except Exception as e:
                    print(f"[rag] query refinement failed, stopping loop: {e}")
                    break

        return RetrievalResult(
            used_retrieval=True,
            memories=best_hits[: config.RAG_TOP_K],
            iterations=iterations,
            reason="ok" if best_hits else "no_relevant_memories",
        )


_agent_singleton: RetrievalAgent | None = None


def get_retrieval_agent() -> RetrievalAgent:
    global _agent_singleton
    if _agent_singleton is None:
        from app.services.ollama_client import OllamaClient
        from app.services.rag.embedding_service import get_embedding_provider

        _agent_singleton = RetrievalAgent(MemoryStore(), get_embedding_provider(), llm_client=OllamaClient())
    return _agent_singleton
