"""Preprocessing batch job (Phase 3).

Reads raw_posts where status='pending' and cleaned_text is NULL.
- Strips HTML and normalizes whitespace.
- Dedupes near-identical text (exact match after cleaning).
- Runs language ID (langdetect).
- Keeps only Hindi / Hindi-English code-mixed rows (status='kept').
- Marks others as status='skipped_non_hindi', 'skipped_duplicate', etc.

Usage:
    python -m preprocessing.clean
"""

import hashlib
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


def _compute_cleaned_hash(text: str) -> str:
    """SHA-256 hash of cleaned text for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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

        # We keep track of hashes within the current batch
        seen_hashes_in_batch: Set[str] = set()

        kept_count = 0
        skipped_count = 0

        for post in posts:
            cleaned = clean_text(post.raw_text)
            
            if not cleaned:
                post.status = "skipped_empty"
                skipped_count += 1
                continue
                
            cleaned_hash = _compute_cleaned_hash(cleaned)
            
            if cleaned_hash in seen_hashes_in_batch:
                post.status = "skipped_duplicate"
                skipped_count += 1
                continue
                
            # DB-level dedup check for previously kept posts
            existing = session.query(RawPost.post_id).filter(
                RawPost.cleaned_text_hash == cleaned_hash
            ).first()
            
            if existing:
                post.status = "skipped_duplicate"
                skipped_count += 1
                continue
                
            if not is_hindi_or_codemixed(cleaned):
                post.status = "skipped_non_hindi"
                skipped_count += 1
                continue
                
            # If we passed all checks, mark as kept
            post.cleaned_text = cleaned
            post.cleaned_text_hash = cleaned_hash
            post.status = "kept"
            seen_hashes_in_batch.add(cleaned_hash)
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
