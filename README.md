# Sahaya — Day 1 foundation

This repository contains the offline-first Day 1 foundation for Sahaya. It provides:

- a shared SQLite migration for future household, maternal, child, ANC, scheme, and prioritisation modules;
- a small, cited corpus created from MoHFW/NHM source material;
- local TF-IDF vector retrieval with derived retrieval confidence;
- a typed, minimal shell app; and
- a strict `llama.cpp` CPU inference adapter. It never substitutes retrieval text or a canned answer when the local model is unavailable.

## Stack decision

The Day 1 runtime is `llama.cpp` on CPU, configured for the Gemma 4 E2B instruction-tuned QAT GGUF model. This keeps the app fully local at runtime and preserves a QNN-backend migration path for the Snapdragon iteration. The model is deliberately **not** committed to the repository.

1. Obtain the approved `google/gemma-4-E2B-it-qat-q4_0-gguf` model through the team's approved model-access workflow.
2. Build or install a local `llama-cli` binary.
3. Set `SAHAYA_MODEL_PATH` to the absolute GGUF path and optionally `SAHAYA_LLAMA_CLI` to the executable path.
4. Run `python app.py`, then visit `http://127.0.0.1:8080`.

Without those local artefacts the question endpoint returns an explicit setup error. This is intentional: answers may only be produced by the real local retrieval-plus-inference path.

## Verify the Day 1 foundation

```powershell
python -m unittest discover -s tests -v
python app.py
```

The tests validate several different protocol queries against the real local corpus and verify that confidence changes with retrieval quality. They do not impersonate LLM output. After placing the model locally, run the manual questions listed in `docs/day1-validation.md` and record latency and language-quality observations there.

## Runtime privacy

The server binds to loopback only. It makes no HTTP requests and has no cloud inference path. Source material is bundled at build time in `data/corpus.json` with its official URLs and retrieval excerpts.
