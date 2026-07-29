# Voice Architecture Redesign — Analysis & Recommendation

## TL;DR

Your core instinct is right, and the debugging session that led here already proved it empirically: we spent an entire session getting Ollama-backed voice to not silently fail, and even "working" it means 30–90+ second replies. That isn't a voice conversation — it's a walkie-talkie with a terrible connection. Moving voice generation off local Ollama is the correct call.

But your proposed architecture has one structural flaw worth fixing before you build it: **`DigitalTwinEngine` should not grow methods that know how to format prompts for specific providers.** That's a different responsibility from loading profile data and managing memory, and conflating them will make the engine harder to test and harder to extend every time you add a third provider. The fix is a small one — pull prompt formatting into its own layer — and it also resolves your Q5 cleanly.

There's also a values-level tradeoff buried in this that's easy to wave through as "just an optimization": ReflectAI's own architecture doc frames the whole project as privacy-first, everything-local. Defaulting voice to GPT-4o-mini means every voice conversation with someone's digital twin now leaves the machine and goes to OpenAI. That may well be the right call — but it's a product decision, not just a technical one, and it deserves to be made on purpose.

Full reasoning below, then direct answers to your seven questions.

---

## 1. The real architectural principle you're reaching for

Your diagram frames the goal as "the analyzed personality should exist only once" and "DigitalTwinEngine should own all personality logic." That's almost the right principle, but it's one layer too coarse. The distinction that actually matters is:

> **One personality source of truth. Pluggable inference backend.**

Not: "one engine that also happens to know how to talk to every provider." Those are different things, and the original requirement that kicked off this whole voice feature — "one Digital Twin engine that can be used by both Ollama and Vapi" — quietly conflated them. That conflation is arguably the root cause of this whole debugging saga: it pushed the design toward "make Vapi call back into the same generation path as Ollama," which is architecturally elegant but practically means voice latency is hostage to whatever the slowest supported backend is.

Your redesign fixes the practical problem (voice no longer waits on Ollama). It doesn't yet fully fix the structural one (who's responsible for shaping data into a provider's expected format), which is why I'd push back on giving `DigitalTwinEngine` two new `build_x_prompt()` methods.

---

## 2. Where I'd push back on the proposal as drawn

### `DigitalTwinEngine` doing per-provider prompt formatting is scope creep

Look at what you're asking it to own:

```
DigitalTwinEngine responsibilities (as proposed):
  - Loading profile.json
  - Loading conversation.json
  - Loading metadata
  - Maintaining shared conversation history
  - Building an Ollama prompt
  - Building a Vapi-optimized prompt
  - Building dynamic context
  - Managing personality evolution (future)
```

The first four (and "dynamic context," which is provider-agnostic English text) are genuinely one responsibility: **own the twin's data and memory.** They're stateful, I/O-bound, and need to be loaded/cached/invalidated correctly.

"Building an Ollama prompt" and "building a Vapi-optimized prompt" are a *different* responsibility: **pure, stateless transformation of data into a specific shape another system expects.** No I/O, no caching, trivially unit-testable in isolation (you can assert "does the Vapi prompt correctly stay under N tokens" without touching disk or instantiating the engine).

Mixing these means:
- Every new provider (a bigger local model later, Claude via Vapi, ElevenLabs Conversational AI, whatever) means editing `DigitalTwinEngine`'s source directly, rather than adding a new file. Violates open/closed.
- Testing prompt-shaping logic requires spinning up the whole stateful engine.
- "Optimized for GPT-4o-mini" isn't just "the Ollama prompt, truncated." A 7B quantized model needs heavy repetition, an explicit Good/Bad example table, and blunt imperative rules because it's bad at following instructions — that's *why* your current `identity_prompt` is so long and repetitive. GPT-4o-mini needs almost none of that; it follows instructions well and repetition just burns tokens and adds latency (prompt length affects TTFT too, not just model choice). A genuinely optimized Vapi prompt is a *differently written* document, not a shorter version of the same one — which means it deserves its own construction logic, not an `if provider == "vapi"` branch bolted onto the existing builder.

