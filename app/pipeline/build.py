# app/pipeline/build.py
from __future__ import annotations

import re
import json
from pathlib import Path

from app.figures.collab_network import plot_collab_network
from app.figures.genre_evolution import plot_genre_evolution

import pandas as pd
import unicodedata
from app.schema import SchemaResolver

schema = SchemaResolver()

CLEAN = Path("data/clean")
MARTS = Path("data/marts")
RAW = Path("data/raw")
FIG_DIR = Path("docs/figures")

MARTS.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

MIN_EDGE_WEIGHT = 2  # keep only edges seen >=2 times


def norm_name(n: str) -> str:
    if not isinstance(n, str):
        return ""
    # strip accents, lowercase, collapse spaces
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    n = n.casefold().strip()
    n = re.sub(r"\s+", " ", n)
    return n


def read_parquet(name: str) -> pd.DataFrame:
    return pd.read_parquet(CLEAN / f"{name}.parquet")


def write_both(df: pd.DataFrame, base: str) -> None:
    df.to_csv(MARTS / f"{base}.csv", index=False)
    df.to_parquet(MARTS / f"{base}.parquet", index=False)


def collabs_from_recordings(jsonl_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = Path(jsonl_path)
    rows_id, rows_name = [], []
    if not p.exists() or p.stat().st_size == 0:
        return (
            pd.DataFrame(columns=["artist_id", "peer_id", "weight"]),
            pd.DataFrame(columns=["name_a", "name_b", "weight"]),
        )
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ac = rec.get("artist-credit") or rec.get("artist_credit") or []
            ids, names = [], []
            for part in ac:
                if isinstance(part, dict):
                    art = part.get("artist") or {}
                    aid = art.get("id")
                    nm = art.get("name") or art.get("sort-name")
                    if aid:
                        ids.append(aid)
                    if nm:
                        names.append(nm.strip())
            ids = sorted(set(ids))
            names = sorted(set(n for n in names if n))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    rows_id.append(
                        {"artist_id": ids[i], "peer_id": ids[j], "weight": 1}
                    )
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    rows_name.append(
                        {"name_a": names[i], "name_b": names[j], "weight": 1}
                    )

    id_df = (
        pd.DataFrame(rows_id)
        .groupby(["artist_id", "peer_id"], as_index=False)["weight"]
        .sum()
        if rows_id
        else pd.DataFrame(columns=["artist_id", "peer_id", "weight"])
    )
    name_df = (
        pd.DataFrame(rows_name)
        .groupby(["name_a", "name_b"], as_index=False)["weight"]
        .sum()
        if rows_name
        else pd.DataFrame(columns=["name_a", "name_b", "weight"])
    )
    return id_df, name_df


# token list for splitting human-entered credits
_SPLIT_TOKENS = [
    " feat. ",
    " featuring ",
    " with ",
    " & ",
    ", ",
    " and ",
    " x ",
    " / ",
    "; ",
    " vs ",
    " meets ",
    " presents ",
    " y ",
    " con ",
    " ft. ",
    " Feat. ",
]


def split_credit(s: str) -> list[str]:
    parts = [s or ""]
    for tok in _SPLIT_TOKENS:
        parts = sum((p.split(tok) for p in parts), [])
    parts = [p.strip() for p in parts if p.strip()]
    block = {"various artists", "various", "soundtrack"}
    return [p for p in parts if p.lower() not in block]


def build() -> None:

    # artists: dictionary says id/name ->
    # canonicalize to artist_mbid/artist_name
    _artists0 = read_parquet("artists")
    artists_raw = schema.require("artists", _artists0, ["artist_mbid", "name"]).rename(
        columns={"name": "artist_name"}
    )[["artist_mbid", "artist_name"]]

    # release_groups: accept name↔title and dash↔underscore variants
    _rgs0 = schema.canonicalize("release_groups", read_parquet("release_groups"))
    if "title" not in _rgs0.columns and "name" in _rgs0.columns:
        _rgs0 = _rgs0.rename(columns={"name": "title"})
    rgs_raw = schema.require(
        "release_groups",
        _rgs0,
        ["rg_mbid", "title", "primary_type", "first_release_date", "artist_credit"],
    )[
        ["rg_mbid", "title", "primary_type", "first_release_date", "artist_credit"]
    ].copy()

    # optional: genres table
    try:
        _eg0 = schema.canonicalize("entity_genres", read_parquet("entity_genres"))
        eg = schema.require(
            "entity_genres", _eg0, ["entity_type", "entity_mbid", "genre"]
        )[["entity_type", "entity_mbid", "genre"]]
    except Exception:
        eg = pd.DataFrame(columns=["entity_type", "entity_mbid", "genre"])

    # ---- Patterns and maps ----
    patt = [
        (
            row.artist_mbid,
            row.artist_name,
            re.compile(rf"(?i)(?<!\w){re.escape(row.artist_name)}(?!\w)"),
        )
        for row in artists_raw.itertuples(index=False)
        if isinstance(row.artist_name, str) and row.artist_name.strip()
    ]
    name_to_id = dict(
        artists_raw.rename(columns={"artist_mbid": "artist_id"})[
            ["artist_name", "artist_id"]
        ].itertuples(index=False, name=None)
    )

    # ---- Artist discography (for ID-based collabs) ----
    disc_rows = []
    for rg in rgs_raw.dropna(subset=["artist_credit"]).itertuples(index=False):
        credit = rg.artist_credit or ""
        hits = [(mbid, name) for (mbid, name, rx) in patt if rx.search(credit)]
        seen, dedup = set(), []
        for mbid, name in hits:
            if mbid not in seen:
                seen.add(mbid)
                dedup.append((mbid, name))
        if len(dedup) < 2:
            for nm in split_credit(credit):
                mbid = name_to_id.get(nm)
                if mbid and mbid not in seen:
                    seen.add(mbid)
                    dedup.append((mbid, nm))
        for mbid, name in dedup:
            disc_rows.append(
                {
                    "artist_mbid": mbid,
                    "artist_name": name,
                    "rg_mbid": rg.rg_mbid,
                    "rg_title": rg.title,
                    "primary_type": rg.primary_type,
                    "first_release_date": rg.first_release_date,
                    "first_release_year": rg.first_release_year,
                }
            )

    artist_discog = (
        pd.DataFrame(
            disc_rows,
            columns=[
                "artist_mbid",
                "artist_name",
                "rg_mbid",
                "rg_title",
                "primary_type",
                "first_release_date",
                "first_release_year",
            ],
        ).drop_duplicates(["artist_mbid", "rg_mbid"])
        if disc_rows
        else pd.DataFrame(
            columns=[
                "artist_mbid",
                "artist_name",
                "rg_mbid",
                "rg_title",
                "primary_type",
                "first_release_date",
                "first_release_year",
            ]
        )
    )
    write_both(artist_discog, "artist_discography")

    # ---- Canonical marts ----
    artists = artists_raw.rename(columns={"artist_mbid": "artist_id"})[
        ["artist_id", "artist_name"]
    ].drop_duplicates()
    write_both(artists, "artists")

    prim_rows = []
    for rg in rgs_raw.itertuples(index=False):
        credit = rg.artist_credit or ""
        matches = [(mbid, name) for (mbid, name, rx) in patt if rx.search(credit)]
        artist_id = matches[0][0] if matches else None
        if artist_id is None:
            for nm in split_credit(credit):
                if nm in name_to_id:
                    artist_id = name_to_id[nm]
                    break
        if artist_id is None:
            continue
        prim_rows.append(
            {
                "release_group_id": rg.rg_mbid,
                "title": rg.title,
                "first_release_year": rg.first_release_year,
                "artist_id": artist_id,
            }
        )
    release_groups = pd.DataFrame(
        prim_rows,
        columns=["release_group_id", "title", "first_release_year", "artist_id"],
    ).dropna(subset=["artist_id"])
    if "first_release_year" in release_groups:
        release_groups["first_release_year"] = release_groups[
            "first_release_year"
        ].astype("Int64")
    write_both(release_groups, "release_groups")

    rg_by_year = (
        rgs_raw.dropna(subset=["first_release_year"])
        .assign(year=lambda d: d["first_release_year"].astype(int))
        .groupby("year", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    write_both(rg_by_year, "release_groups_by_year")

    if not eg.empty:
        rg_gen = eg[eg["entity_type"] == "release-group"].merge(
            rgs_raw[["rg_mbid", "first_release_year"]],
            left_on="entity_mbid",
            right_on="rg_mbid",
            how="left",
        )
        genres_by_decade = (
            rg_gen.dropna(subset=["genre", "first_release_year"])
            .assign(
                year=lambda d: d["first_release_year"].astype(int),
                decade=lambda d: (d["year"] // 10) * 10,
            )
            .groupby(["decade", "genre"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )
    else:
        genres_by_decade = pd.DataFrame(columns=["decade", "genre", "count"])
    write_both(genres_by_decade, "genres_by_decade")

    # ---- Collaborations (ID-based from discog) ----
    coll_rows = []
    if not artist_discog.empty:
        g = artist_discog[["artist_mbid", "rg_mbid"]].rename(
            columns={"artist_mbid": "artist_id", "rg_mbid": "release_group_id"}
        )
        for _, grp in g.groupby("release_group_id"):
            ids = sorted(set(grp["artist_id"]))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    coll_rows.append(
                        {"artist_id": ids[i], "peer_id": ids[j], "weight": 1}
                    )

    collabs = (
        pd.DataFrame(coll_rows)
        .groupby(["artist_id", "peer_id"], as_index=False)["weight"]
        .sum()
        .query("weight >= @MIN_EDGE_WEIGHT")
        if coll_rows
        else pd.DataFrame(columns=["artist_id", "peer_id", "weight"])
    )
    write_both(collabs, "artist_collaborations")

    # ---- Collaborations (Name-based from RG credit) ----
    pairs = []
    for rg in rgs_raw.dropna(subset=["artist_credit"]).itertuples(index=False):
        raw_names = [
            n
            for n in split_credit(rg.artist_credit or "")
            if n.lower() not in {"various", "various artists"}
        ]
        # canonicalize and de-dup within RG
        canon = sorted({norm_name(n) for n in raw_names if norm_name(n)})
        for i in range(len(canon)):
            for j in range(i + 1, len(canon)):
                pairs.append({"name_a": canon[i], "name_b": canon[j], "weight": 1})

    collabs_names = (
        pd.DataFrame(pairs)
        .groupby(["name_a", "name_b"], as_index=False)["weight"]
        .sum()
        .query("weight >= @MIN_EDGE_WEIGHT")
        if pairs
        else pd.DataFrame(columns=["name_a", "name_b", "weight"])
    )
    write_both(collabs_names, "artist_collaborations_names")

    # ---- Fallback from recordings.jsonl if both empty ----
    if collabs.empty and collabs_names.empty:
        rec_id, rec_name = collabs_from_recordings(RAW / "recordings.jsonl")
        if not rec_id.empty:
            write_both(rec_id, "artist_collaborations")
        if not rec_name.empty:
            write_both(rec_name, "artist_collaborations_names")

    print("[INFO] marts written:", MARTS.resolve())

    # ---- Figures ----
    primary = pd.read_csv(MARTS / "artist_collaborations.csv")
    collab_path = (
        str(MARTS / "artist_collaborations.csv")
        if not primary.empty
        else str(MARTS / "artist_collaborations_names.csv")
    )

    plot_collab_network(
        artists_csv=str(MARTS / "artists.csv"),
        collaborations_csv=collab_path,
        out_png=str(FIG_DIR / "collab_network.png"),
        top_n=120,
    )
    plot_genre_evolution(
        genres_by_decade_csv=str(MARTS / "genres_by_decade.csv"),
        out_png=str(FIG_DIR / "genre_evolution.png"),
        top_k=12,
    )
    print("[INFO] figures written:", FIG_DIR.resolve())


if __name__ == "__main__":
    build()
