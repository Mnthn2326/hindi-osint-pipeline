# Tech Stack

Versions below reflect latest stable as of research time (Sept 2026). Pin these in
`requirements.txt`; re-verify via `pip index versions <package>` at setup time in
case newer patch releases exist — do not silently let pip pull unpinned latest
during the build, since an untested newer major version can break the pipeline
mid-sprint.

## Core Python environment

- Python 3.11 (do not use 3.13+ yet — some ML library wheels lag on newest Python)

## Ingestion

| Package | Version | Purpose |
|---|---|---|
| `feedparser` | 6.0.11 | News RSS parsing |
| `python-dotenv` | 1.0.1 | Env var loading for API keys |

## Database

| Package | Version | Purpose |
|---|---|---|
| `psycopg2-binary` | 2.9.9 | Postgres driver |
| `sqlalchemy` | 2.0.36 | ORM / schema definition |
| `alembic` | 1.14.0 | Migrations |
| PostgreSQL (Docker image) | `postgres:15` | Database server |

## NLP / ML

| Package | Version | Purpose |
|---|---|---|
| `transformers` | 5.9.0 | Model loading (NER, NLI) |
| `sentence-transformers` | 5.2.3 | IndicSBERT embeddings |
| `torch` | 2.5.1 (CPU or CUDA build per hardware) | Backend for all model inference |
| `umap-learn` | 0.5.7 | Dimensionality reduction |
| `hdbscan` | 0.8.40 | Clustering |
| `langdetect` | 1.0.9 | Language-ID filtering (fallback: `fasttext` `lid.176` if accuracy insufficient) |
| `fasttext-wheel` | 0.9.2 | Alternative/backup language-ID |

### Specific pretrained models (pull via HuggingFace Hub, pin the exact checkpoint)

| Task | Model | Notes |
|---|---|---|
| Sentence embeddings | `l3cube-pune/hindi-sentence-bert-nli` or `l3cube-pune/indic-sentence-similarity-sbert` | Confirm availability/download works before Prompt 6 |
| Hindi NER | `ai4bharat/IndicNER` | Pretrained, no fine-tuning this phase |
| Zero-shot NLI | `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` | Multilingual; pilot on Hindi text first (see `implementation_plan.md`) |

## Backend / serving

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.136.3 | REST API |
| `uvicorn` | 0.32.1 | ASGI server |
| `pydantic` | 2.9.2 | Request/response validation (bundled with FastAPI) |
| `streamlit` | 1.57.0 | Dashboard |

## Infra

| Tool | Version | Purpose |
|---|---|---|
| Docker | 27.x | Containerization |
| Docker Compose | v2 (plugin, not standalone `docker-compose` binary) | Multi-service orchestration |

## Deferred (not installed this phase — add when the corresponding phase starts)

- `celery`, `redis` — scheduled/streaming ingestion (later phase)
- `paddleocr` — OCR (later phase)
- `openai-whisper` — ASR (later phase)
- `qdrant-client` — vector DB (later phase; this phase stores embeddings as flat
  numpy files, see `architecture.md`)

## Version-pin policy

`requirements.txt` should use exact `==` pins, not `>=`, for this phase — reproducibility
across four team members' machines matters more than getting the newest patch release.
Bump pins deliberately, as a single reviewed change, not ad hoc per-teammate.
