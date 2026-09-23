# Design Guidelines

Scope: the Streamlit dashboard only. This is an analyst tool, not a consumer product
— prioritize legibility and unambiguous semantic color over visual polish.

## 1. Color palette

| Token | Hex | Usage |
|---|---|---|
| Background | `#0E1117` (dark) or `#FFFFFF` (light) | Streamlit default per theme mode — do not override, let user's system theme decide |
| Primary accent | `#2F9E8F` (teal) | Selected state, active nav, primary buttons |
| Text primary | `#1A1A2E` (light mode) / `#E8E8F0` (dark mode) | Body text |
| Text secondary | `#6B6B7D` | Timestamps, metadata, captions |

### Semantic colors — impact labels (use consistently everywhere a label appears)

| Label | Hex | Notes |
|---|---|---|
| Positive | `#2E9E5B` (green) | |
| Negative | `#E0654F` (coral-red) | |
| Neutral | `#9AA0AC` (gray) | |
| Mixed | `#E0A83F` (amber) | Never render as a blend of green/red — use a distinct third color, blending implies a midpoint that mixed does not mean |

### Disagreement score visualization

Single-hue sequential scale, NOT diverging (disagreement is a magnitude, not a
direction): light teal `#D9F2EE` (score near 0, consensus) through dark teal
`#0B5A50` (score near 1, maximal split). Render as a horizontal bar, 0-1 scale,
with the numeric score printed alongside — never color alone (see Section 4).

## 2. Typography

- Use Streamlit's default font stack (`"Source Sans Pro", sans-serif`) — do not
  import custom fonts. This is an internal analyst tool; font loading overhead
  is not worth it.
- Headers: Streamlit's built-in `st.header()` / `st.subheader()` — do not hand-roll
  heading styles with `st.markdown()` + raw HTML unless a specific layout requires it.
- Body text: 14-16px equivalent (Streamlit default `st.write()` / `st.text()` sizing).
- Numeric values (confidence scores, disagreement scores): monospace via
  `st.code()` or markdown backticks, so decimal alignment is scannable in tables.

## 3. Spacing / layout

- Sidebar: event list only. Each entry shows `representative_text` truncated to
  ~60 characters + date. No entity/impact detail in the sidebar — that belongs in
  the main panel after selection.
- Main panel, top to bottom: event title/representative_text (full) → entities
  affected (as a row of small badges/chips) → per-source impact table → consensus
  section (one row per entity: consensus label + disagreement bar).
- Use `st.columns()` for the consensus section (one column per entity) only if
  ≤4 entities are affected; beyond that, fall back to a vertical list to avoid
  cramped columns.
- Standard Streamlit container padding — do not override with custom CSS unless
  a specific readability problem shows up in testing.

## 4. Accessibility / clarity rules

- Never encode meaning by color alone. Every colored label (impact direction,
  disagreement bar) must also carry text (the label word, the numeric score).
  This matters both for accessibility and for demo clarity — a reviewer glancing
  at a screenshot should be able to read the state without color perception.
- Disagreement bars must show the numeric score as text, not just bar length.
- Do not use red/green alone to distinguish positive/negative without the word
  label present (colorblind-safe practice, and also just clearer in a demo).

## 5. What NOT to build this phase

- No custom Streamlit theming beyond `.streamlit/config.toml` primary color.
- No animations, transitions, or custom CSS injection.
- No mobile-responsive layout — this is presented on a laptop/projector for review.
- No logo/branding beyond a plain text title ("Hindi OSINT Entity Impact Dashboard").
