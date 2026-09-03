# Sahaya — Offline AI Field Assistant for ASHA Workers
### Idea Document — iQOO Hackathon

> **Demo scope note:** This hackathon demo does not have access to Snapdragon NPU hardware. Everything below is built exactly as designed, but for this demo the on-device LLM runs on **CPU** (still fully offline, still on-device, still zero cloud calls). NPU dispatch via the Snapdragon NPU is planned as the **next iteration** once hardware access is available — the architecture, model choice, and pipeline are all built to be NPU-ready so that swap is a runtime/backend change, not a redesign.

---

## 1. One-liner

An offline, phone-first AI assistant that lets India's 1M+ ASHA workers **hold a real spoken conversation** — multi-turn, in her own regional language, with follow-up questions — to get protocol-grounded guidance and household prioritization during home visits, with all inference running on-device (CPU for this demo, Snapdragon NPU in the next iteration), zero internet required.

**Headline feature — live, multi-turn, offline conversation.** This is the centerpiece of the demo, not a Q&A add-on: the ASHA worker asks a question by voice, gets a spoken answer, then asks a natural follow-up ("what about the second dose then?") and the app keeps context and answers correctly — entirely offline, on a phone in airplane mode. Most offline-AI demos show a single query and a single answer; this shows an actual back-and-forth, which is the moment that makes people forget they're watching a hackathon demo.

## 2. The problem

India has over 1 million ASHA (Accredited Social Health Activist) workers doing door-to-door primary healthcare — tracking pregnancies, monitoring child immunization, spotting health risks, and connecting families to government schemes. This is the backbone of India's rural primary healthcare delivery.

The tools they're given don't match the environment they work in:

- Paper registers or government apps (like the ASHA app / Anmol) that assume connectivity, login, and digital literacy
- In remote villages, an ASHA worker cannot pull up a vaccination schedule, check a pregnancy risk protocol, or verify scheme eligibility mid-visit if there's no signal
- The knowledge required already exists — immunization schedules, ANC risk protocols, scheme eligibility rules — but it's spread across hundreds of pages no one can memorize or manually cross-reference for hundreds of households

The result: missed vaccination windows, overlooked high-risk pregnancies, and eligible families never enrolling in benefits they qualify for — not because the information doesn't exist, but because it isn't accessible at the point of need.

## 3. What we're building

A single offline Android app that acts as a **field companion**, structured around four things an ASHA worker needs during an actual visit:

| Module | What it does |
|---|---|
| **Immunization tracker** | Tracks each child's dose history against the Universal Immunization Programme (UIP) schedule, flags overdue/upcoming doses, answers protocol questions ("is it safe to give this dose late?") |
| **Pregnancy risk flagging** | Runs ANC checklist inputs (BP, anemia signs, danger signs, gestational age) against maternal health protocols, flags high-risk pregnancies with the *reason* it flagged them |
| **Scheme eligibility matching** | Matches a household's actual details (income, category, delivery status, employment) against real central government scheme rules and tells the ASHA worker what to tell the family, and how to help them enroll |
| **Household prioritization** | Pulls from all three above to rank the ASHA worker's household list by urgency — who to visit today, and why |
| **Multi-turn spoken conversation** ⭐ *(showstopping feature — high priority)* | The worker doesn't just ask one question — she can follow up naturally ("what about the second dose then?", "and if the child has a fever?") and the app holds context across turns, re-grounding each follow-up in the corpus and answering correctly, fully offline. This is the feature designed to be the demo's headline moment |

All five are backed by the same on-device engine: a small quantized LLM doing retrieval-augmented generation over a curated corpus of real protocols and scheme rules, running fully on-device. **For this demo, inference runs on the phone's CPU; the pipeline is built so it can be pointed at the Snapdragon NPU as a backend swap in the next iteration.** No cloud call, no login, no signal required — it works exactly where it's needed most: a village with no connectivity.

The interface is voice-first and works in regional Indian languages, not just Hindi/English — an ASHA worker can speak a question in her local language mid-visit, get a spoken-back, protocol-grounded answer, and then **keep talking**: ask a follow-up in the same conversation and get a contextually correct answer, without repeating herself or starting over. The app is deliberately designed for someone standing in a doorway with one free hand and no time to read a manual: icon-first navigation, no login or setup screens, and urgency communicated visually (not in paragraphs) on the household list.

## 4. Real government schemes covered

This is not a generic "AI healthcare chatbot" — the scheme and protocol layer is grounded in actual Indian government programs, e.g.:

- **JSY (Janani Suraksha Yojana)** — cash assistance for institutional delivery
- **PMMVY (Pradhan Mantri Matru Vandana Yojana)** — maternity benefit for pregnant/lactating women, including ASHA/Anganwadi workers themselves
- **PMSMA (Pradhan Mantri Surakshit Matritva Abhiyan)** — free ANC checkups on fixed dates
- **Ayushman Bharat – PM-JAY** — health insurance coverage
- **Mission Indradhanush / UIP** — immunization schedule and catch-up campaigns
- **Anemia Mukt Bharat** — anemia screening and supplementation protocol
- **POSHAN Abhiyaan** — nutrition tracking for children and mothers
- **RBSK (Rashtriya Bal Swasthya Karyakram)** — child health screening and defect referral

*(Before the corpus is finalized, exact eligibility figures, amounts, and current-year updates need to be pulled from official MoHFW/NHM sources rather than secondary blogs — flagged as a data-sourcing task in the implementation doc.)*

## 5. Why this fits the NPU-first theme

Most hackathon ideas bolt an LLM onto a cloud API and call it "AI." This idea is structurally offline: the *entire premise* is that it has to work with zero connectivity, so on-device inference isn't a checkbox — it's the reason the product can exist at all. Every module — protocol Q&A, risk scoring, eligibility matching — routes through the same on-device retrieval + inference pipeline, with no cloud fallback path.

**For this demo**, that pipeline runs on CPU because we don't have Snapdragon hardware in hand yet. The NPU story for the demo is architectural, not measured: the model, quantization scheme, and runtime were chosen with a documented NPU delegate path (see implementation doc) specifically so the next iteration is "point the same pipeline at QNN and verify dispatch," not a rebuild. We'll be upfront about this distinction with judges rather than implying NPU inference is active when it isn't.

## 6. Why this matters (impact framing)

- 1M+ ASHA workers, each covering ~1,000 people — a small accuracy improvement compounds across an enormous population
- Directly reduces three concrete, measurable harms: missed vaccination windows, undetected high-risk pregnancies, and unclaimed scheme benefits
- Designed for the actual literacy and connectivity conditions of the field, not a demo-friendly urban assumption

## 7. What a successful demo looks like

Walk one ASHA worker through one village on one phone, in airplane mode:
1. Open the household list — see it already ranked by urgency
2. Tap the top household — see why it's flagged (e.g., overdue Penta-3 dose + missed ANC checkup)
3. **Ask a protocol question by voice, get a spoken answer sourced from the real protocol corpus — then ask a natural follow-up and watch the app hold context and answer correctly, live, fully offline.** This multi-turn exchange is the centerpiece of the demo: it's the moment judges realize they just watched a real conversation happen with no signal and no server in sight.
4. Check scheme eligibility for that household, see which real scheme applies and why
5. All of this visibly running fully offline, on-device, on CPU inference for this demo — with the NPU-ready architecture and next-iteration plan explained as part of the pitch

That flow, done well, tells the whole story — impact, technical depth, and a credible offline-first (NPU-bound-for-next-iteration) architecture in under two minutes. The multi-turn conversation is the single moment designed to be memorable on its own — lead the pitch toward it rather than treating it as one feature among several.
