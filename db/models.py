"""SQLAlchemy ORM models for all 7 tables per architecture.md §4.

Loads DB connection string from .env via python-dotenv.
No hardcoded credentials per rules.md §2.
"""

import enum
import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

load_dotenv()


def get_database_url() -> str:
    """Build the Postgres connection URL from environment variables."""
    user = os.getenv("POSTGRES_USER", "osint")
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "osint_db")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


engine = create_engine(get_database_url())
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


# ── impact_label enum ──────────────────────────────────────────────
class ImpactLabel(enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"


# ── 1. raw_posts ───────────────────────────────────────────────────
class RawPost(Base):
    __tablename__ = "raw_posts"

    post_id: int = Column(Integer, primary_key=True, autoincrement=True)
    source_id: str = Column(String, nullable=False, index=True)
    source_type: str = Column(String, nullable=False)
    raw_text: str = Column(Text, nullable=False)
    cleaned_text: Optional[str] = Column(Text, nullable=True)
    status: str = Column(String, nullable=False, default="pending", index=True)
    published_at: Optional[datetime] = Column(DateTime, nullable=True)
    content_hash: str = Column(String, nullable=False, unique=True)

    event_post_maps = relationship("EventPostMap", back_populates="post", cascade="all, delete-orphan")


# ── 2. events ─────────────────────────────────────────────────────
class Event(Base):
    __tablename__ = "events"

    event_id: int = Column(Integer, primary_key=True, autoincrement=True)
    representative_text: str = Column(Text, nullable=False)
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)

    event_post_maps = relationship("EventPostMap", back_populates="event", cascade="all, delete-orphan")
    event_entities = relationship("EventEntity", back_populates="event", cascade="all, delete-orphan")
    impacts = relationship("EventEntityImpact", back_populates="event", cascade="all, delete-orphan")
    consensus = relationship("EventEntityConsensus", back_populates="event", cascade="all, delete-orphan")


# ── 3. event_post_map ─────────────────────────────────────────────
class EventPostMap(Base):
    __tablename__ = "event_post_map"

    event_id: int = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    post_id: int = Column(
        Integer,
        ForeignKey("raw_posts.post_id", ondelete="CASCADE"),
        primary_key=True,
    )
    similarity_score: float = Column(Float, nullable=True)

    event = relationship("Event", back_populates="event_post_maps")
    post = relationship("RawPost", back_populates="event_post_maps")

    __table_args__ = (
        UniqueConstraint("event_id", "post_id", name="uq_event_post"),
    )


# ── 4. entities ───────────────────────────────────────────────────
class Entity(Base):
    __tablename__ = "entities"

    entity_id: int = Column(Integer, primary_key=True, autoincrement=True)
    canonical_name: str = Column(String, nullable=False)
    entity_type: str = Column(String, nullable=False)
    aliases: List[str] = Column(ARRAY(String), nullable=True)

    event_entities = relationship("EventEntity", back_populates="entity", cascade="all, delete-orphan")
    impacts = relationship("EventEntityImpact", back_populates="entity", cascade="all, delete-orphan")
    consensus = relationship("EventEntityConsensus", back_populates="entity", cascade="all, delete-orphan")


# ── 5. event_entities (junction) ──────────────────────────────────
class EventEntity(Base):
    __tablename__ = "event_entities"

    event_id: int = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    entity_id: int = Column(
        Integer,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        primary_key=True,
    )

    event = relationship("Event", back_populates="event_entities")
    entity = relationship("Entity", back_populates="event_entities")

    __table_args__ = (
        UniqueConstraint("event_id", "entity_id", name="uq_event_entity"),
    )


# ── 6. event_entity_impact ────────────────────────────────────────
class EventEntityImpact(Base):
    __tablename__ = "event_entity_impact"

    event_id: int = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    entity_id: int = Column(
        Integer,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_id: str = Column(String, primary_key=True)
    impact_label: ImpactLabel = Column(
        Enum(ImpactLabel, name="impact_label_enum"), nullable=False
    )
    confidence: float = Column(Float, nullable=True)

    event = relationship("Event", back_populates="impacts")
    entity = relationship("Entity", back_populates="impacts")


# ── 7. event_entity_consensus ─────────────────────────────────────
class EventEntityConsensus(Base):
    __tablename__ = "event_entity_consensus"

    event_id: int = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        primary_key=True,
    )
    entity_id: int = Column(
        Integer,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        primary_key=True,
    )
    consensus_label: str = Column(String, nullable=False)
    disagreement_score: float = Column(Float, nullable=False)
    num_sources: int = Column(Integer, nullable=False)

    event = relationship("Event", back_populates="consensus")
    entity = relationship("Entity", back_populates="consensus")

    __table_args__ = (
        UniqueConstraint("event_id", "entity_id", name="uq_event_entity_consensus"),
    )
