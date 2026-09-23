# PRD — Hindi OSINT Entity-Level Impact Analysis

## 1. What this is

A system that ingests Hindi-language OSINT content (news, Reddit, YouTube), detects
real-world events, identifies which entities (countries, markets, sectors) each event
affects, classifies the reported impact direction per entity per source, and computes
a cross-source consensus + disagreement score. Group 18, VIT CSE-AI, guided by
Prof. Prachi Pawar.

## 2. Problem

Existing Hindi OSINT/misinformation tooling treats posts independently and doesn't
connect events to the specific entities they affect, or compare how different sources
characterize that effect. No structured way exists to see, for one event, which
entities are impacted, in which direction, and whether sources agree.

## 3. Target audience

- Primary: academic evaluators (guide, project coordinator, HoD) assessing research
  contribution and system functionality at review checkpoints.
- Secondary (conceptual, not literally built for): an OSINT/policy analyst who wants
  a real-time view of cross-entity event impact.

## 4. Explicit non-goal

This system extracts **reported/inferred** impact — what sources say or imply about
an event's effect on an entity. It does NOT forecast real-world outcomes (e.g.
predicting actual stock movement). That is a different, much harder, unvalidatable
problem for a semester timeline. Do not let scope drift toward prediction.

## 5. MVP scope (current build phase — target 40-50% of full system)

### In scope
- Ingestion: News RSS + Reddit only (PRAW, feedparser)
- Preprocessing: text cleanup + language-ID filter (Hindi / Hindi-English code-mixed)
- Event detection: IndicSBERT embeddings -> UMAP -> HDBSCAN, batch (not streaming)
- Entity extraction: pretrained IndicNER, no fine-tuning
- Entity resolution: exact-match against a curated fixed dictionary (~15-20 entities:
  countries + major Indian market indices/sectors)
- Impact classification: zero-shot NLI (pretrained multilingual NLI model)
- **Consensus/disagreement scoring: fully implemented** — this is the core research
  contribution and must not be simplified or stubbed
- Storage: PostgreSQL, schema per `architecture.md`
- Serving: FastAPI (read-only) + Streamlit dashboard

### Explicitly out of scope for this phase
- YouTube ingestion
- OCR (image text) and ASR (video transcription)
- Any model fine-tuning
- Annotated validation set / precision-recall benchmarking
- Scheduled/incremental clustering (Celery Beat, Redis Streams)
- X/Twitter integration (dropped — API cost prohibitive for a student project)
- Dashboard visual polish beyond functional

## 6. Success criteria for this phase

- End-to-end run on 2-3 pre-selected real events with known cross-entity effects,
  using a bounded pre-collected dataset (not live streaming).
- Every pipeline stage produces real output on real data — no mocked/stub outputs.
- Dashboard shows, for a selected event: entities affected, per-source impact labels,
  consensus label, disagreement score.
- Consensus/disagreement module has unit tests confirming correct behavior at
  agreement extremes (all-agree, 50/50 split, 3-way split).

## 7. Full-system vision (future phases, not this build)

YouTube + multimodal (OCR/ASR) ingestion, fine-tuned NER/impact models, annotated
benchmark dataset with precision/recall evaluation, incremental real-time clustering,
polished dashboard.

## 8. Known risk

Zero-shot NLI quality on Hindi impact statements is unverified — pilot this
(see `implementation_plan.md` Phase 5) before building the full classification
pipeline. If it underperforms, fall back to rule-based or few-shot LLM classification
rather than blocking the build.
