# app/viz/collab_network.py
from __future__ import annotations
from pathlib import Path
import pandas as pd
import networkx as nx
from pyvis.network import Network

MARTS = Path("data/marts")
FIGS = Path("docs/figures")
FIGS.mkdir(parents=True, exist_ok=True)


def _load_edges() -> pd.DataFrame:
    fp = MARTS / "producer_network.csv"
    if fp.exists():
        df = pd.read_csv(fp)
        if not df.empty and {
            "source_id",
            "source_name",
            "target_id",
            "target_name",
        }.issubset(df.columns):
            return df[["source_id", "source_name", "target_id", "target_name"]].dropna()

    # Fallback: name-based collaborations
    fp2 = MARTS / "artist_collaborations_names.csv"
    if not fp2.exists():
        return pd.DataFrame(
            columns=["source_id", "source_name", "target_id", "target_name"]
        )
    dn = pd.read_csv(fp2)
    req = {"name_a", "name_b"}
    if not req.issubset(dn.columns):
        return pd.DataFrame(
            columns=["source_id", "source_name", "target_id", "target_name"]
        )
    # keep top N by weight to avoid hairball
    if "weight" in dn.columns:
        dn = dn.sort_values("weight", ascending=False).head(600)
    dn = dn.rename(columns={"name_a": "source_name", "name_b": "target_name"})
    dn["source_id"] = dn["source_name"]
    dn["target_id"] = dn["target_name"]
    return dn[["source_id", "source_name", "target_id", "target_name"]].dropna()


def _build_graph(df: pd.DataFrame) -> nx.Graph:
    g = nx.Graph()
    if df is None or df.empty:
        return g

    # Build unique nodes keyed by id
    nodes: dict[str, str] = {}
    for _, r in df.iterrows():
        sid, sname = r.get("source_id"), r.get("source_name")
        tid, tname = r.get("target_id"), r.get("target_name")
        if pd.notna(sid):
            nodes.setdefault(str(sid), str(sname) if pd.notna(sname) else str(sid))
        if pd.notna(tid):
            nodes.setdefault(str(tid), str(tname) if pd.notna(tname) else str(tid))

    # Add nodes
    for nid, nname in nodes.items():
        g.add_node(nid, name=nname)

    # Add edges
    for _, r in df.iterrows():
        sid, tid = r.get("source_id"), r.get("target_id")
        if pd.notna(sid) and pd.notna(tid):
            g.add_edge(str(sid), str(tid))
    return g


def _centralities(g: nx.Graph) -> tuple[dict, dict]:
    deg = dict(g.degree())
    # betweenness on giant component for speed
    if g.number_of_nodes() == 0:
        return {}, {}
    largest_cc = max(nx.connected_components(g), key=len)
    bc = nx.betweenness_centrality(g.subgraph(largest_cc))
    # fill 0 for nodes not in largest cc
    for n in g.nodes:
        if n not in bc:
            bc[n] = 0.0
    return deg, bc


def _genres_lookup() -> dict[str, str]:
    # optional: pull genres from artist_roles.csv
    fp = MARTS / "artist_roles.csv"
    if not fp.exists():
        return {}
    df = pd.read_csv(fp, dtype=str)

    # many rows per artist; take the most frequent genre token in 'genres'
    def top_genre(s: pd.Series) -> str | None:
        tokens = []
        for v in s.dropna():
            tokens.extend([t.strip() for t in str(v).split(";") if t.strip()])
        if not tokens:
            return None
        return pd.Series(tokens).value_counts().idxmax()

    gdf = df.groupby("artist_id")["genres"].apply(top_genre).reset_index()
    return dict(zip(gdf["artist_id"], gdf["genres"].fillna("")))


def build_pyvis_html(out_name: str = "collab_network.html") -> str:
    df_edges = _load_edges()
    g = _build_graph(df_edges)
    deg, bc = _centralities(g)
    genres = _genres_lookup()
    print(f"[VIZ] nodes={g.number_of_nodes()} edges={g.number_of_edges()}")

    # lighter background
    net = Network(height="700px", width="100%", notebook=False, directed=False)

    # better physics for medium graphs
    net.barnes_hut(
        gravity=-2000,
        central_gravity=0.2,
        spring_length=160,
        spring_strength=0.02,
        damping=0.09,
    )

    # add nodes with tooltip and size
    for n, data in g.nodes(data=True):
        name = data.get("name", n)
        d = deg.get(n, 0)
        b = bc.get(n, 0.0)
        genre = genres.get(n, "")
        title = (
            f"<b>{name}</b><br>"
            f"MBID: {n}<br>"
            f"Genre: {genre or '—'}<br>"
            f"Degree: {d}<br>"
            f"Betweenness: {b:.3f}"
        )
        size = 8 + 2 * (d**0.6)  # sublinear
        net.add_node(n, label=name, title=title, value=d, size=size)

    # add edges
    for u, v in g.edges():
        net.add_edge(u, v, title="collaboration")

    # options: improve label readability
    net.set_options(
        """
    {
      "nodes": { "shape": "dot", "scaling": { "min": 6, "max": 36 }, "font": { "size": 12, "strokeWidth": 2 } },
      "edges": { "color": { "inherit": true }, "width": 1, "smooth": false },
      "interaction": { "hover": true, "tooltipDelay": 120, "hideEdgesOnDrag": false, "zoomView": true },
      "physics": { "stabilization": { "iterations": 150 } }
    }
    """
    )

    out_fp = FIGS / out_name
    net.save_graph(str(out_fp))
    print(f"[FIG] wrote {out_fp}")
    return str(out_fp)


def run():
    build_pyvis_html()


if __name__ == "__main__":
    run()
