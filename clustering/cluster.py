"""Clustering batch job (Phase 4).

Loads embeddings from clustering/embeddings.npz.
Reduces dimensionality with UMAP.
Clusters with HDBSCAN.
Creates rows in `events` for each cluster (with representative_text)
and links posts via `event_post_map`. Noise posts (-1) are ignored.

Assumption per rules.md §1 (idempotency):
Since this is a batch pipeline without incremental streaming logic,
re-running this script wipes the existing events and event_post_map tables
and recalculates clusters from scratch.
"""

import logging
import os
import sys

import hdbscan
import numpy as np
import umap
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models import (
    Event, 
    EventEntity, 
    EventEntityConsensus, 
    EventEntityImpact, 
    EventPostMap, 
    RawPost, 
    SessionLocal
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

EMBEDDINGS_FILE = os.path.join("clustering", "embeddings.npz")

# Hyperparameters for small dataset MVP
UMAP_N_NEIGHBORS = 5
UMAP_N_COMPONENTS = 5
HDBSCAN_MIN_CLUSTER_SIZE = 3


def process_batch() -> None:
    if not os.path.exists(EMBEDDINGS_FILE):
        logger.error("Embeddings file not found: %s", EMBEDDINGS_FILE)
        sys.exit(1)

    data = np.load(EMBEDDINGS_FILE)
    post_ids = data["post_ids"]
    embeddings = data["embeddings"]

    if len(post_ids) == 0:
        logger.info("No embeddings to cluster.")
        return

    logger.info("Loaded %d embeddings.", len(post_ids))

    n_neighbors = UMAP_N_NEIGHBORS
    if len(post_ids) - 1 < UMAP_N_NEIGHBORS:
        # UMAP requires n_neighbors >= 2
        n_neighbors = max(2, min(UMAP_N_NEIGHBORS, len(post_ids) - 1))
        logger.info("Reduced UMAP n_neighbors to %d due to small dataset.", n_neighbors)

    logger.info(
        "Running UMAP (n_neighbors=%d, n_components=%d)...",
        n_neighbors,
        UMAP_N_COMPONENTS,
    )
    # Cosine metric works best for SBERT embeddings
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=UMAP_N_COMPONENTS,
        metric="cosine",
        random_state=42,
    )
    reduced_embeds = reducer.fit_transform(embeddings)

    logger.info(
        "Running HDBSCAN (min_cluster_size=%d)...", HDBSCAN_MIN_CLUSTER_SIZE
    )
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE, metric="euclidean"
    )
    labels = clusterer.fit_predict(reduced_embeds)

    unique_labels = set(labels)
    cluster_count = len(unique_labels) - (1 if -1 in unique_labels else 0)
    logger.info(
        "Found %d clusters. (Noise points: %d)",
        cluster_count,
        list(labels).count(-1),
    )

    if cluster_count == 0:
        logger.info("No clusters found (all noise or dataset too small). Exiting.")
        return

    session = SessionLocal()
    try:
        # Idempotency: wipe existing clusters and explicitly clear downstream rows
        logger.info("Clearing existing events and their downstream entities/impacts for batch re-clustering...")
        session.query(EventEntityConsensus).delete()
        session.query(EventEntityImpact).delete()
        session.query(EventEntity).delete()
        session.query(EventPostMap).delete()
        session.query(Event).delete()
        session.commit()

        # Gather texts to find representative
        posts = (
            session.query(RawPost.post_id, RawPost.cleaned_text)
            .filter(RawPost.post_id.in_(post_ids.tolist()))
            .all()
        )
        post_text_map = {p.post_id: p.cleaned_text for p in posts}

        events_created = 0
        links_created = 0

        for label in unique_labels:
            if label == -1:
                continue

            # Indices of points in this cluster
            idx_in_cluster = np.where(labels == label)[0]
            cluster_embeddings = embeddings[idx_in_cluster]
            cluster_post_ids = post_ids[idx_in_cluster]

            # Find centroid (mean vector)
            centroid = cluster_embeddings.mean(axis=0)

            # Compute cosine similarity of all cluster points to the centroid
            sims_to_centroid = cosine_similarity(
                cluster_embeddings, centroid.reshape(1, -1)
            ).flatten()

            # Find the most central post
            best_idx = np.argmax(sims_to_centroid)
            rep_post_id = cluster_post_ids[best_idx]
            rep_text = post_text_map.get(rep_post_id, "Unknown text")

            # Create Event
            event = Event(representative_text=rep_text)
            session.add(event)
            session.flush()  # flush to generate event.event_id

            # Create mapping for all posts in cluster
            for i, pid in enumerate(cluster_post_ids):
                link = EventPostMap(
                    event_id=event.event_id,
                    post_id=int(pid),
                    similarity_score=float(sims_to_centroid[i]),
                )
                session.add(link)
                links_created += 1

            events_created += 1

        session.commit()
        logger.info(
            "Successfully created %d events and %d event_post_map links.",
            events_created,
            links_created,
        )

    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Database error during clustering: %s", exc)
    finally:
        session.close()


if __name__ == "__main__":
    process_batch()
