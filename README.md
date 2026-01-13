# Life Path Test (Streamlit MVP) – TR/EN

A small Streamlit web app built as a learning MVP: interactive questionnaire → archetype scoring → shareable result → lightweight logging.

## Live Demo
- Streamlit Cloud: (paste your app link here)

## What this is (and what it isn’t)
This project is **not** a scientifically validated personality test.  
It is a **product/engineering learning MVP**:
- End-to-end user flow
- JSON-driven content
- Basic scoring + results
- Shareable link flow
- Data logging for iteration

## Features
- TR/EN language option (sidebar)
- JSON-driven questions (no hardcoding)
- Session-based flow + scoring
- Result page + share link (query param `?id=...`)
- JSONL logging for later analysis

## Project Structure
- `streamlit_app.py` → Streamlit entrypoint
- `app/` → application code (UI, scoring, storage, i18n)
- `data/` → question sets (JSON)
- `_archive/` → old notebooks/backups (non-production)

## Question files
Questions are loaded from JSON files under `data/`.
Expected format:
```json
[
  {
    "soru": "...",
    "secenekler": [
      {"yazi": "...", "etki": {"merak": 2}, "mini_sahne": "..."}
    ]
  }
]
