import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

st.set_page_config(page_title="Music Explorer", layout="wide")


@st.cache_data
def load(name):
    p = Path("data/marts") / f"{name}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return pd.read_csv(str(p.with_suffix(".csv")))


st.title("Music Explorer")
st.caption("Reads marts only. No live API calls.")

tab1, tab2, tab3 = st.tabs(["Releases by Year", "Genres by Decade", "Collab Network"])

with tab1:
    rg_year = load("release_groups_by_year")  # cols: year, release_groups
    rg_year = load("release_groups_by_year")
    if "release_groups" in rg_year.columns:
        rg_year = rg_year.rename(columns={"release_groups": "count"})
    y0, y1 = int(rg_year["year"].min()), int(rg_year["year"].max())
    ysel = st.slider("Year range", y0, y1, (y0, y1))
    view = rg_year[(rg_year["year"] >= ysel[0]) & (rg_year["year"] <= ysel[1])]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(view["year"], view["release_groups"])
    ax.set_title("Release groups per year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Count")
    st.pyplot(fig, clear_figure=True)

with tab2:
    gdec = load("genres_by_decade")  # decade, genre, releases
    top = (
        gdec.groupby("genre")["releases"]
        .sum()
        .sort_values(ascending=False)
        .head(12)
        .index
    )
    sel = st.multiselect("Genres", options=sorted(top), default=list(top)[:6])
    pv = (
        gdec[gdec["genre"].isin(sel)]
        .pivot(index="decade", columns="genre", values="releases")
        .fillna(0)
    )
    fig, ax = plt.subplots(figsize=(8, 4))
    pv.plot(ax=ax)
    ax.set_title("Genre evolution by decade")
    ax.set_xlabel("Decade")
    ax.set_ylabel("Releases")
    st.pyplot(fig, clear_figure=True)

with tab3:
    st.image("docs/figures/collab_network.png", caption="Artist collaboration clusters")
