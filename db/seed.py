"""Seed script — creates all tables directly via SQLAlchemy metadata.

Alternative to Alembic migration for quick setup.
Usage: python -m db.seed
"""

import logging

from db.models import Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed() -> None:
    """Create all tables defined in db.models if they don't already exist."""
    logger.info("Creating tables from SQLAlchemy metadata...")
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created (or already exist).")


if __name__ == "__main__":
    seed()
