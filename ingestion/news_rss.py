"""News RSS ingestion connector.

Fetches Hindi news RSS feeds listed in config/feeds.json, hashes each entry's
title+link for dedup via content_hash, and inserts new entries into raw_posts
(source_type='news'). Skips entries whose content_hash already exists.

Ingestion never interprets content — it only fetches, hashes, dedupes, stores
(architecture.md §5).

Usage:
    python -m ingestion.news_rss
    python -m ingestion.news_rss --config ingestion/config/feeds.json
"""

import argparse
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import feedparser
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from db.models import RawPost, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Retry config per rules.md §3: max 3 attempts with backoff
MAX_RETRIES: int = 3
BACKOFF_BASE: float = 2.0


def _compute_hash(title: str, link: str) -> str:
    """SHA-256 hash of title+link for content-based dedup."""
    payload = f"{title}|{link}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_published(entry: Dict[str, Any]) -> Optional[datetime]:
    """Extract published datetime from a feed entry, or None."""
    time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if time_struct:
        try:
            return datetime(*time_struct[:6])
        except (TypeError, ValueError) as exc:
            logger.debug("Could not parse date for entry: %s", exc)
    return None


def _build_raw_text(entry: Dict[str, Any]) -> str:
    """Assemble raw text from available entry fields.

    Assumption (rules.md §1): narrowest interpretation — concatenate title
    and summary/description since those are the text fields available in RSS.
    """
    parts: List[str] = []
    title = (entry.get("title") or "").strip()
    if title:
        parts.append(title)
    # summary is the typical content field in RSS entries
    summary = (entry.get("summary") or entry.get("description") or "").strip()
    if summary:
        parts.append(summary)
    return "\n\n".join(parts)


def fetch_feed(url: str) -> Optional[feedparser.FeedParserDict]:
    """Fetch an RSS feed with retry-with-backoff (max 3 attempts).

    Returns the parsed feed or None if all attempts fail.
    Per rules.md §3: handle network errors, log and skip rather than crash.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            feed = feedparser.parse(url)
            if feed.bozo and feed.bozo_exception:
                # feedparser sets bozo=1 for malformed feeds; log but proceed
                # if entries were still parsed
                logger.warning(
                    "Feed %s had parse warning (attempt %d): %s",
                    url, attempt, feed.bozo_exception,
                )
            if feed.entries:
                return feed
            if attempt < MAX_RETRIES:
                logger.info(
                    "Feed %s returned 0 entries (attempt %d/%d), retrying...",
                    url, attempt, MAX_RETRIES,
                )
                time.sleep(BACKOFF_BASE ** attempt)
                continue
            logger.warning("Feed %s returned 0 entries after %d attempts.", url, MAX_RETRIES)
            return feed
        except Exception as exc:
            logger.error(
                "Network error fetching %s (attempt %d/%d): %s",
                url, attempt, MAX_RETRIES, exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE ** attempt)
    return None


def ingest_feed(url: str) -> Dict[str, int]:
    """Ingest a single RSS feed URL into raw_posts.

    Returns counts: {'inserted': N, 'skipped': M, 'errors': E}
    """
    stats: Dict[str, int] = {"inserted": 0, "skipped": 0, "errors": 0}

    feed = fetch_feed(url)
    if feed is None:
        logger.error("Skipping feed %s — all fetch attempts failed.", url)
        return stats

    logger.info("Processing %d entries from %s", len(feed.entries), url)

    session = SessionLocal()
    try:
        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()

            if not title and not link:
                logger.debug("Skipping entry with no title and no link.")
                stats["errors"] += 1
                continue

            content_hash = _compute_hash(title, link)

            # Idempotency check: skip if hash already exists (rules.md §2)
            existing = (
                session.query(RawPost.post_id)
                .filter(RawPost.content_hash == content_hash)
                .first()
            )
            if existing:
                logger.debug("Duplicate skipped: %s", title[:60])
                stats["skipped"] += 1
                continue

            raw_text = _build_raw_text(entry)
            if not raw_text:
                logger.debug("Skipping entry with empty raw_text: %s", link)
                stats["errors"] += 1
                continue

            post = RawPost(
                source_id=link or title,
                source_type="news",
                raw_text=raw_text,
                status="pending",
                published_at=_parse_published(entry),
                content_hash=content_hash,
            )
            session.add(post)
            stats["inserted"] += 1

        # Batch commit per rules.md §3
        session.commit()
        logger.info(
            "Feed %s — inserted: %d, skipped (dups): %d, errors: %d",
            url, stats["inserted"], stats["skipped"], stats["errors"],
        )
    except (IntegrityError, SQLAlchemyError) as exc:
        session.rollback()
        logger.error("DB error during batch insert for %s: %s", url, exc)
        stats["errors"] += stats["inserted"]
        stats["inserted"] = 0
    finally:
        session.close()

    return stats


def load_feed_urls(config_path: str) -> List[str]:
    """Load RSS feed URLs from a JSON config file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path, encoding="utf-8") as f:
        urls = json.load(f)
    if not isinstance(urls, list):
        raise ValueError(f"Expected a JSON array in {config_path}")
    return urls


def main() -> None:
    """CLI entry point for RSS ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest Hindi news RSS feeds into raw_posts."
    )
    parser.add_argument(
        "--config",
        default=os.path.join("ingestion", "config", "feeds.json"),
        help="Path to JSON file containing RSS feed URLs (default: ingestion/config/feeds.json)",
    )
    args = parser.parse_args()

    urls = load_feed_urls(args.config)
    logger.info("Loaded %d feed URL(s) from %s", len(urls), args.config)

    totals: Dict[str, int] = {"inserted": 0, "skipped": 0, "errors": 0}
    for url in urls:
        stats = ingest_feed(url)
        for key in totals:
            totals[key] += stats[key]

    logger.info(
        "DONE — total inserted: %d, skipped: %d, errors: %d",
        totals["inserted"], totals["skipped"], totals["errors"],
    )


if __name__ == "__main__":
    main()
