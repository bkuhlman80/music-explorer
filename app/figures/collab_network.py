import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path
from datetime import date

CAPTION = 'Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {pulled}. "Music metadata provided by MusicBrainz."'


def plot_collab_network(
    artists_csv: str, collaborations_csv: str, out_png: str, top_n: int = 100
) -> str:
    artists = pd.read_csv(artists_csv)
    edges = pd.read_csv(collaborations_csv)

    # Normalize columns
    if {"artist_id", "peer_id", "weight"}.issubset(edges.columns):
        edges = edges.rename(columns={"peer_id": "collab_id", "weight": "w"})
    elif {"artist_id", "collab_id", "w"}.issubset(edges.columns):
        pass
    else:
        raise ValueError(
            "artist_collaborations requires (artist_id, peer_id/ collab_id, weight/w)"
        )

    deg = edges[["artist_id", "collab_id", "w"]].copy()

    # keep top_n by weighted degree
    deg_long = pd.concat(
        [
            deg.rename(columns={"artist_id": "id"})[["id", "w"]],
            deg.rename(columns={"collab_id": "id"})[["id", "w"]],
        ]
    )
    keep = (
        deg_long.groupby("id")["w"].sum().sort_values(ascending=False).head(top_n).index
    )
    sub = deg[deg["artist_id"].isin(keep) & deg["collab_id"].isin(keep)]

    G = nx.Graph()
    G.add_weighted_edges_from(
        sub[["artist_id", "collab_id", "w"]].itertuples(index=False, name=None)
    )

    name_map = artists.set_index("artist_id")["artist_name"].to_dict()
    for n in G.nodes:
        G.nodes[n]["label"] = name_map.get(n, str(n))

    pos = nx.spring_layout(G, k=0.35, seed=42, weight="w")

    plt.figure(figsize=(10, 10))
    ew = [
        0.5 + 2.5 * (d.get("weight", d.get("w", 1)) / sub["w"].max())
        for _, _, d in G.edges(data=True)
    ]
    nd = dict(G.degree(weight="weight"))
    ns = [50 + 250 * (nd[n] / max(nd.values())) for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=ns, alpha=0.85)
    nx.draw_networkx_edges(G, pos, width=ew, alpha=0.25)

    top_labels = set(sorted(nd, key=lambda x: nd[x], reverse=True)[:30])
    labels = {n: G.nodes[n]["label"] for n in top_labels}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)

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
    plt.savefig(out_png, dpi=200)
    plt.close()
    return out_png
