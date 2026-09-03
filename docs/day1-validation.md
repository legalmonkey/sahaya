# Day 1 validation record

## Source provenance

The bundled excerpts are limited to the official sources below and retain their source URL in every chunk.

- MoHFW, *Universal Immunization Program — National Immunization Schedule*: <https://www.mohfw.gov.in/sites/default/files/5628564789562315.pdf>
- NHM, *Pradhan Mantri Surakshit Matritva Abhiyan*: <https://nhm.gov.in/index1.php?lang=1&level=3&lid=689&sublinkid=1308>

The corpus is a Day 1 slice only. It does not yet contain the full UIP schedule, threshold-based ANC decision support, or scheme rules; those must be added from their official primary guidelines before their respective Day 2 modules are built.

## Manual CPU validation — required after local model provisioning

With Wi-Fi disabled, launch `python app.py`, ask each question, and record latency and the source IDs returned. The expected retrieval source is listed only to assess retrieval; application code does not branch on these questions.

| Question | Expected retrieved source |
| --- | --- |
| When are oral polio vaccine doses due? | `mohfw-nis-opv-002` |
| When should Hepatitis B birth dose be given for institutional delivery? | `mohfw-nis-hepb-003` |
| When is BCG given if it was missed at birth? | `mohfw-nis-bcg-001` |
| When are DPT boosters scheduled? | `mohfw-nis-dpt-004` |
| Which day does PMSMA provide ANC care? | `nhm-pmsma-anc-002` |
| How does PMSMA identify high-risk pregnancy follow-up? | `nhm-pmsma-hrp-001` |

Record target-language quality (Hindi and selected regional languages) here after testing the actual local Gemma model. Do not claim support based on a model card alone.

## Known Day 1 blocker

No approved Gemma GGUF model or local `llama-cli` executable was present in the workspace. Consequently actual CPU-generation latency and language quality cannot be measured yet. The API refuses to generate until those artefacts are configured; it does not return a retrieval extract as an answer or use any remote service.
