# Music Explorer

The **Music Explorer** project demonstrates how to transform an open cultural dataset into clear, interactive insights for analysts and casual listeners alike. Using the [MusicBrainz](https://musicbrainz.org/) API, the project pulls structured data on artists, releases, and genres, then cleans and reshapes it into timelines, collaboration graphs, and trend visualizations.  

Success is measured by three criteria:  
1. Reliability and speed of queries (artist or release results in under three seconds).  
2. Accuracy of derived genre and collaboration metrics against spot-checks from the source.  
3. Engagement with the app, where users navigate at least three distinct visualizations per session.  

The result is a reproducible, cloud-hosted portfolio artifact that highlights skills in API integration, data modeling, and interactive storytelling.

---

## Primary User Tasks
- Search artists by name and view a release timeline.  
- Explore collaboration networks through interactive graphs.  
- Analyze genre distribution and evolution across decades.  

## Key Performance Indicators (KPIs)
- Query response time ≤ 3 seconds for artist or release searches.  
- ≥ 90% accuracy in genre and collaboration counts versus source validation.  
- Average session depth of ≥ 3 unique views per user.  

---
![CI](https://github.com/bkuhlman80/music-explorer/actions/workflows/ci.yml/badge.svg)

## Live Demo
https://kuhl-music-explorer.streamlit.app/ 

<img width="562" height="455" alt="rg_per_year" src="https://github.com/user-attachments/assets/0e9bd330-1157-47f5-814f-2a79f9b76b62" />

Source: MusicBrainz, CC BY-NC-SA 4.0. Pulled 2025-08-28.

## Repo Map

- **README.md** — Project overview, usage guide
- **Makefile** — One-click setup, pipeline, testing, deploy
- **app/** — Streamlit app (`Main.py`) + pipeline and tools
  - `pipeline/` — Pull, clean, build
  - `figures/` — Export charts
  - `report/` — Generate PDF
  - `tools/` — Schema dictionary helpers
- **data/**
  - `raw/` — JSON pulls from MusicBrainz
  - `clean/` — Normalized tables (Parquet)
  - `marts/` — Aggregated data for analysis (CSV/Parquet)
- **docs/**
  - `figures/` — Exported charts and hero figure
  - `report.pdf` — 2-page non-technical summary
- **tests/** — Unit tests, schema checks, viz regression
- **env/**
  - `.env.example` — Template environment config
  - `requirements.txt` — Python dependencies
- **DATA_DICTIONARY.csv** — Schema mapping raw → clean → marts
- **PROVENANCE.md** — Data pull commands and logs
- **LICENSE_NOTES.md** — Reuse terms for data/code
- **.github/workflows/** — CI config
