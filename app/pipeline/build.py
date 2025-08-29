# app/pipeline/build.py
import os, pandas as pd, numpy as np

CLEAN = "data/clean"
MARTS = "data/marts"
os.makedirs(MARTS, exist_ok=True)

def read(name): return pd.read_parquet(f"{CLEAN}/{name}.parquet")

def artist_discography():
    import re
    artists = read("artists")[["artist_mbid","name"]].rename(columns={"name":"artist_name"})
    rgs = read("release_groups")[["rg_mbid","title","primary_type","first_release_date","artist_credit"]].copy()
    rgs["first_release_year"] = pd.to_datetime(rgs["first_release_date"], errors="coerce").dt.year
    rgs = rgs.dropna(subset=["artist_credit"])

    # Precompile regex for each artist to match whole words inside credit
    patt = [
        (row.artist_mbid, row.artist_name, re.compile(rf"(?i)(?<!\w){re.escape(row.artist_name)}(?!\w)"))
        for row in artists.itertuples(index=False)
        if isinstance(row.artist_name, str) and row.artist_name.strip()
    ]

    rows = []
    for rg in rgs.itertuples(index=False):
        hits = [(mbid, name) for (mbid, name, rx) in patt if rx.search(rg.artist_credit or "")]
        # de-dup while preserving order
        seen = set()
        dedup = []
        for mbid, name in hits:
            if mbid not in seen:
                seen.add(mbid); dedup.append((mbid, name))
        for mbid, name in dedup:
            rows.append({
                "artist_mbid": mbid,
                "artist_name": name,
                "rg_mbid": rg.rg_mbid,
                "rg_title": rg.title,
                "primary_type": rg.primary_type,
                "first_release_date": rg.first_release_date,
                "first_release_year": rg.first_release_year,
            })

    out = pd.DataFrame(rows, columns=[
        "artist_mbid","artist_name","rg_mbid","rg_title",
        "primary_type","first_release_date","first_release_year"
    ]).drop_duplicates(["artist_mbid","rg_mbid"])

    out.to_parquet(f"{MARTS}/artist_discography.parquet", index=False)
    out.to_csv(f"{MARTS}/artist_discography.csv", index=False)


def collaboration_edges():
    import pandas as pd
    rgs = read("release_groups")[["rg_mbid","title","first_release_date","artist_credit"]].copy()
    rgs = rgs.dropna(subset=["artist_credit"])
    if rgs.empty:
        # write empty outputs and return
        pd.DataFrame(columns=["a_name","b_name","rg_mbid","rg_title","rg_year","edge_weight"]).to_parquet(f"{MARTS}/collaboration_edges.parquet", index=False)
        pd.DataFrame(columns=["a_name","b_name","total_weight","first_year","last_year"]).to_parquet(f"{MARTS}/collaboration_edges_weighted.parquet", index=False)
        pd.DataFrame(columns=["a_name","b_name","total_weight","first_year","last_year"]).to_csv(f"{MARTS}/collaboration_edges_weighted.csv", index=False)
        return

    rgs["rg_year"] = pd.to_datetime(rgs["first_release_date"], errors="coerce").dt.year

    SPLIT_TOKENS = [" feat. ", " featuring ", " with ", " & ", ", ", " and "]
    def split_credit(s: str):
        parts = [s]
        for tok in SPLIT_TOKENS:
            parts = sum((p.split(tok) for p in parts), [])
        # remove “Various Artists”, “Soundtrack”, empty, and duplicates
        blocklist = {"various artists","various","soundtrack"}
        out = []
        for p in parts:
            p2 = p.strip()
            if not p2: 
                continue
            if p2.lower() in blocklist:
                continue
            if p2 not in out:
                out.append(p2)
        return out

    rows = []
    for _, r in rgs.iterrows():
        names = split_credit(r["artist_credit"])
        if len(names) < 2:
            continue
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                a, b = sorted([names[i], names[j]])
                rows.append({
                    "a_name": a,
                    "b_name": b,
                    "rg_mbid": r["rg_mbid"],
                    "rg_title": r["title"],
                    "rg_year": r["rg_year"],
                    "edge_weight": 1
                })

    if not rows:
        pd.DataFrame(columns=["a_name","b_name","rg_mbid","rg_title","rg_year","edge_weight"]).to_parquet(f"{MARTS}/collaboration_edges.parquet", index=False)
        pd.DataFrame(columns=["a_name","b_name","total_weight","first_year","last_year"]).to_parquet(f"{MARTS}/collaboration_edges_weighted.parquet", index=False)
        pd.DataFrame(columns=["a_name","b_name","total_weight","first_year","last_year"]).to_csv(f"{MARTS}/collaboration_edges_weighted.csv", index=False)
        return

    edges = pd.DataFrame(rows)
    weighted = (edges.groupby(["a_name","b_name"], as_index=False)
                      .agg(total_weight=("edge_weight","sum"),
                           first_year=("rg_year","min"),
                           last_year=("rg_year","max")))
    edges.to_parquet(f"{MARTS}/collaboration_edges.parquet", index=False)
    weighted.to_parquet(f"{MARTS}/collaboration_edges_weighted.parquet", index=False)
    weighted.to_csv(f"{MARTS}/collaboration_edges_weighted.csv", index=False)

def genre_trends():
    rgs = read("release_groups")[["rg_mbid","first_release_date"]]
    rgs["year"] = pd.to_datetime(rgs["first_release_date"], errors="coerce").dt.year
    eg = read("entity_genres")[["entity_type","entity_mbid","genre"]]
    # Prefer RG genres
    rg_gen = eg[eg["entity_type"]=="release-group"].merge(rgs, left_on="entity_mbid", right_on="rg_mbid", how="left")
    # Fallback: none here yet; keep minimal
    gt = (rg_gen.dropna(subset=["year","genre"])
               .groupby(["year","genre"], as_index=False)
               .agg(release_groups=("rg_mbid","nunique")))
    gt["releases"] = 0
    gt["recordings"] = 0
    gt.to_parquet(f"{MARTS}/genre_trends.parquet", index=False)
    gt.to_csv(f"{MARTS}/genre_trends.csv", index=False)

def main():
    artist_discography()
    collaboration_edges()
    genre_trends()
    print("Marts written to data/marts")

if __name__ == "__main__":
    main()
