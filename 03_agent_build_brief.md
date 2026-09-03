# Sahaya — Agent Build Brief

This document is the working spec for the coding agent building this project. It assumes the agent has access to the idea doc and implementation doc as context; this brief translates those into concrete build instructions, conventions, and acceptance criteria.

> **Demo scope note:** We do not have Snapdragon hardware for this build. Build everything as specified below — same model, same runtime, same RAG/data/UX design — but target **CPU execution** for on-device inference in this demo instead of the Snapdragon NPU. Anywhere this doc previously said "must run on NPU" or "verify NPU dispatch," treat that as **deferred to the next iteration** (see Section 7, new). Do not skip the runtime/model choices that keep an NPU delegate path available later — just don't block this build on having NPU hardware to verify against.

---

## 1. Non-negotiable constraints (this demo)

- **Fully offline at runtime.** No network calls anywhere in the inference or data path. If you ever find yourself reaching for an HTTP client to call a hosted LLM API, stop — that's the wrong pattern for this project.
- **All inference runs on-device, on CPU, for this demo.** Snapdragon NPU dispatch is out of scope for this build (no hardware available) and is explicitly deferred to the next iteration. Pick a runtime and model with a documented NPU delegate path (see Section 2) so that swap is a backend/config change later, not a rewrite — but do not spend build time trying to verify NPU dispatch now.
- **Grounded answers only.** Every protocol/scheme answer the app surfaces must cite which corpus chunk it came from. Never let the LLM answer from parametric knowledge alone for medical/scheme content — retrieval must actually constrain the generation. This holds regardless of inference backend.
- **⚠️ No hardcoding, no fallbacks — this is a top priority, not a style preference.** Every answer, dose calculation, risk flag, and eligibility result must come from the real pipeline (real corpus data + real retrieval + real rule logic) running live — never a canned/scripted response, a pre-written demo answer, a hardcoded lookup table standing in for retrieval, or a silent fallback path that kicks in when something fails. If any part of the pipeline fails or proves unreliable during build or testing, do not quietly patch over it with a hardcoded or scripted substitute — surface the failure, fix the actual logic, or explicitly flag it to the team as an open problem so a real fix (or a considered decision to cut scope) can be made. This applies everywhere in this doc, including the multi-turn conversation feature: it must work as a genuine live capability, not a rehearsed sequence.
- **Real data.** Scheme rules and the immunization schedule must come from actual government sources (MoHFW, NHM, UIP official schedule, scheme guideline PDFs) transcribed into the corpus — not paraphrased from third-party blogs. Flag any figure you're not confident is current rather than guessing.
- **Voice input must support regional Indian languages, not just Hindi/English.** ASHA workers and the households they visit speak the state's local language day-to-day. Pick a target set for the demo (Hindi + 2 regional languages is a realistic scope for 4 days, e.g. Tamil and one more matched to wherever you're demoing) and confirm the ASR model actually has usable accuracy in them before committing — don't assume a model "supports" a language just because it's listed in a model card. ASR runs on CPU for this demo, same as the core LLM.
- **The app must be usable by someone with low digital literacy, one-handed, mid-visit.** This isn't a nice-to-have — it's the actual usage condition. Treat every screen against that bar (see Section 4a).
- **⭐ Multi-turn conversation is a high-priority, showstopping feature — not a stretch goal.** The core pipeline must hold a short conversation buffer (last 1–2 turns) so a spoken follow-up question ("what about the second dose then?") resolves correctly against the prior exchange, live, fully offline. Build and validate this early (see Section 4, module 1) rather than bolting it on at the end — it is the single feature most likely to make the demo memorable, and it needs real testing time, not a Day 4 surprise.

## 2. Recommended stack (confirm against actual hackathon-provided hardware/SDKs before locking in)

