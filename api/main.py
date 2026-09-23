"""FastAPI backend (Phase 8)."""

from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.models import (
    SessionLocal,
    Event,
    Entity,
    EventEntityImpact,
    EventEntityConsensus,
    RawPost,
)
from pydantic import BaseModel

app = FastAPI(title="Hindi OSINT Entity Impact API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class EventOut(BaseModel):
    event_id: int
    representative_text: str


class ImpactSourceOut(BaseModel):
    source_id: str
    impact_label: str
    confidence: float
    source_text: str


class EntityConsensusOut(BaseModel):
    entity_id: int
    canonical_name: str
    consensus_label: str
    disagreement_score: float
    num_sources: int
    sources: List[ImpactSourceOut]


class EventDetailOut(BaseModel):
    event_id: int
    representative_text: str
    entities: List[EntityConsensusOut]


@app.get("/events", response_model=List[EventOut])
def list_events(db: Session = Depends(get_db)):
    """List all events."""
    events = db.query(Event).order_by(desc(Event.event_id)).all()
    return [{"event_id": e.event_id, "representative_text": e.representative_text} for e in events]


@app.get("/events/{event_id}/impacts", response_model=EventDetailOut)
def get_event_impacts(event_id: int, db: Session = Depends(get_db)):
    """Get full impact and consensus details for an event."""
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Fetch consensus
    consensus_rows = db.query(EventEntityConsensus).filter(EventEntityConsensus.event_id == event_id).all()
    
    entities_out = []
    
    for c in consensus_rows:
        entity = db.query(Entity).filter(Entity.entity_id == c.entity_id).first()
        
        # Fetch impacts
        impacts = db.query(EventEntityImpact, RawPost.cleaned_text).join(
            RawPost, EventEntityImpact.source_id == RawPost.source_id
        ).filter(
            EventEntityImpact.event_id == event_id,
            EventEntityImpact.entity_id == c.entity_id
        ).all()
        
        sources_out = []
        for imp, text in impacts:
            sources_out.append({
                "source_id": imp.source_id,
                "impact_label": imp.impact_label.name,
                "confidence": imp.confidence,
                "source_text": text or ""
            })
            
        entities_out.append({
            "entity_id": c.entity_id,
            "canonical_name": entity.canonical_name,
            "consensus_label": c.consensus_label,
            "disagreement_score": c.disagreement_score,
            "num_sources": c.num_sources,
            "sources": sources_out
        })
        
    return {
        "event_id": event.event_id,
        "representative_text": event.representative_text,
        "entities": entities_out
    }
