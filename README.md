# Hindi OSINT Entity Impact Pipeline

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136.3-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57.0-red.svg)
![Transformers](https://img.shields.io/badge/HuggingFace-Transformers-yellow.svg)

An end-to-end OSINT (Open Source Intelligence) pipeline designed to ingest unstructured Hindi news data, automatically group related articles into clustered "Events", extract critical Named Entities, and use zero-shot cross-lingual NLI models to determine whether the event had a **Positive**, **Negative**, or **Neutral** impact on those entities.

Finally, it calculates a **Consensus and Disagreement Score** across multiple reporting sources and visualizes the results on a Streamlit dashboard.

---

## 🏗️ Architecture & Pipeline Phases

The system operates as a sequence of idempotent batch jobs:

1. **Ingestion (`ingestion/news_rss.py`)**
   - Fetches Hindi news RSS feeds (configured in `feeds.json`).
   - Hashes payloads for strict idempotency to prevent duplicate rows.
2. **Preprocessing (`preprocessing/clean.py`)**
   - Strips HTML, normalizes whitespace.
   - Filters non-Hindi text using `langdetect`.
   - Performs efficient DB-level deduplication using SHA-256 text hashing.
3. **Event Clustering (`clustering/embed.py` & `clustering/cluster.py`)**
   - Generates sentence embeddings using `l3cube-pune/hindi-sentence-bert-nli`.
   - Reduces dimensions via **UMAP** and clusters into distinct Events via **HDBSCAN**.
   - Determines the most "representative" text for the event centroid.
4. **Entity Extraction (`entities/extract.py`)**
   - Uses `mirfan899/hindi-roberta-ner` to extract named entities.
   - Smart-resolves aliases (exact and substring matches) using a curated entity dictionary.
5. **Impact Classification (`impact/classify.py`)**
   - Runs Zero-Shot NLI via `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`.
   - Classifies the semantic impact of the event on each extracted entity (सकारात्मक / नकारात्मक / तटस्थ).
6. **Consensus Aggregation (`consensus/aggregate.py`)**
   - Aggregates labels across all sources reporting on the same event.
   - Calculates a normalized Shannon Entropy **Disagreement Score** (0 = full agreement, 1 = perfectly split opinions).
7. **Serving (`api/main.py` & `dashboard/app.py`)**
   - **FastAPI** serves the aggregated metrics.
   - **Streamlit** dashboard provides a UI to explore events, affected entities, per-source impact, and consensus tracking.

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.11**
- **Docker & Docker Compose** (for PostgreSQL)

### 2. Environment Setup

Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/Mnthn2326/hindi-osint-pipeline.git
cd hindi-osint-pipeline

python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database & Config

Start the PostgreSQL database:
```bash
docker-compose up -d
```

Copy the environment template:
```bash
cp .env.example .env
```

Apply database migrations to construct the 7-table schema:
```bash
python -m alembic upgrade head
```

---

## 🏃‍♂️ Running the Pipeline

You can run the pipeline sequentially. Every script is strictly idempotent, meaning you can run them multiple times safely without generating duplicate data.

```bash
# 1. Ingest Raw Feeds
python -m ingestion.news_rss

# 2. Preprocess & Clean
python -m preprocessing.clean

# 3. Embed & Cluster Events
python -m clustering.embed
python -m clustering.cluster

# 4. Extract Entities
python -m entities.extract

# 5. Classify Impact
python -m impact.classify

# 6. Aggregate Consensus
python -m consensus.aggregate
```

*(Note: The first time you run embedding, NER, or classification, HuggingFace will download the respective ML models to your local cache. Subsequent runs will be much faster.)*

### Running Unit Tests

The codebase includes fast, deterministic, model-free unit tests:
```bash
python -m unittest discover -s . -p "test_*.py"
```

---

## 📊 Viewing the Dashboard

Start the backend **FastAPI** server:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

In a new terminal window, start the **Streamlit** dashboard:
```bash
streamlit run dashboard/app.py
```

The dashboard will open automatically in your browser at `http://localhost:8501`.

---

## 🔒 Security & Data Integrity

- **Idempotency**: Downstream tables aggressively wipe and rebuild on re-runs via SQL `ON DELETE CASCADE` architecture.
- **N+1 Query Protections**: The API aggressively batches SQL lookups utilizing SQLAlchemy's `joinedload`.
- **XSS Protection**: All entity names and dynamic texts are explicitly sanitized using `html.escape()` prior to rendering in the Streamlit UI.
- **Error Boundaries**: Deep learning inference steps (NER, NLI) are wrapped in per-item `try/except` blocks so that a single malformed text or tensor size mismatch doesn't crash the entire batch pipeline.
