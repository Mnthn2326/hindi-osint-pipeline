"""Consensus aggregation logic (Phase 7).

Computes majority vote and disagreement score (normalized entropy)
for impact predictions.
"""

import logging
import math
import sys
from collections import Counter, defaultdict
from typing import List, Tuple

from sqlalchemy.exc import SQLAlchemyError

from db.models import (
    EventEntityConsensus,
    EventEntityImpact,
    SessionLocal,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Max possible classes output by our zero-shot NLI (positive, negative, neutral)
MAX_CLASSES = 3
MAX_ENTROPY = math.log2(MAX_CLASSES)


def compute_disagreement(labels: List[str]) -> float:
    """
    Computes normalized entropy over the label distribution.
    0.0 = Full agreement (all same label)
    1.0 = Maximally split across the 3 classes
    """
    if not labels or len(labels) <= 1:
        return 0.0

    counts = Counter(labels)
    total = sum(counts.values())
    
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
            
    # Normalize by max possible entropy for 3 classes
    score = entropy / MAX_ENTROPY
    
    # Cap at 1.0 to prevent floating point edge cases
    return min(score, 1.0)


def compute_consensus(labels: List[str], confidences: List[float]) -> str:
    """
    Computes majority vote. Ties are broken by highest average confidence.
    """
    if not labels:
        return "neutral"  # Fallback

    label_counts = defaultdict(int)
    label_conf_sum = defaultdict(float)
    
    for l, c in zip(labels, confidences):
        label_counts[l] += 1
        label_conf_sum[l] += c
        
    max_count = max(label_counts.values())
    candidates = [l for l, count in label_counts.items() if count == max_count]
    
    if len(candidates) == 1:
        return candidates[0]
        
    # Tie break
    best_label = candidates[0]
    best_avg_conf = -1.0
    for l in candidates:
        avg_conf = label_conf_sum[l] / label_counts[l]
        if avg_conf > best_avg_conf:
            best_avg_conf = avg_conf
            best_label = l
            
    return best_label


def process_batch():
    session = SessionLocal()
    try:
        logger.info("Clearing existing consensus records...")
        session.query(EventEntityConsensus).delete()
        session.commit()
    except Exception as e:
        logger.error("Failed to wipe old consensus: %s", e)
        session.rollback()
        sys.exit(1)

    # Load all impacts, group by (event_id, entity_id)
    impacts = session.query(EventEntityImpact).all()
    if not impacts:
        logger.info("No impact records found.")
        return

    # Grouping
    groups = defaultdict(list)
    for imp in impacts:
        # impact_label is an Enum, get its string name
        label_str = imp.impact_label.name if hasattr(imp.impact_label, "name") else str(imp.impact_label)
        groups[(imp.event_id, imp.entity_id)].append((label_str, imp.confidence))

    total_consensus = 0

    try:
        for (event_id, entity_id), items in groups.items():
            labels = [x[0] for x in items]
            confs = [x[1] for x in items]
            
            consensus_label = compute_consensus(labels, confs)
            disagreement = compute_disagreement(labels)
            
            row = EventEntityConsensus(
                event_id=event_id,
                entity_id=entity_id,
                consensus_label=consensus_label,
                disagreement_score=disagreement,
                num_sources=len(labels)
            )
            session.add(row)
            total_consensus += 1
            
        session.commit()
        logger.info("Successfully generated %d consensus records.", total_consensus)
        
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Database error during consensus aggregation: %s", exc)
    finally:
        session.close()


if __name__ == "__main__":
    process_batch()
