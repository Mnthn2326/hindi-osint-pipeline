"""Streamlit Dashboard (Phase 8)."""

import os
import html
import streamlit as st
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Color mappings
COLORS = {
    "positive": "#2E9E5B",
    "negative": "#E0654F",
    "neutral": "#9AA0AC",
    "mixed": "#E0A83F"
}

st.set_page_config(page_title="Hindi OSINT Entity Impact Dashboard", layout="wide")

st.title("Hindi OSINT Entity Impact Dashboard")

@st.cache_data(ttl=10)
def fetch_events():
    try:
        r = requests.get(f"{API_URL}/events")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return []

@st.cache_data(ttl=10)
def fetch_impacts(event_id):
    try:
        r = requests.get(f"{API_URL}/events/{event_id}/impacts")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error fetching impacts: {e}")
        return None

def format_label(label: str) -> str:
    color = COLORS.get(label.lower(), "#9AA0AC")
    safe_label = html.escape(label.upper())
    return f"<span style='color: {color}; font-weight: bold;'>{safe_label}</span>"

events = fetch_events()

if not events:
    st.info("No events found or API is down.")
    st.stop()

# Sidebar
st.sidebar.header("Events")
event_options = {}
for e in events:
    short_text = e["representative_text"][:60] + ("..." if len(e["representative_text"]) > 60 else "")
    label = f"[{e['event_id']}] {short_text}"
    event_options[label] = e["event_id"]

selected_event_label = st.sidebar.radio("Select an event:", list(event_options.keys()))
selected_event_id = event_options[selected_event_label]

# Main Panel
data = fetch_impacts(selected_event_id)

if not data:
    st.warning("No impact data available for this event.")
    st.stop()

st.subheader("Event Text")
st.write(data["representative_text"])

entities = data.get("entities", [])
if not entities:
    st.info("No entities detected for this event.")
    st.stop()

# Badges for entities
entity_names = [e["canonical_name"] for e in entities]
badges = " ".join([f"<span style='background-color: #2F9E8F; color: white; padding: 4px 8px; border-radius: 4px; margin-right: 8px;'>{html.escape(name)}</span>" for name in entity_names])
st.markdown(f"**Entities Affected:** <br/> {badges}", unsafe_allow_html=True)
st.markdown("---")

st.subheader("Per-Source Impact")
# Flatten impacts into a dataframe
table_data = []
for ent in entities:
    for src in ent["sources"]:
        table_data.append({
            "Entity": ent["canonical_name"],
            "Source Text": src["source_text"][:100] + "...",
            "Impact": src["impact_label"].upper(),
            "Confidence": round(src["confidence"], 2)
        })

if table_data:
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)
else:
    st.write("No source impacts found.")

st.markdown("---")
st.subheader("Consensus & Disagreement")

# Consensus section
use_columns = len(entities) <= 4
if use_columns:
    cols = st.columns(len(entities))
    for idx, ent in enumerate(entities):
        with cols[idx]:
            st.markdown(f"#### {ent['canonical_name']}")
            lbl_html = format_label(ent["consensus_label"])
            st.markdown(f"**Consensus:** {lbl_html}", unsafe_allow_html=True)
            score = ent["disagreement_score"]
            st.markdown(f"**Disagreement:** `{score:.2f}`")
            st.progress(score)
            st.caption(f"Based on {ent['num_sources']} sources")
else:
    for ent in entities:
        st.markdown(f"#### {ent['canonical_name']}")
        lbl_html = format_label(ent["consensus_label"])
        st.markdown(f"**Consensus:** {lbl_html}", unsafe_allow_html=True)
        score = ent["disagreement_score"]
        st.markdown(f"**Disagreement:** `{score:.2f}`")
        st.progress(score)
        st.caption(f"Based on {ent['num_sources']} sources")
        st.markdown("<br/>", unsafe_allow_html=True)
