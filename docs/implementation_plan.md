# Implementation Plan

Checkbox roadmap for the 40-50% MVP slice defined in `prd.md`. Work through phases
in order — each phase's Verify step gates the next phase. Do not start a phase
before the previous one's checkboxes are all confirmed.

## Phase 0 — Setup

- [x] Repo + folder structure created per `architecture.md`
- [x] `docker-compose.yml` with Postgres service
- [x] `requirements.txt` pinned per `tech_stack.md`
- [x] `.env.example` with all required placeholder vars
- [x] **Verify:** `docker-compose up` starts Postgres cleanly; connect via `psql`

## Phase 1 — Database

- [x] SQLAlchemy models for all 7 tables per `architecture.md` §4
- [x] Alembic migration created and applied
- [x] **Verify:** all 7 tables exist in Postgres via `\dt`

## Phase 2 — Ingestion

- [x] News RSS connector (`ingestion/news_rss.py`) — fetch, hash, dedupe, insert
- [x] **Verify:** run against real sources; rows appear in `raw_posts`;
      rerunning does not duplicate rows

## Phase 3 — Preprocessing

- [x] `cleaned_text` and `status` columns added to `raw_posts`
- [x] `preprocessing/clean.py` — cleanup + language-ID filter (Hindi / code-mixed
      kept, others marked `skipped` not deleted)
- [x] **Verify:** count of kept vs skipped printed; 5 kept rows manually spot-checked
      for readable Devanagari text

## Phase 4 — Event detection

- [ ] `clustering/embed.py` — IndicSBERT embeddings for kept posts, stored as
      numpy files keyed by `post_id`
- [ ] **Verify (embed):** cosine similarity sanity check — manually-similar posts
      score high, unrelated posts score low
- [ ] `clustering/cluster.py` — UMAP + HDBSCAN, writes `events` and `event_post_map`
- [ ] **Verify (cluster):** run against chosen demo-event data; cluster count is
      small; representative_text per cluster is coherent on manual read

## Phase 5 — Entities

- [ ] `entities/entity_dict.json` — curated ~15-20 entity list with Hindi + English
      aliases
- [ ] `entities/extract.py` — IndicNER extraction + dictionary resolution ->
      `event_entities`
- [ ] **Verify:** entity matches per event printed and manually judged sensible
      for the chosen demo events

## Phase 6 — Impact classification (pilot-gated)

- [ ] `impact/pilot_test.py` — zero-shot NLI on 5 hand-picked (event, entity) pairs
- [ ] **GATE:** manually check all 5 predictions. If 3+ are wrong or the model
      fails on Hindi text, STOP — do not proceed to the full pipeline. Report back
      for a fallback classifier decision (rule-based or few-shot LLM) before
      continuing.
- [ ] `impact/classify.py` — full batch classification -> `event_entity_impact`
      (only after pilot gate passes)
- [ ] **Verify:** run against all demo-event data; spot-check 10 rows manually;
      confirm label distribution is not degenerate

## Phase 7 — Consensus (core contribution)

- [ ] `consensus/aggregate.py` — majority vote + entropy-based disagreement score
      -> `event_entity_consensus`
- [ ] `consensus/test_aggregate.py` — unit tests: all-agree -> score ~0, 50/50 split
      -> high score, 3-way split -> high score
- [ ] **Verify:** all unit tests pass; run against real classified data; scores
      in [0,1]; at least one entity across demo events shows meaningful disagreement

## Phase 8 — Serving

- [ ] `api/main.py` — `GET /events`, `GET /events/{event_id}/impacts`
- [ ] `dashboard/app.py` — Streamlit per `design.md` layout
- [ ] **Verify:** click through all 2-3 demo events end to end in the dashboard;
      no missing/null data at any stage

## Phase 9 — Demo readiness

- [ ] 2-3 demo events finalized and their full pipeline output reviewed once more
      end to end
- [ ] Fallback prepared: cached output / screenshots in case live run fails during
      review
- [ ] Team walkthrough rehearsed: raw posts -> event -> entities -> per-source
      labels -> consensus + disagreement -> dashboard

## Explicitly not in this plan (future phases)

YouTube ingestion, OCR/ASR, model fine-tuning, annotated evaluation set,
incremental/streaming clustering, Celery+Redis scheduling, dashboard polish.
See `prd.md` §5 for the full deferred list.
