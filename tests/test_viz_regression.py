from pathlib import Path
import pandas as pd
import numpy as np

MARTS = Path("data/marts")
DOCS = Path("docs/figures")


def pct_diff(a, b):
    if b == 0 and a == 0:
        return 0.0
    return abs(a - b) / max(1, abs(b))


def load_csv(p: Path) -> pd.DataFrame:
    return pd.read_csv(p)


def test_rg_per_year_series_stable_within_1pct_if_two_paths_exist():
    # Path A: direct mart (preferred if present)
    path_a = MARTS / "release_groups_by_year.csv"
    path_b = MARTS / "release_groups.csv"
    a = pd.read_csv(path_a).rename(columns=str.lower)
    b = pd.read_csv(path_b).rename(columns=str.lower)
    assert {"year", "count"}.issubset(set(a.columns))
    assert {"first_release_year"}.issubset(set(b.columns))
    # Recompute from raw RGs
    b_agg = (
        b.dropna(subset=["first_release_year"])
        .assign(year=b["first_release_year"].astype(int))
        .groupby("year")
        .size()
        .reset_index(name="count")
    )
    merged = a.merge(b_agg, on="year", suffixes=("_a", "_b"))
    # Allow ±1% tolerance per year and overall
    per_year_ok = (
        merged.apply(lambda r: pct_diff(r["count_a"], r["count_b"]) <= 0.01, axis=1)
    ).all()
    overall_ok = pct_diff(merged["count_a"].sum(), merged["count_b"].sum()) <= 0.01
    assert per_year_ok and overall_ok, "rg/year drift >1%"


def test_hero_figure_exists():
    png = DOCS / "rg_per_year.png"
    assert png.exists(), "expected hero figure docs/figures/rg_per_year.png"
