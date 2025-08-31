from pathlib import Path
import pandas as pd
import pytest
from datetime import datetime, UTC

NOW_YEAR = datetime.now(UTC).year

MARTS = Path("data/marts")


def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        pytest.skip(f"missing {p}")
    return pd.read_csv(p)


def test_year_bounds_and_types():
    rg = load_csv(MARTS / "release_groups.csv")
    assert "first_release_year" in rg.columns
    years = rg["first_release_year"].dropna().astype(int)
    assert (years >= 1900).all(), "unexpected pre-1900 years"
    assert (years <= NOW_YEAR + 1).all(), "future years out of bounds"


def test_no_duplicate_artist_name_id_pairs():
    art = load_csv(MARTS / "artists.csv")
    assert art.duplicated(["artist_id", "artist_name"]).sum() == 0


def test_genre_counts_consistent_if_available():
    p = MARTS / "genres_by_decade.csv"
    g = pd.read_csv(p)
    req = {"decade", "genre", "count"}
    assert req.issubset(g.columns)
    assert (g["count"] >= 0).all()
    totals = g.groupby("decade")["count"].sum()
    assert (totals > 0).all(), "empty genre totals by decade"


def test_collaboration_edges_if_available():
    p = MARTS / "artist_collaborations.csv"
    e = pd.read_csv(p)
    req = {"artist_id", "peer_id", "weight"}
    assert req.issubset(e.columns)
    assert (e["artist_id"] != e["peer_id"]).all()
    assert (e["weight"] > 0).all()
