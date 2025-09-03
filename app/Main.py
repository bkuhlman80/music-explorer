# app/Main.py
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

# Must be first
st.set_page_config(page_title="Music Explorer", layout="wide")

DATA_DIR = Path("data/marts")
FIG_DIR = Path("docs/figures")
TODAY = dt.date.today().isoformat()

st.caption(
    f"Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {TODAY}. "
    "Music metadata provided by MusicBrainz."
)


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    """Read marts CSV. Warn if missing, return empty DataFrame instead of None."""
    fp = DATA_DIR / f"{name}.csv"
    if not fp.exists():
        st.warning(f"Missing {fp}. Build locally then push, or rerun CI.")
        return pd.DataFrame()
    return pd.read_csv(fp)


def metric_int(label: str, value) -> None:
    try:
        st.metric(label, int(value))
    except Exception:
        st.metric(label, value)


# ---- Sidebar ----
PAGES = ["Overview", "Explore", "Download"]
with st.sidebar:
    page = st.radio("Pages", PAGES)
    if st.button("Clear cache"):
        st.cache_data.clear()
        st.success("Cache cleared")

# ---- Load marts shared across pages ----
artists = load_csv("artists")  # artist_id, artist_name
discog = load_csv("artist_discography")  # artist_mbid, artist_name, rg_mbid, ...
edges_names = load_csv("artist_collaborations_names")  # name_a, name_b, weight
rg_by_year = load_csv("release_groups_by_year")  # year, count
genres_by_decade = load_csv("genres_by_decade")  # decade, genre, count

# ---- Overview ----
if page == "Overview":
    st.title("Music Explorer")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_int("Artists", len(artists))
    with c2:
        n_rgs = discog["rg_mbid"].nunique() if "rg_mbid" in discog.columns else 0
        metric_int("Release groups", n_rgs)
    with c3:
        metric_int("Collab edges (names)", len(edges_names))
    with c4:
        metric_int("PNG exists", int((FIG_DIR / "collab_network.png").exists()))

    with st.expander("Debug"):
        st.write(
            {
                "artists.csv": artists.shape,
                "artist_discography.csv": discog.shape,
                "artist_collaborations_names.csv": edges_names.shape,
                "release_groups_by_year.csv": rg_by_year.shape,
                "genres_by_decade.csv": genres_by_decade.shape,
            }
        )

    st.subheader("Release groups per year")
    if not rg_by_year.empty and {"year", "count"}.issubset(rg_by_year.columns):
        rgp = rg_by_year.sort_values("year").set_index("year")["count"]
        st.line_chart(rgp, use_container_width=True)
        st.caption(
            f"Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {TODAY}. "
            "Music metadata provided by MusicBrainz."
        )
    else:
        st.info("release_groups_by_year.csv missing or empty.")

    st.subheader("Genre evolution by decade")
    if not genres_by_decade.empty and {"decade", "genre", "count"}.issubset(
        genres_by_decade.columns
    ):
        pivot = (
            genres_by_decade.pivot_table(
                index="decade", columns="genre", values="count", aggfunc="sum"
            )
            .fillna(0)
            .sort_index()
        )
        st.area_chart(pivot, use_container_width=True)
        st.caption(
            f"Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {TODAY}. "
            "Music metadata provided by MusicBrainz."
        )
    else:
        st.info("genres_by_decade.csv missing or empty.")

    st.subheader("Collaboration network")
    png = FIG_DIR / "collab_network.png"
    svg = FIG_DIR / "collab_network.svg"
    if png.exists():
        st.image(str(png), use_container_width=True)
        if svg.exists():
            st.download_button(
                "Download SVG",
                data=svg.read_bytes(),
                file_name="collab_network.svg",
                mime="image/svg+xml",
                type="primary",
            )
        st.caption(
            f"Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {TODAY}. "
            "Music metadata provided by MusicBrainz."
        )
    else:
        st.info("No figure yet. Run: `python -m app.pipeline.build`")

# ---- Explore ----
elif page == "Explore":
    st.title("Explore")
    if discog.empty or "artist_name" not in discog.columns:
        st.info("artist_discography.csv not available.")
        st.stop()

    artist = st.selectbox("Artist", sorted(discog["artist_name"].dropna().unique()))
    sub = discog.loc[discog["artist_name"] == artist].sort_values("first_release_year")

    st.markdown("**Discography**")
    st.dataframe(
        sub[["rg_title", "primary_type", "first_release_year"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("**Collaborators (name-based edges)**")
    if edges_names.empty or not {"name_a", "name_b", "weight"}.issubset(
        edges_names.columns
    ):
        st.info("artist_collaborations_names.csv not available.")
    else:
        a = artist.casefold()
        df = edges_names.copy()
        df["a"] = df["name_a"].astype(str).str.casefold()
        df["b"] = df["name_b"].astype(str).str.casefold()
        mask = (df["a"] == a) | (df["b"] == a)
        partners = (
            df.loc[mask]
            .assign(
                partner=lambda d: d.apply(
                    lambda r: r["name_b"] if r["a"] == a else r["name_a"], axis=1
                )
            )[["partner", "weight"]]
            .groupby("partner", as_index=False)["weight"]
            .sum()
            .sort_values("weight", ascending=False)
        )
        if partners.empty:
            st.info("No collaboration edges for this artist in current sample.")
        else:
            st.bar_chart(
                partners.set_index("partner")["weight"], use_container_width=True
            )

# ---- Download ----
else:
    st.title("Download")
    files = [
        "artists",
        "artist_discography",
        "artist_collaborations",
        "artist_collaborations_names",
        "release_groups_by_year",
        "genres_by_decade",
    ]
    for name in files:
        df = load_csv(name)
        if df.empty:
            st.warning(f"{name}.csv not available.")
        else:
            st.download_button(
                f"Download {name}.csv",
                df.to_csv(index=False),
                file_name=f"{name}.csv",
                mime="text/csv",
            )
