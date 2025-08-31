import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import date

CAPTION = 'Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {pulled}. "Music metadata provided by MusicBrainz."'


def plot_genre_evolution(
    genres_by_decade_csv: str, out_png: str, top_k: int = 10
) -> str:
    df = pd.read_csv(genres_by_decade_csv)  # decade, genre, count|releases
    if "releases" not in df.columns and "count" in df.columns:
        df = df.rename(columns={"count": "releases"})
    keep = (
        df.groupby("genre")["releases"]
        .sum()
        .sort_values(ascending=False)
        .head(top_k)
        .index
    )
    dff = df[df["genre"].isin(keep)].copy()
    pv = (
        dff.pivot(index="decade", columns="genre", values="releases")
        .fillna(0)
        .sort_index()
    )
    plt.figure(figsize=(10, 6))
    for g in pv.columns:
        plt.plot(pv.index, pv[g], marker="o", label=g)
    plt.title("Genre evolution by decade")
    plt.xlabel("Decade")
    plt.ylabel("Releases")
    plt.legend(ncol=2, fontsize=8)
    plt.figtext(
        0.5,
        0.01,
        CAPTION.format(pulled=date.today().isoformat()),
        ha="center",
        fontsize=8,
    )
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(rect=[0, 0.06, 1, 0.97])
    plt.savefig(out_png, dpi=200)
    plt.close()
    return out_png