- **Platform**: Android (native or React Native/Flutter — pick whichever the team already knows; don't burn a day learning a new framework)
- **On-device LLM runtime** — pick a runtime with a working CPU execution path today, and a documented NPU delegate path for later, in this order of preference:
  1. ONNX Runtime — use the default CPU Execution Provider for this build; the QNN Execution Provider is the same runtime's NPU path for the next iteration
  2. Google AI Edge / MediaPipe LLM Inference API — CPU/GPU delegate for this build; Qualcomm NPU delegate for the next iteration
  3. llama.cpp — CPU build for this build; QNN backend for the next iteration
- **Model**: a small instruction-tuned model in the 1–3B parameter range, INT4/INT8 quantized (e.g. a Gemma or Phi-class small model) — prioritize one with a working, documented NPU delegate path in its target runtime (even though you're running it on CPU now) over a "better" model with no such path, so the next iteration doesn't require re-choosing the model. Confirm CPU inference latency is acceptable for a live, in-person demo — this is your Day 1 acceptance bar in place of NPU dispatch verification
- **Embeddings/retrieval**: a small on-device embedding model + a simple local vector index (in-memory or SQLite-backed — don't over-engineer retrieval at this corpus size)
- **On-device ASR**: a lightweight offline speech-to-text model for the voice-input differentiator, with real (tested, not assumed) support for regional Indian languages, running on CPU. Whisper's multilingual variants (tiny/base, quantized) have reasonable coverage of major Indian languages including Hindi, Tamil, Telugu, Bengali, Marathi; Vosk has separate per-language models with narrower but lighter-weight coverage — pick based on which languages you actually need and test accuracy on real speech samples in Day 1, not just check a supported-languages list
- **Local data store**: SQLite for household/dose/visit records

If the hackathon provides a specific device/SDK, validate the above choices against it on Day 1 — for this build that means confirming CPU inference works end-to-end and is fast enough to demo live, not confirming NPU dispatch.

## 3. Data model (starting schema — extend as needed)

```
households(id, name, village, income_band, category, contact_notes)
mothers(id, household_id, age, lmp_date, anc_visit_count, risk_flags[], last_visit_date)
children(id, household_id, dob, dose_history[{vaccine, date_given, due_date}])
anc_checkups(id, mother_id, date, bp, hb_level, danger_signs[], notes)
scheme_matches(household_id, scheme_name, eligible bool, reason, next_action)
priority_queue(household_id, score, reasons[], last_computed)
```

Keep this in one shared migration file everyone builds against — do not let each track invent its own household representation.

## 4. Module build order (maps to the 3 tracks in the implementation doc)

1. **Core RAG + on-device inference pipeline (CPU-backed)** (build and validate first, standalone, before any UI depends on it)
   - Input: a text query (typed or ASR output), plus an optional short conversation buffer (last 1–2 prior turns: query + answer)
   - Process: fold the conversation buffer into the query (either by rewriting the follow-up into a standalone query, or by appending buffer text to the retrieval query — pick whichever is more reliable in testing) → embed → retrieve top-k corpus chunks → generate grounded answer via on-device LLM, running on CPU
   - Output: `{ answer, source_chunks[], confidence }` — `confidence` must be a genuinely derived value (e.g. from retrieval similarity scores and/or model output), never a static placeholder number
   - Acceptance test: 10 known protocol questions return correct, source-attributed answers fully offline, on CPU, within a latency that's acceptable to demo live. These must go through the exact same retrieval+generation code path as any other query — do not special-case or hardcode answers keyed to these specific test questions. Before Day 4, also run a handful of *unseen* protocol questions (not from this list) through the same pipeline as a check against overfitting the demo to a memorized test set
   - **⭐ Multi-turn acceptance test (high priority — showstopping feature):** for at least 5 of the 10 known protocol questions, ask a natural, context-dependent follow-up ("what about the second dose then?", "and if the child has a fever?") and confirm the pipeline returns a correct, still source-attributed answer that reflects the prior turn — fully offline, on CPU, at live-demo latency, through the same general pipeline (no hardcoded follow-up→answer mapping). Treat this as equal-priority to the single-turn test, not optional polish.
2. **Immunization module**
   - Given a child record, compute overdue/upcoming doses against the UIP schedule
   - Route free-text protocol questions through the core pipeline
   - Acceptance test: a seeded child record with a deliberately overdue dose is correctly flagged
3. **Pregnancy risk + scheme eligibility modules**
   - Risk: rule-based checklist scoring against protocol thresholds, with the "why" pulled from the core pipeline, not hardcoded strings
   - Eligibility: deterministic rule matching against structured scheme criteria (this should NOT be LLM-generated — eligibility logic should be exact/rule-based; use the LLM only to explain the result and next steps in plain language). The criteria/thresholds the rules match against must trace back to the real sourced corpus (see Section 1, "Real data") — don't independently author or estimate a scheme's income cutoff, benefit amount, or eligibility condition inside the rule engine's code separately from what's in the corpus
4. **Prioritization engine**
   - Deterministic scoring function combining: days overdue (immunization), risk flag severity (pregnancy), days since last visit, unclaimed scheme flags
   - Output ranked household list with human-readable reasons per household
5. **Voice input**
   - ASR → text → same core pipeline as typed queries; no separate logic path; CPU-backed for this demo
   - **⭐ Multi-turn UI (high priority — showstopping feature):** after an answer is spoken back, keep the mic reachable and the conversation buffer live for a short window so the worker can ask a follow-up without re-opening the ask-a-question screen; show a lightweight "still listening" cue; reset the buffer cleanly when the worker leaves the household or starts a new topic
6. **Shell UI**
   - Household list (prioritized) → household detail (flags, doses, schemes) → ask-a-question interface (voice or text)

## 4a. UX principles — the app has to be intuitive, not just functional

An ASHA worker is standing in a doorway, phone in one hand, mid-conversation with a family. Design against that, not against a desk-testing session:

- **Icon-first, minimal-text navigation.** Don't rely on dense text labels or multi-level menus — large tappable cards/icons for each module (immunization, pregnancy, schemes, ask-a-question), one tap deep from the household list wherever possible.
- **Voice as a first-class input, not a fallback.** A prominent, always-reachable mic button (not buried in a menu) — typing should be the fallback, not the primary path, given the field conditions this is built for.
- **UI text in the local language, not just the AI answers.** If the ASR/answers are localized but the buttons and labels are in English, the app still isn't usable — localize the interface chrome too, not just the model output.
- **Color/urgency coding over prose.** The prioritized household list should communicate urgency at a glance (e.g. color-coded severity) — a worker scanning a list of 20 households needs to triage in seconds, not read paragraphs.
- **No login, no setup friction.** Anything that looks like an auth screen, sync step, or onboarding wizard works against the "just works, right now" requirement — the app should open straight into the household list.
- **Answers should be short and spoken-back where possible**, not long text blocks — read the grounded answer aloud (on-device TTS is a reasonable stretch add if time allows) since reading a paragraph mid-visit isn't realistic either.
- **The multi-turn follow-up should feel like a natural continuation, not a new screen.** Don't make the worker re-tap the mic or re-navigate to ask a follow-up — the whole point of this showstopping feature is that it feels like talking to a person, not operating an app.
- **Test the UI with someone who isn't on the team**, ideally someone unfamiliar with the app, on Day 3 or 4 — the team will find their own UI intuitive by default, which is exactly why it needs an outside check before demo day.

## 5. Things to explicitly avoid

- Don't let the LLM freehand medical advice, dosage instructions, or scheme amounts without a retrieved source chunk backing it — this is a field-deployed health app in concept, treat hallucination risk as a real bug class, not a demo nitpick
- Don't build eligibility matching as an LLM free-text judgment — keep it as auditable rule logic with the LLM only used for explanation
- Don't scrape scheme/protocol data from SEO blogs for the corpus — go to official MoHFW/NHM/scheme portal sources
- Don't claim or imply NPU inference is active in this demo — it isn't, by design, because the hardware isn't available yet. Say "on-device, CPU-backed, fully offline, NPU next iteration" if asked
- Don't pick a model/runtime purely for CPU convenience if it has no documented NPU delegate path at all — that would turn "next iteration" into a re-architecture instead of a backend swap
- Multi-turn conversation must be built and tested as a genuine, general capability — it must handle a real, unrehearsed follow-up question, not a scripted or pre-written one. Do not narrow it down to a fixed set of rehearsed patterns or hardcode expected follow-ups/answers as a safety net. If testing shows it's unreliable, that is a finding to raise and address directly (fix the retrieval/context logic, or make an explicit, separate call to cut the feature) — not a reason to quietly swap in scripted responses

## 6. Definition of done for the hackathon demo

A single phone, airplane mode, can:
1. Show a prioritized household list with reasons
2. Open a household and see immunization/risk/scheme status with sources
3. Answer a spoken protocol question correctly, grounded in the real corpus
4. **⭐ Hold a live multi-turn spoken exchange** — answer a follow-up question that only makes sense in context of the first, correctly and still grounded, without the worker re-navigating the app. This is the showstopping moment the demo should be built to lead toward.
5. Visibly demonstrate fully offline, on-device inference (CPU-backed) — have a debug overlay or logged inference backend ready in case a judge asks how the app runs, so you can show it's genuinely on-device and offline, and speak clearly to the CPU-now/NPU-next roadmap rather than implying NPU is already active

## 7. Next iteration (once Snapdragon hardware is available)

- Confirm NPU dispatch on real hardware on Day 1 of that iteration — this was the original non-negotiable constraint and it's simply pushed to when hardware exists, not dropped
- Swap the runtime's execution provider/delegate from CPU to QNN (or equivalent) against the same model and the same query-in/answer-out interface built in this demo
- Verify actual NPU dispatch via profiling/logs from whichever runtime is chosen, don't assume it from API selection alone — if NPU dispatch silently falls back to CPU, treat that as build-blocking, not a footnote
- Re-benchmark latency/power against the CPU baseline from this demo before making any on-stage or public performance claims
