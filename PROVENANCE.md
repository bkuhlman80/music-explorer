# Data Provenance — Music Explorer

## Source
- Name: MusicBrainz
- URL: https://musicbrainz.org
- API: https://musicbrainz.org/ws/2
- Documentation: https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2

## License
- Data License: Creative Commons BY-NC-SA 4.0
- Link: https://creativecommons.org/licenses/by-nc-sa/4.0/

## Rate Limits
- Official guidance: 1 request/second per IP
- Implemented: 1100ms delay between requests (configurable in `.env`)

## Pull Process
- Command used: make pull ARTIST="Radiohead"
- Environment: Python 3.11, Streamlit 1.37.1  
- User-Agent string: `music-explorer/0.1 (your-email@example.com)`

## Pull Log
- Initial run: 2025-08-28, artists: Radiohead, Taylor Swift, Daft Punk
- Subsequent updates: [append entries here with date + seed list]

## Notes
- Raw responses stored in `data/raw/` as JSON.  
- Clean transforms stored in `data/clean/` as CSV/Parquet.  
- Final marts stored in `data/marts/` for visualization.
