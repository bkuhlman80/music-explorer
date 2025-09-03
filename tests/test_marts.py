import os
from pathlib import Path
import pandas as pd
import pytest

BASE = Path("data/marts")


def _read_any(name: str) -> pd.DataFrame:
    p_csv = BASE / f"{name}.csv"
    p_parq = BASE / f"{name}.parquet"
    if p_csv.exists():
        return pd.read_csv(p_csv)
    if p_parq.exists():
        return pd.read_parquet(p_parq)
    return pd.DataFrame()


def test_marts_exist():
    for name in ["artists", "release_groups", "release_groups_by_year"]:
        assert (BASE / f"{name}.csv").exists() or (BASE / f"{name}.parquet").exists()


def test_artists_csv_schema():
    df = _read_any("artists")
    assert {"artist_id", "artist_name"}.issubset(df.columns)
    if os.getenv("REQUIRE_DATA") == "1":
        assert len(df) > 0


def test_release_groups_schema():
    df = _read_any("release_groups")
    assert {"release_group_id", "title", "first_release_year", "artist_id"}.issubset(
        df.columns
    )
    if os.getenv("REQUIRE_DATA") == "1":
        assert len(df) > 0


def test_release_groups_by_year_nonnegative():
    df = _read_any("release_groups_by_year")
    assert {"year", "count"}.issubset(df.columns)
    assert (df["count"] >= 0).all()


def test_names_mart_schema():
    p = BASE / "artist_collaborations_names.csv"
    if not p.exists():
        pytest.skip("names mart not emitted")
    df = pd.read_csv(p)
    assert {"name_a", "name_b", "weight"}.issubset(df.columns)
    if os.getenv("REQUIRE_DATA") == "1":
        assert len(df) > 0
