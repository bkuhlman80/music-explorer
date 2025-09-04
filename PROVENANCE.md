# PROVENANCE — Music Explorer

## Source
- **Name:** MusicBrainz  
- **URL:** https://musicbrainz.org  
- **API:** https://musicbrainz.org/ws/2  
- **Docs:** https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2  
- **License:** Creative Commons BY-NC-SA 4.0  
  - https://creativecommons.org/licenses/by-nc-sa/4.0/  

## Access & Limits
- No auth required, but **descriptive User-Agent is mandatory**  
  Example: `music-explorer/0.1 (your-email@example.com)`  
- Rate limits: official guideline = 1 req/sec/IP  
- Implemented: 1100 ms delay between requests (`MB_RATE_LIMIT_MS`)  
- Retries: exponential backoff, max 3  
- Timeout: 30 s  

## Pull Process
- Command:  
  ```bash
  make pull
- Environment: Python ≥3.11, Streamlit ≥1.37
- Controlled via .env:
    - MB_BASE_URL
    - USER_AGENT
    - MB_RATE_LIMIT_MS, MB_MAX_RETRIES, MB_TIMEOUT_S
    - ARTISTS_SEED (comma-separated names or MBIDs)

## Entities & Fields
- artist → id, name, sort-name, country, type, begin/end, tags
- release-group → id, title, first-release-date, primary-type, secondary-types, artist-credit, tags
- recording (optional) → id, title, length, release-list, artist-credit, tags

## Extract → Transform → Load
- raw → JSONL dumps per entity (data/raw/*.jsonl)
- clean → normalized tables (data/clean/*.parquet)
- marts → analysis-ready (data/marts/*.csv|parquet)
    - artists
    - artist_discography
    - release_groups_by_year
    - genres_by_decade
    - artist_collaborations_names

## Date Ranges
- Release groups aggregated by year (min..max from marts)
- Genres aggregated by decade (e.g., 1960s–2020s depending on seed)

## Figures
- docs/figures/collab_network.png
- docs/figures/genre_evolution.png
- Each caption:
    - Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled YYYY-MM-DD. Music metadata provided by MusicBrainz.

## Pull Log
- 2025-08-28 — Radiohead; Taylor Swift; Daft Punk
- 2025-09-03 — Radiohead; Daft Punk; Beyonce

## Repro Stamp
- Version tag: music-explorer-v0.2.0
- Commit: 808643d
- Build command: `make build && make report`
- Build date (UTC): 2025-09-03
- Environment: Linux/OSX, Python 3.11