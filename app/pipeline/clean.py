import os, json, glob
import pandas as pd

try:
    # when run as module: python -m app.pipeline.clean
    from ._clean_utils import parse_date, to_ms, is_uuid, norm_country
except ImportError:
    # when run as script: python app/pipeline/clean.py
    from _clean_utils import parse_date, to_ms, is_uuid, norm_country

OUTDIR = "data/clean"
REJECTS = []


def _append_reject(reason, tbl, row):
    REJECTS.append({"table": tbl, "reason": reason, **row})


def _write(df, name, pk=None):
    os.makedirs(OUTDIR, exist_ok=True)
    if pk:
        df = df.drop_duplicates(subset=pk, keep="first")
    df.to_parquet(f"{OUTDIR}/{name}.parquet", index=False)


def _finalize_rejects():
    if REJECTS:
        pd.DataFrame(REJECTS).to_parquet(f"{OUTDIR}/_rejects.parquet", index=False)


def _load_raw():
    files = glob.glob("data/raw/**/*.json", recursive=True)
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            yield fp, json.load(f)


def clean_artists(raw):
    rows = []
    for fp, data in raw:
        # artist detail responses have "id" at root; searches have "artists":[]
        if isinstance(data, dict) and data.get("id") and data.get("name"):
            a = data
            rows.append(
                {
                    "artist_mbid": a.get("id"),
                    "name": a.get("name"),
                    "sort_name": a.get("sort-name"),
                    "disambiguation": a.get("disambiguation"),
                    "type": a.get("type"),
                    "gender": a.get("gender"),
                    "area_mbid": (a.get("area") or {}).get("id"),
                    "begin_date": parse_date(((a.get("life-span") or {}).get("begin"))),
                    "end_date": parse_date(((a.get("life-span") or {}).get("end"))),
                    "ended": (a.get("life-span") or {}).get("ended"),
                }
            )
        elif isinstance(data, dict) and "artists" in data:
            for a in data.get("artists") or []:
                rows.append(
                    {
                        "artist_mbid": a.get("id"),
                        "name": a.get("name"),
                        "sort_name": a.get("sort-name"),
                        "disambiguation": a.get("disambiguation"),
                        "type": a.get("type"),
                        "gender": a.get("gender"),
                        "area_mbid": (a.get("area") or {}).get("id"),
                        "begin_date": parse_date(
                            ((a.get("life-span") or {}).get("begin"))
                        ),
                        "end_date": parse_date(((a.get("life-span") or {}).get("end"))),
                        "ended": (a.get("life-span") or {}).get("ended"),
                    }
                )
    df = (
        pd.DataFrame(rows)
        if rows
        else pd.DataFrame(
            columns=[
                "artist_mbid",
                "name",
                "sort_name",
                "disambiguation",
                "type",
                "gender",
                "area_mbid",
                "begin_date",
                "end_date",
                "ended",
            ]
        )
    )
    # validate PK + FK shapes
    bad = ~df["artist_mbid"].map(is_uuid)
    for _, r in df[bad].iterrows():
        _append_reject("bad_artist_mbid", "artists", r.to_dict())
    df = df[~bad]
    _write(df, "artists", pk=["artist_mbid"])
    return df


def clean_release_groups(raw):
    rows = []
    for fp, data in raw:
        if isinstance(data, dict) and "release-groups" in data:
            for g in data["release-groups"]:
                rows.append(
                    {
                        "rg_mbid": g.get("id"),
                        "title": g.get("title"),
                        "primary_type": g.get("primary-type"),
                        "first_release_date": parse_date(g.get("first-release-date")),
                        "artist_credit": g.get("artist-credit-phrase"),
                    }
                )
    df = pd.DataFrame(
        rows,
        columns=[
            "rg_mbid",
            "title",
            "primary_type",
            "first_release_date",
            "artist_credit",
        ],
    )
    bad = ~df["rg_mbid"].map(is_uuid)
    for _, r in df[bad].iterrows():
        _append_reject("bad_rg_mbid", "release_groups", r.to_dict())
    df = df[~bad]
    _write(df, "release_groups", pk=["rg_mbid"])
    return df


def clean_releases(raw):
    rows = []
    rel_labels = []
    for fp, data in raw:
        if isinstance(data, dict) and "releases" in data:
            for r in data["releases"]:
                rows.append(
                    {
                        "release_mbid": r.get("id"),
                        "rg_mbid": (r.get("release-group") or {}).get("id"),
                        "title": r.get("title"),
                        "date": parse_date(r.get("date")),
                        "country": norm_country(r.get("country")),
                        "barcode": r.get("barcode"),
                        "status": r.get("status"),
                    }
                )
                for li in r.get("label-info") or []:
                    lab = li.get("label") or {}
                    rel_labels.append(
                        {
                            "release_mbid": r.get("id"),
                            "label_mbid": lab.get("id"),
                            "catalog_number": li.get("catalog-number"),
                        }
                    )
    df = pd.DataFrame(
        rows,
        columns=[
            "release_mbid",
            "rg_mbid",
            "title",
            "date",
            "country",
            "barcode",
            "status",
        ],
    )
    dfl = pd.DataFrame(
        rel_labels, columns=["release_mbid", "label_mbid", "catalog_number"]
    )
    bad = ~df["release_mbid"].map(is_uuid)
    for _, r in df[bad].iterrows():
        _append_reject("bad_release_mbid", "releases", r.to_dict())
    df = df[~bad]
    _write(df, "releases", pk=["release_mbid"])
    if not dfl.empty:
        dfl = dfl.dropna(subset=["release_mbid", "label_mbid"])
        _write(
            dfl.drop_duplicates(),
            "release_labels",
            pk=["release_mbid", "label_mbid", "catalog_number"],
        )
    else:
        _write(
            pd.DataFrame(columns=["release_mbid", "label_mbid", "catalog_number"]),
            "release_labels",
        )
    return df


