# app/pipeline/marts_relations.py
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/clean")
MARTS_DIR = Path("data/marts")
MARTS_DIR.mkdir(parents=True, exist_ok=True)


def _read_jsonl(fp: Path) -> list[dict]:
    if not fp.exists():
        return []
    with fp.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _safe(x, *keys):
    cur = x
    for k in keys:
        if cur is None:
            return None
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur


def build_artist_roles(artist_objs: list[dict]) -> pd.DataFrame:
    cols = [
        "artist_id",
        "artist_name",
        "role_type",
        "target_type",
        "target_id",
        "area",
        "tags",
        "genres",
    ]
    if not artist_objs:
        return pd.DataFrame(columns=cols)

    rows = []
    for a in artist_objs:
        a_id = a.get("id")
        a_name = a.get("name")
        area = (a.get("area") or {}).get("name")
        tags = [t.get("name") for t in (a.get("tags") or []) if isinstance(t, dict)]
        genres = [g.get("name") for g in (a.get("genres") or []) if isinstance(g, dict)]

        for rel in a.get("relations") or []:
            rtype = rel.get("type")
            ttype = rel.get("target-type")
            if rtype in {
                "producer",
                "remixer",
                "engineer",
                "composer",
                "lyricist",
                "vocal supporting",
                "performer",
            }:
                tid = None
                if ttype == "artist":
                    tid = (rel.get("artist") or {}).get("id")
                elif ttype == "work":
                    tid = (rel.get("work") or {}).get("id")
                elif ttype == "recording":
                    tid = (rel.get("recording") or {}).get("id")
                elif ttype in {"release_group", "release-group"}:
                    tid = (rel.get("release-group") or {}).get("id")
                rows.append(
                    {
                        "artist_id": a_id,
                        "artist_name": a_name,
                        "role_type": rtype,
                        "target_type": ttype,
                        "target_id": tid,
                        "area": area,
                        "tags": ";".join(tags) if tags else None,
                        "genres": ";".join(genres) if genres else None,
                    }
                )

    df = pd.DataFrame(rows, columns=cols)
    return df if not df.empty else pd.DataFrame(columns=cols)


def build_producer_network(artist_roles: pd.DataFrame) -> pd.DataFrame:
    cols = ["source_id", "source_name", "target_id_artist", "target_name", "target_id"]
    if artist_roles is None or artist_roles.empty:
        return pd.DataFrame(columns=cols)

    df = artist_roles.copy()
    if "role_type" not in df.columns or "target_id" not in df.columns:
        return pd.DataFrame(columns=cols)

    producers = df[df["role_type"].str.contains("producer", na=False)]
    performers = df[
        df["role_type"].str.contains("performer|vocal", na=False, regex=True)
    ]
    if producers.empty or performers.empty:
        return pd.DataFrame(columns=cols)

    edges = producers.merge(performers, on="target_id", suffixes=("_prod", "_perf"))
    edges = edges.rename(
        columns={
            "artist_id_prod": "source_id",
            "artist_name_prod": "source_name",
            "artist_id_perf": "target_id_artist",
            "artist_name_perf": "target_name",
        }
    )
    keep = ["source_id", "source_name", "target_id_artist", "target_name", "target_id"]
    if not set(keep).issubset(edges.columns):
        return pd.DataFrame(columns=cols)
    return (
        edges[keep].dropna(subset=["source_id", "target_id_artist"]).drop_duplicates()
    )


def build_label_affiliations(
    artist_objs: list[dict], rg_objs: list[dict]
) -> pd.DataFrame:
    cols = [
        "artist_id",
        "artist_name",
        "label_id",
        "label_name",
        "relation_type",
        "begin",
        "end",
    ]
    rows = []

    for a in artist_objs or []:
        a_id, a_name = a.get("id"), a.get("name")
        for rel in a.get("relations") or []:
            if rel.get("target-type") == "label":
                lab = rel.get("label") or {}
                rows.append(
                    {
                        "artist_id": a_id,
                        "artist_name": a_name,
                        "label_id": lab.get("id"),
                        "label_name": lab.get("name"),
                        "relation_type": rel.get("type"),
                        "begin": rel.get("begin"),
                        "end": rel.get("end"),
                    }
                )

    for rg in rg_objs or []:
        for rel in rg.get("relations") or []:
            if rel.get("target-type") == "label":
                lab = rel.get("label") or {}
                for ac in rg.get("artist-credit") or []:
                    art = ac.get("artist") or {}
                    rows.append(
                        {
                            "artist_id": art.get("id"),
                            "artist_name": art.get("name"),
                            "label_id": lab.get("id"),
                            "label_name": lab.get("name"),
                            "relation_type": rel.get("type"),
                            "begin": rel.get("begin"),
                            "end": rel.get("end"),
                        }
                    )

    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return pd.DataFrame(columns=cols)
    return df.dropna(subset=["artist_id", "label_id"]).drop_duplicates()


def build_releases_by_country_year(rg_objs: list[dict]) -> pd.DataFrame:
    rows = []
    for rg in rg_objs:
        # Use first-release-date at RG level when present
        y = None
        frd = rg.get("first-release-date")
        if frd and len(frd) >= 4:
            try:
                y = int(frd[:4])
            except Exception:
                y = None
        country = None
        # Try primary release’s country via 'releases' if present in payload
        for rel in rg.get("releases", []) or []:
            country = rel.get("country") or country
        for ac in rg.get("artist-credit", []):
            a = ac.get("artist", {})
            rows.append(
                {
                    "release_group_id": rg.get("id"),
                    "year": y,
                    "country": country,
                    "artist_id": a.get("id"),
                    "artist_name": a.get("name"),
                }
            )
    df = pd.DataFrame(rows)
    return df.dropna(subset=["year"]).astype({"year": "int64"})


def build_collab_matrix(rg_objs: list[dict]) -> pd.DataFrame:
    # Count co-credit by genre pairs across RGs
    rows = []
    for rg in rg_objs:
        genres = sorted(
            {
                g.get("name")
                for g in rg.get("genres", [])
                if isinstance(g, dict) and g.get("name")
            }
        )
        if len(genres) < 1:
            continue
        # co-appearances: include diagonal to show self-collab frequency
        for g1 in genres:
            for g2 in genres:
                rows.append({"genre_1": g1, "genre_2": g2, "n": 1})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.groupby(["genre_1", "genre_2"], as_index=False)["n"].sum()


def run():
    artist_objs = _read_jsonl(Path("data/raw/artist_relations.jsonl"))
    rg_objs = _read_jsonl(Path("data/raw/release_group_relations.jsonl"))

    artist_roles = build_artist_roles(artist_objs)
    label_aff = build_label_affiliations(artist_objs, rg_objs)
    prod_net = build_producer_network(artist_roles)
    r_by_cy = build_releases_by_country_year(rg_objs)
    collab_mat = build_collab_matrix(rg_objs)

    out = {
        "artist_roles.csv": artist_roles,
        "label_affiliations.csv": label_aff,
        "producer_network.csv": prod_net,
        "releases_by_country_year.csv": r_by_cy,
        "collab_matrix.csv": collab_mat,
    }
    for name, df in out.items():
        (MARTS_DIR / name).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(MARTS_DIR / name, index=False)
    print("[INFO] marts written:", MARTS_DIR.resolve())


if __name__ == "__main__":
    run()
