import pandas as pd, os
BASE="data/marts"
def test_marts_exist():
    for f in ["artist_discography.parquet","collaboration_edges_weighted.parquet","genre_trends.parquet"]:
        assert os.path.exists(f"{BASE}/{f}")

def test_artist_discography_cols():
    df = pd.read_parquet(f"{BASE}/artist_discography.parquet")
    for c in ["artist_mbid","rg_mbid","rg_title","first_release_year"]:
        assert c in df.columns

def test_genre_trends_nonnegative():
    df = pd.read_parquet(f"{BASE}/genre_trends.parquet")
    assert (df["release_groups"]>=0).all()