def clean_recordings_and_tracks(raw):
    recs = []
    tracks = []
    for fp, data in raw:
        if isinstance(data, dict) and "releases" in data:
            # recordings embedded under media[].tracks[]
            for r in data["releases"]:
                for m in r.get("media") or []:
                    for t in m.get("tracks") or []:
                        tr = {
                            "track_mbid": t.get("id"),
                            "release_mbid": r.get("id"),
                            "recording_mbid": (t.get("recording") or {}).get("id"),
                            "medium_index": m.get("position"),
                            "position": t.get("position"),
                            "title": t.get("title"),
                            "length_ms": to_ms(t.get("length")),
                        }
                        tracks.append(tr)
                        rec = t.get("recording") or {}
                        recs.append(
                            {
                                "recording_mbid": rec.get("id"),
                                "title": rec.get("title"),
                                "length_ms": to_ms(rec.get("length")),
                                "video": rec.get("video"),
                            }
                        )
    dfr = pd.DataFrame(
        recs, columns=["recording_mbid", "title", "length_ms", "video"]
    ).drop_duplicates(subset=["recording_mbid"])
    dft = pd.DataFrame(
        tracks,
        columns=[
            "track_mbid",
            "release_mbid",
            "recording_mbid",
            "medium_index",
            "position",
            "title",
            "length_ms",
        ],
    )
    dfr = dfr[dfr["recording_mbid"].map(is_uuid)]
    dft = dft[dft["track_mbid"].map(is_uuid)]
    _write(dfr, "recordings", pk=["recording_mbid"])
    _write(dft, "tracks", pk=["track_mbid"])
    return dfr, dft


def clean_labels(raw):
    rows = []
    for fp, data in raw:
        # labels usually embedded; skip unless present
        if isinstance(data, dict) and "releases" in data:
            for r in data["releases"]:
                for li in r.get("label-info") or []:
                    lab = li.get("label") or {}
                    rows.append(
                        {
                            "label_mbid": lab.get("id"),
                            "name": lab.get("name"),
                            "type": lab.get("type"),
                            "disambiguation": lab.get("disambiguation"),
                        }
                    )
    df = pd.DataFrame(
        rows, columns=["label_mbid", "name", "type", "disambiguation"]
    ).drop_duplicates(subset=["label_mbid"])
    df = df[df["label_mbid"].map(is_uuid)]
    _write(df, "labels", pk=["label_mbid"])
    return df


def clean_genres_and_tags(raw):
    grows = []
    trows = []

    def emit(entity_type, entity_id, genres, tags):
        for g in genres or []:
            grows.append(
                {
                    "entity_type": entity_type,
                    "entity_mbid": entity_id,
                    "genre": g.get("name"),
                    "votes": g.get("count"),
                }
            )
        for t in tags or []:
            trows.append(
                {
                    "entity_type": entity_type,
                    "entity_mbid": entity_id,
                    "tag": t.get("name"),
                    "votes": t.get("count"),
                }
            )

    for fp, data in raw:
        if isinstance(data, dict) and "release-groups" in data:
            for g in data["release-groups"]:
                emit("release-group", g.get("id"), g.get("genres"), g.get("tags"))
        if isinstance(data, dict) and data.get("id") and data.get("name"):
            a = data
            emit("artist", a.get("id"), a.get("genres"), a.get("tags"))
    dg = pd.DataFrame(
        grows, columns=["entity_type", "entity_mbid", "genre", "votes"]
    ).dropna(subset=["entity_mbid", "genre"])
    dt = pd.DataFrame(
        trows, columns=["entity_type", "entity_mbid", "tag", "votes"]
    ).dropna(subset=["entity_mbid", "tag"])
    _write(
        dg.drop_duplicates(),
        "entity_genres",
        pk=["entity_type", "entity_mbid", "genre"],
    )
    _write(
        dt.drop_duplicates(), "entity_tags", pk=["entity_type", "entity_mbid", "tag"]
    )
    return dg, dt


def main():
    raw = list(_load_raw())
    artists = clean_artists(raw)
    rgs = clean_release_groups(raw)
    releases = clean_releases(raw)
    recs, tr = clean_recordings_and_tracks(raw)
    labels = clean_labels(raw)
    genres, tags = clean_genres_and_tags(raw)
    _finalize_rejects()
    print("Clean layer written to data/clean")


if __name__ == "__main__":
    main()
