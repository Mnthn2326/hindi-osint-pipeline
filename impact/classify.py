"""Impact classification batch job (Phase 6).

For each (event, entity) pair, predicts the impact on the entity
for all posts linked to the event using zero-shot classification.
Saves results into event_entity_impact.

Assumption per rules.md §1 (idempotency):
Wipes existing `event_entity_impact` before processing batch to allow safe re-runs.
"""

import logging
import sys

from sqlalchemy.exc import SQLAlchemyError
from transformers import pipeline

from db.models import (
    Entity,
    EventEntity,
    EventEntityImpact,
    EventPostMap,
    RawPost,
    SessionLocal,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"


def map_label(hindi_label: str) -> str:
    """Map Hindi NLI outputs to our Postgres enum."""
    if hindi_label == "सकारात्मक":
        return "positive"
    elif hindi_label == "नकारात्मक":
        return "negative"
    return "neutral"


def process_batch() -> None:
    session = SessionLocal()
    try:
        logger.info("Clearing existing event_entity_impact for batch run...")
        session.query(EventEntityImpact).delete()
        session.commit()
    except Exception as e:
        logger.error("Failed to wipe old impacts: %s", e)
        session.rollback()
        sys.exit(1)

    logger.info("Loading NLI model %s...", MODEL_NAME)
    try:
        classifier = pipeline("zero-shot-classification", model=MODEL_NAME)
    except Exception as e:
        logger.error("Failed to load NLI model: %s", e)
        sys.exit(1)

    pairs = session.query(EventEntity).all()
    if not pairs:
        logger.info("No event-entity pairs found.")
        return

    total_impacts = 0
    candidate_labels = ["सकारात्मक", "नकारात्मक", "तटस्थ"]

    logger.info("Classifying %d event-entity pairs...", len(pairs))

    try:
        for ee in pairs:
            entity = session.query(Entity).filter_by(entity_id=ee.entity_id).first()
            if not entity:
                continue

            linked_posts = (
                session.query(RawPost)
                .join(EventPostMap, EventPostMap.post_id == RawPost.post_id)
                .filter(EventPostMap.event_id == ee.event_id)
                .all()
            )

            if not linked_posts:
                continue

            template = f"इस घटना का {entity.canonical_name} पर {{}} प्रभाव है।"
            texts = [p.cleaned_text for p in linked_posts]

            try:
                # pipeline accepts lists and returns list of dicts
                results = classifier(
                    texts, candidate_labels, hypothesis_template=template
                )
            except Exception as e:
                # Catch per-item inference failures without crashing the batch
                logger.error("Inference failed for event %d: %s", ee.event_id, e)
                continue

            if isinstance(results, dict):
                results = [results]

            for post, res in zip(linked_posts, results):
                best_label = res["labels"][0]
                confidence = res["scores"][0]

                # Create the impact mapping
                impact = EventEntityImpact(
                    event_id=ee.event_id,
                    entity_id=ee.entity_id,
                    source_id=post.source_id,
                    impact_label=map_label(best_label),
                    confidence=float(confidence),
                )
                session.add(impact)
                total_impacts += 1

        session.commit()
        logger.info("Successfully saved %d impact classification rows.", total_impacts)

    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Database error during impact classification: %s", exc)
    finally:
        session.close()


if __name__ == "__main__":
    process_batch()
