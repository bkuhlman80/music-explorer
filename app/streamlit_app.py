import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import networkx as nx  # for fallback network render

st.set_page_config(page_title="Music Explorer", layout="wide")


def _mtime(name: str) -> float:
    p1 = Path("data/marts") / f"{name}.parquet"
    p2 = p1.with_suffix(".csv")
    t = 0.0
    if p1.exists():
        t = max(t, p1.stat().st_mtime)
    if p2.exists():
        t = max(t, p2.stat().st_mtime)
    return t


@st.cache_data
def load(name, mtime: float):
    p = Path("data/marts") / f"{name}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    p_csv = p.with_suffix(".csv")
    if p_csv.exists():
        return pd.read_csv(p_csv)
    return pd.DataFrame()  # empty fallback


st.title("Music Explorer")
st.caption("Reads marts only. No live API calls.")

tab1, tab2, tab3 = st.tabs(["Releases by Year", "Genres by Decade", "Collab Network"])

# ---------- Releases by Year ----------
with tab1:
    rg_year = load("release_groups_by_year", _mtime("release_groups_by_year"))
    # normalize columns
    if "release_groups" in rg_year.columns:
        rg_year = rg_year.rename(columns={"release_groups": "count"})
    if "size" in rg_year.columns:
        rg_year = rg_year.rename(columns={"size": "count"})

    # if mart empty/malformed, rebuild from release_groups
    if rg_year.empty or not {"year", "count"}.issubset(rg_year.columns):
        rg = load("release_groups")
        if not rg.empty and {"first_release_year"}.issubset(rg.columns):
            tmp = rg.dropna(subset=["first_release_year"]).copy()
            if not tmp.empty:
                tmp["year"] = tmp["first_release_year"].astype(int)
                rg_year = (
                    tmp.groupby("year", as_index=False)
                    .size()
                    .rename(columns={"size": "count"})
                )
        # else keep empty

    if rg_year.empty:
        st.info("No year data available.")
    else:
        rg_year = rg_year.dropna(subset=["year", "count"]).copy()
        rg_year["year"] = rg_year["year"].astype(int)
        years = sorted(rg_year["year"].unique().tolist())
        y0, y1 = years[0], years[-1]
        ysel = st.slider("Year range", y0, y1, (y0, y1))
        view = rg_year[(rg_year["year"] >= ysel[0]) & (rg_year["year"] <= ysel[1])]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(view["year"], view["count"])
        ax.set_title("Release groups per year")
        ax.set_xlabel("Year")
        ax.set_ylabel("Count")
        st.pyplot(fig, clear_figure=True)

# ---------- Genres by Decade ----------
with tab2:
    gdec = load("genres_by_decade", _mtime("genres_by_decade"))
    if "releases" not in gdec.columns and "count" in gdec.columns:
        gdec = gdec.rename(columns={"count": "releases"})
    need = {"decade", "genre", "releases"}
    if not need.issubset(gdec.columns) or gdec.empty:
        st.info("No genre-by-decade data available.")
    else:
        gdec = gdec.dropna(subset=list(need))
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
            .sort_index()
        )
        fig, ax = plt.subplots(figsize=(8, 4))
        pv.plot(ax=ax)
        ax.set_title("Genre evolution by decade")
        ax.set_xlabel("Decade")
        ax.set_ylabel("Releases")
        st.pyplot(fig, clear_figure=True)

# ---------- Collab Network ----------
with tab3:
    artists = load("artists", _mtime("artists"))

    # Prefer names-based mart; fall back to ID mart
    edges = load("artist_collaborations_names", _mtime("artist_collaborations_names"))
    mode = "name" if not edges.empty else "id"
    if edges.empty:
        edges = load("artist_collaborations", _mtime("artist_collaborations"))

    # Normalize → src, dst, w
    if {"name_a", "name_b", "weight"}.issubset(edges.columns):
        edges = edges.rename(columns={"name_a": "src", "name_b": "dst", "weight": "w"})
        mode = "name"
    elif {"artist_id", "peer_id", "weight"}.issubset(edges.columns):
        edges = edges.rename(
            columns={"artist_id": "src", "peer_id": "dst", "weight": "w"}
        )
        mode = "id"
    elif {"artist_id", "collab_id", "w"}.issubset(edges.columns):
        edges = edges.rename(columns={"artist_id": "src", "collab_id": "dst"})
        mode = "id"
    else:
        edges = pd.DataFrame(columns=["src", "dst", "w"])

    with st.expander("Debug: collaboration marts"):
        st.write(
            {
                "mode": mode,
                "names_rows": int(
                    load(
                        "artist_collaborations_names",
                        _mtime("artist_collaborations_names"),
                    ).shape[0]
                ),
                "id_rows": int(
                    load(
                        "artist_collaborations", _mtime("artist_collaborations")
                    ).shape[0]
                ),
            }
        )
        st.dataframe(edges.head(10))

    if edges.empty:
        st.info("No collaborations found. Try a larger sample and rebuild.")
    else:
        # reduce to <=120 nodes by weighted degree
        deg_long = pd.concat(
            [
                edges.rename(columns={"src": "id"})[["id", "w"]],
                edges.rename(columns={"dst": "id"})[["id", "w"]],
            ],
            ignore_index=True,
        )
        keep = (
            deg_long.groupby("id")["w"]
            .sum()
            .sort_values(ascending=False)
            .head(min(120, deg_long["id"].nunique()))
            .index
        )
        sub = edges[edges["src"].isin(keep) & edges["dst"].isin(keep)]

        if sub.empty:
            st.info(
                "Collaborations exist but were all filtered. Reduce ‘top N’ or pull more data."
            )
        else:
            import networkx as nx

            G = nx.Graph()
            G.add_weighted_edges_from(
                sub[["src", "dst", "w"]].itertuples(index=False, name=None)
            )

            if G.number_of_edges() == 0:
                st.info("Not enough co-credits to draw a graph.")
            else:
                name_map = (
                    artists.set_index("artist_id")["artist_name"].to_dict()
                    if mode == "id"
                    else {}
                )
                pos = nx.spring_layout(G, k=0.35, seed=42, weight="weight")
                fig = plt.figure(figsize=(8, 6))

                wmax = float(sub["w"].max())
                ewidths = [
                    0.5 + 2.5 * (d.get("weight", 1.0) / wmax)
                    for _, _, d in G.edges(data=True)
                ]
                nd = dict(G.degree(weight="weight"))
                nsmax = max(nd.values())
                nsizes = [50 + 250 * (nd[n] / nsmax) for n in G.nodes]

                nx.draw_networkx_nodes(G, pos, node_size=nsizes, alpha=0.85)
                nx.draw_networkx_edges(G, pos, width=ewidths, alpha=0.25)

                top_labels = set(sorted(nd, key=lambda x: nd[x], reverse=True)[:25])
                labels = {
                    n: (name_map.get(n, str(n)) if mode == "id" else str(n))
                    for n in top_labels
                }
                nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)

                plt.title("Artist collaboration clusters")
                st.pyplot(fig, clear_figure=True)
