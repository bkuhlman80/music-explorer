# app/figures/collab_network.py
from __future__ import annotations

from pathlib import Path
from datetime import date

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

CAPTION = (
    "Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {pulled}. "
    '"Music metadata provided by MusicBrainz."'
)


def plot_collab_network(
    artists_csv: str,
    collaborations_csv: str,
    out_png: str,
    top_n: int = 100,
) -> str:
    artists = pd.read_csv(artists_csv)
    edges = pd.read_csv(collaborations_csv)

    # normalize → src, dst, w
    mode = "id"
    if {"artist_id", "peer_id", "weight"}.issubset(edges.columns):
        edges = edges.rename(
            columns={"artist_id": "src", "peer_id": "dst", "weight": "w"}
        )
    elif {"artist_id", "collab_id", "w"}.issubset(edges.columns):
        edges = edges.rename(columns={"artist_id": "src", "collab_id": "dst"})
    elif {"name_a", "name_b", "weight"}.issubset(edges.columns):
        mode = "name"
        edges = edges.rename(columns={"name_a": "src", "name_b": "dst", "weight": "w"})
    else:
        _write_empty(out_png, "Artist collaboration clusters")
        return out_png

    if edges.empty:
        _write_empty(out_png, "Artist collaboration clusters")
        return out_png

    # top-N by weighted degree
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
        .head(min(top_n, deg_long["id"].nunique()))
        .index
    )
    sub = edges[edges["src"].isin(keep) & edges["dst"].isin(keep)]
    if sub.empty:
        _write_empty(out_png, "Artist collaboration clusters")
        return out_png

    # graph
    G = nx.Graph()
    G.add_weighted_edges_from(
        sub[["src", "dst", "w"]].itertuples(index=False, name=None)
    )

    # labels
    if mode == "id":
        name_map = artists.set_index("artist_id")["artist_name"].to_dict()
        labels_lookup = {n: name_map.get(n, str(n)) for n in G.nodes}
    else:
        labels_lookup = {n: str(n) for n in G.nodes}

    # draw
    pos = nx.spring_layout(G, k=0.35, seed=42, weight="weight")
    fig = plt.figure(figsize=(10, 8))

    wmax = float(sub["w"].max())
    ewidths = [
        0.5 + 2.5 * (d.get("weight", 1.0) / wmax) for _, _, d in G.edges(data=True)
    ]
    nd = dict(G.degree(weight="weight"))
    nsmax = max(nd.values())
    nsizes = [50 + 250 * (nd[n] / nsmax) for n in G.nodes]

    nx.draw_networkx_nodes(G, pos, node_size=nsizes, alpha=0.85)
    nx.draw_networkx_edges(G, pos, width=ewidths, alpha=0.25)

    top_labels = set(sorted(nd, key=lambda x: nd[x], reverse=True)[:25])
    nx.draw_networkx_labels(
        G, pos, labels={n: labels_lookup[n] for n in top_labels}, font_size=8
    )

    plt.title("Artist collaboration clusters")
    plt.figtext(
        0.5,
        0.01,
        CAPTION.format(pulled=date.today().isoformat()),
        ha="center",
        fontsize=8,
    )
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    return out_png


def _write_empty(out_png: str, title: str) -> None:
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(10, 8))
    plt.title(title)
    plt.figtext(
        0.5,
        0.01,
        CAPTION.format(pulled=date.today().isoformat()),
        ha="center",
        fontsize=8,
    )
    plt.axis("off")
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
