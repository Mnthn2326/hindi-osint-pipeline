"""Entity extraction and resolution batch job (Phase 5).

Loads entity_dict.json and syncs it to the `entities` DB table.
Uses mirfan899/hindi-roberta-ner to extract entities from event texts.
Resolves mentions to canonical entity IDs using string matching against aliases.
Saves matched (event_id, entity_id) pairs into `event_entities`.

Assumption per rules.md §1 (idempotency):
Wipes existing `event_entities` before processing batch to allow safe re-runs.
"""

import json
import logging
import os
import sys

from sqlalchemy.exc import SQLAlchemyError
from transformers import pipeline

from db.models import Entity, Event, EventEntity, EventEntityConsensus, EventEntityImpact, EventPostMap, RawPost, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

DICT_FILE = os.path.join("entities", "entity_dict.json")
MODEL_NAME = "mirfan899/hindi-roberta-ner"


def sync_entity_dict(session) -> dict:
    """Syncs entity_dict.json to DB and returns alias -> entity_id map."""
    if not os.path.exists(DICT_FILE):
        logger.error("Dictionary file not found: %s", DICT_FILE)
        sys.exit(1)

    with open(DICT_FILE, "r", encoding="utf-8") as f:
        dict_data = json.load(f)

    alias_to_id = {}

    for item in dict_data:
        canonical = item["canonical_name"]
        etype = item["entity_type"]
        aliases = item["aliases"]

        ent = session.query(Entity).filter(Entity.canonical_name == canonical).first()
        if not ent:
            ent = Entity(canonical_name=canonical, entity_type=etype, aliases=aliases)
            session.add(ent)
            session.flush()
        else:
            ent.aliases = aliases
            session.flush()

        for al in aliases:
            # Lowercase string match mapping
            alias_to_id[al.lower()] = ent.entity_id

    return alias_to_id


def resolve_entity(word: str, alias_map: dict) -> int | None:
    """Resolve an extracted word to an entity ID using exact or substring matching."""
    word_lower = word.lower()

    # 1. Exact string match on aliases
    if word_lower in alias_map:
        return alias_map[word_lower]
        
    # 2. Substring match
    # Resolves if full/partial alias appears as a substring of the extracted span or vice versa
    for alias, eid in alias_map.items():
        if word_lower in alias or alias in word_lower:
            return eid
            
    return None

def process_batch():
    session = SessionLocal()
    try:
        alias_map = sync_entity_dict(session)
        logger.info("Clearing existing event_entities and downstream impacts/consensus for batch run...")
        session.query(EventEntityConsensus).delete()
        session.query(EventEntityImpact).delete()
        session.query(EventEntity).delete()
        session.commit()
    except Exception as e:
        logger.error("Failed to sync dictionary or wipe old links: %s", e)
        session.rollback()
        sys.exit(1)

    logger.info("Loading NER model %s...", MODEL_NAME)
    try:
        # aggregation_strategy="simple" merges B- and I- tokens into whole words
        ner_pipeline = pipeline("ner", model=MODEL_NAME, aggregation_strategy="simple")
    except Exception as e:
        logger.error("Failed to load NER model: %s", e)
        sys.exit(1)

    events = session.query(Event).all()
    if not events:
        logger.info("No events found to process.")
        return

    logger.info("Extracting entities for %d events...", len(events))
    total_matches = 0

    try:
        for event in events:
            # 1. Gather all unique texts for this event
            texts = [event.representative_text]
            linked_posts = (
                session.query(RawPost.cleaned_text)
                .join(EventPostMap, EventPostMap.post_id == RawPost.post_id)
                .filter(EventPostMap.event_id == event.event_id)
                .all()
            )
            for p in linked_posts:
                if p.cleaned_text:
                    texts.append(p.cleaned_text)

            matched_entity_ids = set()

            # 2. Extract and resolve
            for text in set(texts):
                try:
                    preds = ner_pipeline(text)
                    for p in preds:
                        word = p.get("word", "").strip()
                        if not word:
                            continue

                        eid = resolve_entity(word, alias_map)
                        if eid is not None:
                            matched_entity_ids.add(eid)
                        else:
                            # Log unmatched mentions per requirements
                            logger.debug("Unmatched entity mention: '%s'", word)

                except Exception as e:
                    # Rules §3: catch per-item failures without aborting batch
                    logger.error(
                        "Inference failed for text '%s...': %s", text[:30], e
                    )
                    continue

            # 3. Store matched entities
            if matched_entity_ids:
                # Resolve names in a single query for cleaner logging
                resolved_entities = session.query(Entity.canonical_name).filter(Entity.entity_id.in_(matched_entity_ids)).all()
                resolved_names = [row[0] for row in resolved_entities]

                logger.info(
                    "Event %d matched %d entities: %s",
                    event.event_id,
                    len(matched_entity_ids),
                    resolved_names,
                )

                for eid in matched_entity_ids:
                    ee = EventEntity(event_id=event.event_id, entity_id=eid)
                    session.add(ee)
                    total_matches += 1

        session.commit()
        logger.info("Successfully mapped %d event-entity pairs.", total_matches)

    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Database error during extraction: %s", exc)
    finally:
        session.close()


if __name__ == "__main__":
    process_batch()
