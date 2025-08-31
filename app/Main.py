import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Music Explorer", layout="wide")

DATA_DIR = Path("data/marts")

@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    fp = DATA_DIR / f"{name}.csv"
    if not fp.exists():
        raise FileNotFoundError(f"Missing file: {fp}")
    return pd.read_csv(fp)

def metric_int(label, value):
    try:
        st.metric(label, int(value))
    except Exception:
        st.metric(label, value)

PAGES = ["Overview","Explore","Download"]
page = st.sidebar.radio("Pages", PAGES)

if page == "Overview":
    st.title("Music Explorer")
    st.caption("Data: MusicBrainz (CC BY-NC-SA 4.0).")
    
    import numpy as np
    import pathlib

    kpi_file = pathlib.Path("data/marts/kpi_latency_samples.csv")
    if kpi_file.exists():
        dfk = pd.read_csv(kpi_file)
        mean_ms = int(dfk["elapsed_ms"].mean())
        st.metric("Avg query latency (ms)", f"{mean_ms} ms", help="Target ≤ 3000 ms")
    else:
        st.info("No KPI samples yet. Run `make pull` to collect timings.")

    try:
        d1 = load_csv("artist_discography")
        metric_int("Release groups", d1["rg_mbid"].nunique())
    except Exception as e:
        st.error(f"artist_discography load failed: {e}")
        st.stop()

    try:
        g = load_csv("genre_trends")
        if not g.empty and {"year","genre","release_groups"}.issubset(g.columns):
            pivot = g.pivot_table(index="year", columns="genre", values="release_groups", aggfunc="sum").fillna(0)
            st.line_chart(pivot)
        else:
            st.info("genre_trends.csv is empty or missing required columns.")
    except Exception as e:
        st.error(f"genre_trends load failed: {e}")

elif page == "Explore":
    try:
        d1 = load_csv("artist_discography")
    except Exception as e:
        st.error(f"artist_discography load failed: {e}")
        st.stop()

    if d1.empty or "artist_name" not in d1.columns:
        st.info("artist_discography has no rows or missing artist_name.")
    else:
        artist = st.selectbox("Artist", sorted(d1["artist_name"].dropna().unique()))
        sub = d1[d1["artist_name"]==artist].sort_values("first_release_year")
        st.dataframe(sub[["rg_title","primary_type","first_release_year"]], use_container_width=True)

    try:
        ew = load_csv("collaboration_edges_weighted")
        if not ew.empty and {"a_name","b_name","total_weight"}.issubset(ew.columns):
            # derive a one-column series for bar chart keys
            a = st.selectbox("Collaborator seed", sorted(set(ew["a_name"]).union(ew["b_name"])))
            mask = (ew["a_name"]==a)|(ew["b_name"]==a)
            sub = ew[mask].copy()
            sub["partner"] = sub.apply(lambda r: r["b_name"] if r["a_name"]==a else r["a_name"], axis=1)
            st.bar_chart(sub.set_index("partner")["total_weight"])
        else:
            st.info("No collaboration edges found yet.")
    except Exception as e:
        st.error(f"collaboration_edges_weighted load failed: {e}")

elif page == "Download":
    for name in ["artist_discography","collaboration_edges_weighted","genre_trends"]:
        try:
            df = load_csv(name)
            st.download_button(f"Download {name}.csv", df.to_csv(index=False), file_name=f"{name}.csv")
        except Exception as e:
            st.error(f"{name} not available: {e}")
