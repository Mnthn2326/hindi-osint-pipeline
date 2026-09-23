"""Embedding generation batch job (Phase 4).

Reads raw_posts where cleaned_text is not null and status='kept'.
Generates embeddings using l3cube-pune/hindi-sentence-bert-nli.
Stores embeddings in a numpy .npz file (post_ids, embeddings) for 
idempotent runs and later clustering.
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Tuple, Optional

import numpy as np

from db.models import RawPost, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_NAME = "l3cube-pune/hindi-sentence-bert-nli"
EMBEDDINGS_FILE = os.path.join("clustering", "embeddings.npz")
BATCH_SIZE = 32


def load_existing_embeddings() -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Load existing post_ids and embeddings from disk if available."""
    if os.path.exists(EMBEDDINGS_FILE):
        try:
            data = np.load(EMBEDDINGS_FILE)
            return data["post_ids"], data["embeddings"]
        except Exception as exc:
            logger.warning("Failed to load existing embeddings, starting fresh: %s", exc)
    return np.array([]), None


def save_embeddings(post_ids: np.ndarray, embeddings: np.ndarray) -> None:
    """Save post_ids and embeddings to disk."""
    Path(EMBEDDINGS_FILE).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(EMBEDDINGS_FILE, post_ids=post_ids, embeddings=embeddings)
    logger.info("Saved %d embeddings to %s", len(post_ids), EMBEDDINGS_FILE)


def process_batch() -> None:
    session = SessionLocal()
    try:
        # Fetch posts
        posts = (
            session.query(RawPost.post_id, RawPost.cleaned_text)
            .filter(RawPost.status == "kept", RawPost.cleaned_text.is_not(None))
            .all()
        )

        if not posts:
            logger.info("No kept posts found to embed.")
            return

        logger.info("Found %d kept posts.", len(posts))

        # Load existing embeddings to make job idempotent
        existing_ids, existing_embeds = load_existing_embeddings()
        existing_ids_set = set(existing_ids.tolist())

        # Filter to posts needing embedding
        to_embed = [p for p in posts if p.post_id not in existing_ids_set]

        if not to_embed:
            logger.info("All posts are already embedded.")
            if existing_embeds is None:
                logger.info("No existing embeddings and no posts to embed. Inferring model dim...")
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(MODEL_NAME)
                dim = model.get_sentence_embedding_dimension()
                existing_embeds = np.empty((0, dim))
                save_embeddings(existing_ids, existing_embeds)
            return

        logger.info("Need to generate embeddings for %d new posts.", len(to_embed))

        # Load model lazily so CLI parses quickly and dependencies aren't loaded if no-op
        logger.info("Loading model %s...", MODEL_NAME)
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)

        new_ids = []
        new_texts = []
        for p in to_embed:
            new_ids.append(p.post_id)
            new_texts.append(p.cleaned_text)

        logger.info("Encoding texts in batches of %d...", BATCH_SIZE)
        # Generate embeddings
        new_embeds = model.encode(
            new_texts, batch_size=BATCH_SIZE, show_progress_bar=True
        )

        if existing_embeds is None:
            # Infer shape from the first batch of new_embeds
            dim = new_embeds.shape[1]
            existing_embeds = np.empty((0, dim))

        # Merge with existing
        if len(existing_ids) > 0:
            if existing_embeds.shape[1] != new_embeds.shape[1]:
                logger.error(
                    "Shape mismatch: existing embeddings have dimension %d, but new model generated dimension %d.",
                    existing_embeds.shape[1], new_embeds.shape[1]
                )
                raise ValueError(
                    f"Embedding dimension mismatch: {existing_embeds.shape[1]} vs {new_embeds.shape[1]}"
                )
                
            final_ids = np.concatenate([existing_ids, new_ids])
            final_embeds = np.concatenate([existing_embeds, new_embeds])
        else:
            final_ids = np.array(new_ids)
            final_embeds = new_embeds

        save_embeddings(final_ids, final_embeds)
        logger.info("Embedding batch complete.")

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate embeddings for kept posts.")
    parser.parse_args()
    process_batch()


if __name__ == "__main__":
    main()
