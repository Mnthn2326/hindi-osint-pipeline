# Architecture

## 1. Pipeline (linear, stage-decoupled)

```
Data Sources (News RSS)
        |
Ingestion connectors  -->  raw_posts (Postgres)
        |
Preprocessing (cleanup + language-ID filter)
        |
Event detection (IndicSBERT embed -> UMAP -> HDBSCAN)  -->  events, event_post_map
        |
Entity extraction + resolution (IndicNER + fixed dictionary)  -->  event_entities
        |
Impact classification (zero-shot NLI, per event/entity/source)  -->  event_entity_impact
        |
Consensus + disagreement aggregation  -->  event_entity_consensus
        |
FastAPI (read-only)  -->  Streamlit dashboard
```

Each stage reads from and writes to Postgres. No stage calls another stage's code
directly — they are separate scripts/jobs run in sequence (batch mode for this
phase; Celery Beat + Redis Streams scheduling is a later-phase addition, not built
now).

## 2. "User" journey (dashboard, the only interactive surface)

1. Analyst opens Streamlit dashboard.
2. Sidebar lists detected events (representative_text, date).
3. Selecting an event shows:
   a. Entities affected (from event_entities)
   b. Per-source impact label table (from event_entity_impact) — one row per
      (source, entity) pair, showing label + confidence
   c. Consensus label + disagreement score per entity (from event_entity_consensus),
      disagreement visualized as a simple bar (0 = agreement, 1 = maximal split)
4. No write actions from the dashboard — it is strictly read-only for this phase.

## 3. Folder structure

```
/ingestion/
    news_rss.py       # RSS connector
    config/feeds.json   # RSS feed URLs
/preprocessing/
    clean.py           # cleanup + language-ID filter
/clustering/
    embed.py           # IndicSBERT embedding generation
    cluster.py          # UMAP + HDBSCAN -> events
/entities/
    entity_dict.json   # curated canonical entity list + aliases
    extract.py          # NER + resolution -> event_entities
/impact/
    pilot_test.py       # zero-shot NLI pilot (run FIRST, gate for classify.py)
    classify.py          # full impact classification -> event_entity_impact
/consensus/
    aggregate.py         # consensus + disagreement -> event_entity_consensus
    test_aggregate.py    # unit tests on synthetic label distributions
/api/
    main.py              # FastAPI app
/dashboard/
    app.py               # Streamlit app
/db/
    models.py            # SQLAlchemy schema
    migrations/           # Alembic
docker-compose.yml
requirements.txt
.env.example
```

## 4. Data contracts (exact schema — see `tech_stack.md` for library versions)

| Table | Columns |
|---|---|
| `raw_posts` | post_id (PK), source_id, source_type, raw_text, cleaned_text, status, published_at, content_hash (unique) |
| `events` | event_id (PK), representative_text, created_at |
| `event_post_map` | event_id (FK), post_id (FK), similarity_score |
| `entities` | entity_id (PK), canonical_name, entity_type, aliases (array) |
| `event_entities` | event_id (FK), entity_id (FK) |
| `event_entity_impact` | event_id (FK), entity_id (FK), source_id, impact_label (enum: positive/negative/neutral/mixed), confidence |
| `event_entity_consensus` | event_id (FK), entity_id (FK), consensus_label, disagreement_score, num_sources |

## 5. Component responsibility boundaries

- **Ingestion** never interprets content — it only fetches, hashes, dedupes, stores.
- **Preprocessing** never assigns meaning — only cleans and filters by language.
- **Clustering** operates purely on embeddings — it has no knowledge of entities or
  impact.
- **Entity extraction** operates per-post/per-event text — it does not classify
  impact.
- **Impact classification** operates per (event, entity, source) triple — it does
  not aggregate across sources.
- **Consensus** is the only stage that aggregates across sources. It is pure Python
  logic with no ML model dependency.

This separation is deliberate: each stage can be tested and debugged in isolation
against its own input/output contract.

## 6. Deployment (this phase)

Single Docker Compose stack: Postgres only, as a service. All pipeline stages run
as one-off scripts (`python -m ingestion.news_rss`, etc.), not as long-running
services yet. FastAPI + Streamlit run locally via `uvicorn` / `streamlit run`
against the same Postgres instance. Full containerization of every stage is a
later-phase addition.
