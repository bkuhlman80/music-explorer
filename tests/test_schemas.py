# tests/test_schemas.py  
from pathlib import Path
import pandas as pd

BASE = Path("data/marts")

def read_any(name):
    p_csv = BASE / f"{name}.csv"
    p_parq = BASE / f"{name}.parquet"
    if p_csv.exists():
        return pd.read_csv(p_csv)
    return pd.read_parquet(p_parq)

def test_marts_exist():
    for name in ["artists", "release_groups", "release_groups_by_year"]:
        assert (BASE / f"{name}.csv").exists() or (BASE / f"{name}.parquet").exists()

def test_artists_schema():
    df = read_any("artists")
    for c in ["artist_id", "artist_name"]:
        assert c in df.columns

def test_release_groups_schema():
    df = read_any("release_groups")
    for c in ["release_group_id", "title", "first_release_year", "artist_id"]:
        assert c in df.columns

def test_release_groups_by_year_nonnegative():
    df = read_any("release_groups_by_year")
    assert {"year", "count"}.issubset(df.columns)
    assert (df["count"] >= 0).all()
