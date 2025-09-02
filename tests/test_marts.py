import pandas as pd


def test_names_mart_nonempty():
    df = pd.read_csv("data/marts/artist_collaborations_names.csv")
    assert len(df) > 0


def test_artists_csv_exists():
    df = pd.read_csv("data/marts/artists.csv")
    assert len(df) > 0 and set(df.columns) >= {"artist_id", "artist_name"}


def test_rg_by_year_monotonic():
    df = pd.read_csv("data/marts/release_groups_by_year.csv")
    assert df["year"].is_monotonic_increasing
