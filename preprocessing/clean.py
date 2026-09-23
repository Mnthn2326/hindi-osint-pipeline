"""Preprocessing batch job (Phase 3).

Reads raw_posts where status='pending' and cleaned_text is NULL.
- Strips HTML and normalizes whitespace.
- Dedupes near-identical text (exact match after cleaning).
- Runs language ID (langdetect).
- Keeps only Hindi / Hindi-English code-mixed rows (status='processed').
- Marks others as status='skipped'.

Usage:
    python -m preprocessing.clean
"""

import html
import logging
import re
from typing import Set

from langdetect import LangDetectException, detect_langs
from sqlalchemy.exc import SQLAlchemyError

from db.models import RawPost, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")


def clean_text(raw_text: str) -> str:
    """Strip HTML, unescape entities, and normalize whitespace."""
    text = html.unescape(raw_text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_hindi_or_codemixed(text: str) -> bool:
    """Determine if text is Hindi or Hindi-English code-mixed.

    Uses langdetect. Since code-mixed text or short Devanagari text can
    sometimes be misclassified as Marathi (mr) or Nepali (ne) due to
    shared script, we use a heuristic combination.
    """
    has_devanagari = bool(DEVANAGARI_REGEX.search(text))

    try:
        langs = detect_langs(text)
        for lang_res in langs:
            # If langdetect explicitly finds Hindi, we keep it
            if lang_res.lang == "hi":
                return True
            # If it has Devanagari script and is classified as mr/ne/en,
            # it's likely code-mixed or regional variation of our target data
            if has_devanagari and lang_res.lang in ("mr", "ne", "en"):
                return True
    except LangDetectException:
        pass

    # Fallback: if langdetect fails but we have Devanagari, keep it
    return has_devanagari


def process_batch() -> None:
    """Run preprocessing on all pending posts."""
    session = SessionLocal()
    
    try:
        # Fetch pending posts
        posts = session.query(RawPost).filter(RawPost.status == "pending").all()
        if not posts:
            logger.info("No pending posts to process.")
            return

        logger.info("Fetched %d pending posts.", len(posts))

        # We will dedupe across this batch and any existing processed text
        # To scale, we'd query existing cleaned_text hashes. For MVP, we load
        # existing processed texts into a set.
        existing_cleaned = session.query(RawPost.cleaned_text).filter(
            RawPost.status == "processed"
        ).all()
        seen_texts: Set[str] = {row[0] for row in existing_cleaned if row[0]}

        kept_count = 0
        skipped_count = 0

        for post in posts:
            cleaned = clean_text(post.raw_text)
            
            if not cleaned:
                post.status = "skipped_empty"
                skipped_count += 1
                continue
                
            if cleaned in seen_texts:
                post.status = "skipped_duplicate"
                skipped_count += 1
                continue
                
            if not is_hindi_or_codemixed(cleaned):
                post.status = "skipped_non_hindi"
                skipped_count += 1
                continue
                
            # If we passed all checks, mark as processed
            post.cleaned_text = cleaned
            post.status = "processed"
            seen_texts.add(cleaned)
            kept_count += 1

        # Commit batch per rules.md §3
        session.commit()
        
        logger.info(
            "Batch complete. Kept: %d, Skipped: %d (Total: %d)",
            kept_count, skipped_count, len(posts)
        )

    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("DB error during preprocessing batch: %s", exc)
    finally:
        session.close()


def main() -> None:
    """CLI entry point."""
    logger.info("Starting preprocessing job...")
    process_batch()


if __name__ == "__main__":
    main()
