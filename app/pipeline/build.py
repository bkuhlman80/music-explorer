# app/pipeline/build.py
from __future__ import annotations
import os, re, pandas as pd

CLEAN = "data/clean"
MARTS = "data/marts"
os.makedirs(MARTS, exist_ok=True)


def read(name: str) -> pd.DataFrame:
    return pd.read_parquet(f"{CLEAN}/{name}.parquet")


def write_both(df: pd.DataFrame, base: str) -> None:
    df.to_csv(f"{MARTS}/{base}.csv", index=False)
    df.to_parquet(f"{MARTS}/{base}.parquet", index=False)


def build():
    # ---- Load clean layer ----
    artists_raw = read("artists")[["artist_mbid", "name"]].rename(
        columns={"name": "artist_name"}
    )
    rgs_raw = read("release_groups")[
        ["rg_mbid", "title", "primary_type", "first_release_date", "artist_credit"]
    ].copy()
    rgs_raw["first_release_year"] = pd.to_datetime(
        rgs_raw["first_release_date"], errors="coerce"
    ).dt.year
    eg = read("entity_genres")[["entity_type", "entity_mbid", "genre"]]

    # ---- Artist discography (compat mart you already had) ----
    patt = [
        (
            row.artist_mbid,
            row.artist_name,
            re.compile(rf"(?i)(?<!\w){re.escape(row.artist_name)}(?!\w)"),
        )
        for row in artists_raw.itertuples(index=False)
        if isinstance(row.artist_name, str) and row.artist_name.strip()
    ]
    rows = []
    for rg in rgs_raw.dropna(subset=["artist_credit"]).itertuples(index=False):
        hits = [
            (mbid, name)
            for (mbid, name, rx) in patt
            if rx.search(rg.artist_credit or "")
        ]
        seen = set()
        dedup = []
        for mbid, name in hits:
            if mbid not in seen:
                seen.add(mbid)
                dedup.append((mbid, name))
        for mbid, name in dedup:
            rows.append(
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
    artist_discog = pd.DataFrame(
        rows,
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
    write_both(artist_discog, "artist_discography")  # keeps your prior outputs

    # ---- Canonical marts expected by tests ----

    # 1) artists
    artists = artists_raw.rename(columns={"artist_mbid": "artist_id"})[
        ["artist_id", "artist_name"]
    ].drop_duplicates()
    write_both(artists, "artists")

    # 2) release_groups with a single "primary" artist per RG (first regex match)
    #    fallback: if no regex match, try exact name split and match to artists table
    split_tokens = [" feat. ", " featuring ", " with ", " & ", ", ", " and "]

    def split_credit(s: str) -> list[str]:
        parts = [s or ""]
        for tok in split_tokens:
            parts = sum((p.split(tok) for p in parts), [])
        parts = [p.strip() for p in parts if p.strip()]
        block = {"various artists", "various", "soundtrack"}
        return [p for p in parts if p.lower() not in block]

    # map name -> mbid for fallback
    name_to_id = dict(
        artists[["artist_name", "artist_id"]].itertuples(index=False, name=None)
    )

    prim_rows = []
    for rg in rgs_raw.itertuples(index=False):
        credit = rg.artist_credit or ""
        # prefer regex match list used above
        matches = [(mbid, name) for (mbid, name, rx) in patt if rx.search(credit)]
        artist_id = None
        if matches:
            artist_id = matches[0][0]
        else:
            names = split_credit(credit)
            for nm in names:
                if nm in name_to_id:
                    artist_id = name_to_id[nm]
                    break
        if artist_id is None:
            continue  # drop unmatched RGs to satisfy FK tests
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
    # enforce integer year if present
    if "first_release_year" in release_groups:
        release_groups["first_release_year"] = release_groups[
            "first_release_year"
        ].astype("Int64")
    write_both(release_groups, "release_groups")

    # 3) release_groups_by_year
    rg_by_year = (
        release_groups.dropna(subset=["first_release_year"])
        .assign(year=lambda d: d["first_release_year"].astype(int))
        .groupby("year", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    write_both(rg_by_year, "release_groups_by_year")

    # 4) genres_by_decade
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
    write_both(genres_by_decade, "genres_by_decade")

    # 5) artist_collaborations (ids, weighted)
    # Use artist_discog to map RG -> participating artist IDs, then make undirected pairs
    coll_rows = []
    g = artist_discog[["artist_mbid", "rg_mbid"]].rename(
        columns={"artist_mbid": "artist_id", "rg_mbid": "release_group_id"}
    )
    for rg_id, grp in g.groupby("release_group_id"):
        ids = sorted(set(grp["artist_id"]))
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                coll_rows.append({"artist_id": ids[i], "peer_id": ids[j], "weight": 1})
    if coll_rows:
        collabs = (
            pd.DataFrame(coll_rows)
            .groupby(["artist_id", "peer_id"], as_index=False)["weight"]
            .sum()
        )
    else:
        collabs = pd.DataFrame(columns=["artist_id", "peer_id", "weight"])
    write_both(collabs, "artist_collaborations")

    print("Marts written to data/marts")


if __name__ == "__main__":
    build()
