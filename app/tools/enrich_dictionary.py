# app/tools/enrich_dictionary.py
import argparse, csv, re

# Field-level defaults (applied by exact field match, case-sensitive)
FIELD_NOTES = {
    "id": ("uuid", "Primary MBID (MusicBrainz UUID)"),
    "artist_mbid": ("uuid", "Artist MBID (FK)"),
    "rg_mbid": ("uuid", "Release Group MBID (FK)"),
    "release_mbid": ("uuid", "Release MBID (FK)"),
    "recording_mbid": ("uuid", "Recording MBID (FK)"),
    "work_mbid": ("uuid", "Work MBID (FK)"),
    "label_mbid": ("uuid", "Label MBID (FK)"),
    "area_mbid": ("uuid", "Area MBID (FK)"),
    "type": ("", "Entity type from MusicBrainz (e.g., person, group, album)"),
    "type-id": ("uuid", "Type UUID in MusicBrainz"),
    "name": ("", "Display name or title"),
    "sort-name": ("", "Name used for sorting"),
    "disambiguation": ("", "Short comment to distinguish similar entities"),
    "gender": ("", "Artist gender when applicable"),
    "country": ("ISO-2", "Release country code"),
    "barcode": ("", "Barcode for a release"),
    "status": ("", "Release status (e.g., Official, Promotion)"),
    "first-release-date": ("date", "First release date for the group (YYYY-MM-DD)"),
    "date": ("date", "Release date (YYYY-MM-DD)"),
    "begin": ("date", "Begin date (YYYY-MM-DD)"),
    "end": ("date", "End date (YYYY-MM-DD)"),
    "begin-date": ("date", "Begin date (YYYY-MM-DD)"),
    "end-date": ("date", "End date (YYYY-MM-DD)"),
    "ended": ("", "Whether the entity has ended"),
    "length": ("ms", "Recording or track length in milliseconds"),
    "video": ("", "Flag indicating a video recording"),
    "position": ("", "Track position within medium"),
    "title": ("", "Title"),
    "artist-credit-phrase": ("", "Rendered artist credit string"),
    "primary-type": ("", "Primary release-group type (Album/Single/EP/etc.)"),
    "genres[].name": ("", "Genre label"),
    "genres[].count": ("", "Genre vote count"),
    "tags[].name": ("", "Free tag label"),
    "tags[].count": ("", "Tag vote count"),
    "iswcs[]": ("", "ISWC codes for a work"),
    "medium.position": ("", "Medium index within release (disc number)"),
    "medium.track[].position": ("", "Track position on medium"),
    "medium.track[].length": ("ms", "Track length in milliseconds"),
    "medium.track[].id": ("uuid", "Track MBID (distinct from recording MBID)"),
    "medium.track[].recording.id": ("uuid", "Recording MBID for this track"),
    "relations[].type": ("", "Relationship type (e.g., official homepage)"),
    "relations[].target-type": ("", "Target entity type for relation"),
    "href": ("", "Target URL"),
}

# Heuristics (regex on field path). Only fill if unit/description empty.
HEURISTICS = [
    (re.compile(r"(?:^|[\.\[\]])id$"), ("uuid", "Primary or foreign key MBID (UUID)")),
    (
        re.compile(r"(?:^|[\.\[\]])length(?:[\.\[].*)?$"),
        ("ms", "Duration in milliseconds"),
    ),
    (
        re.compile(r"(?:^|[\.\[\]])(date|begin|end|first-release-date)(?:[\.\[].*)?$"),
        ("date", "Date in YYYY-MM-DD when available"),
    ),
    (
        re.compile(r"(?:^|[\.\[\]])country$"),
        ("ISO-2", "Country code (ISO-3166-1 alpha-2)"),
    ),
]


def enrich(unit, desc, field):
    # keep existing if already filled
    if unit and desc:
        return unit, desc

    # exact field notes first
    if field in FIELD_NOTES:
        u, d = FIELD_NOTES[field]
        unit = unit or u
        desc = desc or d

    # heuristics next
    for rx, (u, d) in HEURISTICS:
        if rx.search(field):
            unit = unit or u
            desc = desc or d

    return unit, desc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="DATA_DICTIONARY.csv")
    ap.add_argument("--outfile", default="DATA_DICTIONARY_enriched.csv")
    args = ap.parse_args()

    rows = []
    with open(args.infile, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        want_cols = ["table", "field", "type", "unit", "description", "source_field"]
        if r.fieldnames != want_cols:
            raise SystemExit(f"Unexpected header. Got {r.fieldnames}, want {want_cols}")
        for row in r:
            unit, desc = enrich(
                row.get("unit", ""), row.get("description", ""), row["field"]
            )
            row["unit"], row["description"] = unit, desc
            rows.append(row)

    with open(args.outfile, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "table",
                "field",
                "type",
                "unit",
                "description",
                "source_field",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {args.outfile} with enriched units and descriptions")


if __name__ == "__main__":
    main()