**Recommendation:** introduce a `PromptBuilder` layer (answers your Q5 — see below) and keep `DigitalTwinEngine` limited to data + memory.

### "Personality evolution (future)" doesn't belong in this decision

You listed it as a future `DigitalTwinEngine` responsibility. I'd cut it from this design entirely for now — not because it's a bad idea, but because designing today's class boundaries around a feature with zero current requirements is how you end up with speculative abstractions that don't fit the feature once it actually arrives. When it's real, it's probably its own service that *writes* profile.json (a producer), not something layered onto the engine that *reads* profile.json to serve live requests (a consumer). Different responsibility, different lifecycle. Leave it out of this redesign.

### Shared memory: the "immediately visible both ways" promise needs a concrete mechanism, and it gets harder in `vapi-native` mode

This is the part of your proposal I'd flag as underspecified rather than wrong. Today, in `custom-llm` mode, *we* generate every voice reply, so we trivially know what was said the instant it happens and can append it to shared memory in the same request. If voice moves to `vapi-native`, GPT-4o-mini generates replies *inside Vapi's infrastructure* — we only learn what was said via webhook events, not through our own generation call.

Two real options, and you should pick one deliberately rather than have it fall out of implementation details:

1. **Batch sync at call end** — rely on the `end-of-call-report` webhook (which we already handle) to backfill the full transcript into shared memory once the call finishes. Simple, but "immediately visible in text chat" is false while the call is still active.
2. **Incremental sync during the call** — enable Vapi's `conversation-update` server messages and append each turn to shared memory as it happens via webhook. True to the "immediately visible" promise, but it's an actual feature to build (a webhook handler branch + idempotency handling so retried webhook deliveries don't double-append), not something "shared memory" gets for free just by existing.

Neither is hard, but the diagram as drawn implies this is automatic. It isn't — pick (1) for a first cut, note (2) as the upgrade if live-visibility matters to you.

### Voice transcripts are noisier than typed text — decide now whether that's allowed to pollute Ollama's context

STT introduces misheard words, filler, and fragments that a typed message never would. If voice turns flow into the exact same memory Ollama reads for text chat, a bad transcription can degrade text chat quality. You already tag messages with `channel: "voice"|"text"` — that's enough to *filter or de-weight* voice turns in the Ollama-facing context later if this becomes a real problem. Not a blocker, just don't assume "shared memory" means "equally trustworthy content" — it doesn't, structurally.

---

## 3. Direct answers to your questions

**1. Is this architecture sound?**
The core idea — one profile, pluggable inference per channel — is sound and is the right fix for the latency problem you're seeing. The specific class boundary (`DigitalTwinEngine` owning per-provider prompt formatting) is not; see above. Everything else about it (shared memory, thin `TextChatService`/`VoiceChatService`) is good.

**2. `vapi-native` or stay with `custom-llm`?**
`vapi-native` as the default, for this project as it exists today (single local machine, CPU-only quantized model, ngrok tunnel in the critical path). Keep `custom-llm` alive as a configurable, tested alternative — not dead code, not the default. You already have `VAPI_LLM_PROVIDER` as a config switch; that's the right mechanism, just flip the default. There are two real reasons someone would still want `custom-llm`, not just "it's slower": genuine local-only privacy requirements, and the possibility of running Ollama on real GPU hardware later where TTFT stops being the bottleneck.

**3. Is generating a dedicated Vapi prompt from `DigitalTwinEngine` the right abstraction?**
The *data* should come from `DigitalTwinEngine` (or whatever loads profile/conversation/memory). The *formatting* shouldn't live there — that's the `PromptBuilder`'s job. So: half right. Engine supplies raw ingredients (identity text, voice-grounding quotes, recent history, dynamic context); a separate builder shapes them per provider.

**4. Should `VoiceChatService` contain any personality logic at all?**
No, and your instinct here is correct. Its job is: ask for a built prompt, wire it into Vapi's assistant config shape, manage call lifecycle, handle webhooks, sync memory. It should never construct or edit prompt text itself. One thing already in the codebase does this right today: `build_opening_line()` lives on the engine, not on `VoiceChatService` — keep following that pattern.

**5. `PromptBuilder` or `TwinSessionManager`?**
`PromptBuilder`, not `TwinSessionManager`. The builder is solving a real, present problem (two providers need differently-shaped prompts from the same data) — introduce it now. A session manager would unify session-tracking across `TextChatService` and `VoiceChatService`'s separate in-memory session dicts, but nothing in this redesign requires that unification — this is a single-user local app where sessions are short-lived per page visit, and you don't have a scenario yet where one logical "session" needs to span a simultaneous text tab and live call. Introducing it now is solving a problem you don't have. Revisit if that scenario becomes real.

**6. Is there a cleaner architecture that keeps one twin while giving voice lower latency?**
Yes — it's your proposal with the `PromptBuilder` layer added:

```
                         profile.json + conversation.json
                                       │
                                       ▼
                     DigitalTwinEngine (data + shared memory)
                       loads profile, loads conversation,
                       owns conversation history, builds
                       dynamic context — NO provider knowledge
                                       │
                              get_twin_context()
                                       │
                       ┌───────────────┴───────────────┐
                       ▼                                ▼
             OllamaPromptBuilder                VapiPromptBuilder
          (verbose, repetitive, tuned      (concise, distilled, tuned
           for a small local model)          for GPT-4o-mini's token
                       │                       economics + latency)
                       ▼                                ▼
              TextChatService                   VoiceChatService
              (talks to Ollama)          (configures Vapi, handles
                                          webhooks, syncs memory)
```

`DigitalTwinEngine` never imports or knows about `OllamaClient` or Vapi's assistant schema. `TextChatService`/`VoiceChatService` never construct prompt text themselves. Each `PromptBuilder` is a pure function you can unit test with a fixture profile and no I/O.

**7. From scratch today, what would you choose?**
Same shape as above, plus three things I'd bake in from day one rather than retrofit:
- Treat "which LLM backs voice" as pure configuration from the start — never let "same engine" become a load-bearing architectural principle. The invariant that matters is "same personality source," not "same inference call."
- Design conversation memory as an append-only log with `channel` + timestamp + confidence/quality metadata from the start, so filtering noisy STT content later doesn't require a storage migration.
- Don't build `TwinSessionManager` or personality-evolution hooks speculatively. Add them when a concrete second use case demands them, not because the shape of the diagram looks incomplete without them.

---

## 4. What this redesign does and doesn't address

Worth naming since you used the word "scalability": this redesign fixes *latency* and *architectural cleanliness*, not multi-tenant scale. If you ever want multiple simultaneous users, the bigger gap is that everything is file-based storage with in-process Python dicts for session state — no DB, single process, no horizontal scaling story. That's an unrelated, much larger project. Nothing here makes it worse, but nothing here addresses it either.

Also worth naming plainly: moving voice to a hosted model is a recurring-cost decision (STT + LLM + TTS all billed per voice-minute via Vapi) where Ollama was electricity-only. Not a reason not to do it, just a real line item to be aware of.

---

## 5. The one product-level decision I'd make explicit

`architecture.md`'s own stated value prop is "everything runs locally, no data leaves the machine." Defaulting voice to GPT-4o-mini quietly breaks that for one entire feature. I'm not saying don't do it — for a real conversational experience it's clearly the right engineering tradeoff — but I'd:

- Keep it user-configurable (you already have the mechanism).
- Surface which mode is active in the UI when voice is running (e.g. "Voice replies are processed by OpenAI via Vapi" vs. "Voice runs entirely on your local Ollama"), so it's a decision the person using it can see, not one silently made for them.

That's a small addition, and it turns a potentially uncomfortable silent contradiction into a deliberate, disclosed tradeoff — which fits the same "measure twice" spirit as the rest of this redesign.
