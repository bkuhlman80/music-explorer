# app/figures/relations_charts.py
from __future__ import annotations
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import os

MARTS = Path("data/marts")
FIGS = Path("docs/figures")
FIGS.mkdir(parents=True, exist_ok=True)

CAPTION = "Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {date}. Music metadata via MusicBrainz."
PULL_DATE = os.getenv("PULL_DATE_OVERRIDE") or pd.Timestamp.today().date().isoformat()


def _save(fig, name: str, title: str, subtitle: str):
    fig.suptitle(title, fontsize=14, y=0.98)
    fig.text(
        0.5,
        0.01,
        f"{subtitle}\n{CAPTION.format(date=PULL_DATE)}\nTime zone: UTC",
        ha="center",
        va="bottom",
        fontsize=8,
    )
    fig.savefig(FIGS / name, bbox_inches="tight", dpi=180)
    plt.close(fig)
    print(f"[FIG] {name}")


def genre_genre_heatmap():
    df = pd.read_csv(MARTS / "collab_matrix.csv")
    if df.empty:
        return
    pivot = (
        df.pivot(index="genre_1", columns="genre_2", values="n").fillna(0).astype(int)
    )
    # Reorder by total volume
    order = pivot.sum(axis=1).sort_values(ascending=False).index
    pivot = pivot.loc[order, order]
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111)
    im = ax.imshow(pivot.values, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_yticks(range(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, rotation=90)
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Genre 2")
    ax.set_ylabel("Genre 1")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Co-credits (count)")
    _save(
        fig,
        "heatmap_genre_x_genre.png",
        "Genres collaborate with themselves and neighbors",
        "Result, not recipe: Co-credit frequency across genre pairs.",
    )


def avg_team_size_by_decade():
    # Approximate “team size” from number of artist-credits per RG
    # Use release_group_relations.jsonl so we count credits directly
    import json

    rgs = []
    with open("data/raw/release_group_relations.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            rgs.append(json.loads(line))
    rows = []
    for rg in rgs:
        frd = rg.get("first-release-date")
        year = None
        if frd and len(frd) >= 4:
            try:
                year = int(frd[:4])
            except Exception:
                year = None
        if year is None:
            continue
        decade = int(year / 10) * 10
        team_size = len(rg.get("artist-credit", []))
        rows.append({"decade": decade, "team_size": team_size})
    df = pd.DataFrame(rows)
    if df.empty:
        return
    g = df.groupby("decade", as_index=False)["team_size"].mean()
    fig = plt.figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    ax.plot(g["decade"], g["team_size"], marker="o")
    ax.set_xlabel("Decade")
    ax.set_ylabel("Avg team size (artist credits)")
    ax.set_title("")
    _save(
        fig,
        "avg_team_size_by_decade.png",
        "Average team size has changed with production eras",
        "Result, not recipe: Mean artist-credits per release-group by decade.",
    )


def label_change_vs_release_velocity():
    # Proxy velocity: RG count per 3-year window around label-affiliation changes
    la = pd.read_csv(MARTS / "label_affiliations.csv")
    rcy = pd.read_csv(MARTS / "releases_by_country_year.csv")
    if la.empty or rcy.empty:
        return
    # Coerce year bounds from label begin/end
    for col in ["begin", "end"]:
        if col in la.columns:
            la[col] = pd.to_datetime(la[col], errors="coerce").dt.year
    # For each artist, mark years with label edges and compute RGs per year
    velocity = (
        rcy.groupby(["artist_id", "year"], as_index=False)
        .size()
        .rename(columns={"size": "rg_count"})
    )
    # Join nearest label boundary per artist-year
    edges = la.melt(
        id_vars=["artist_id"], value_vars=["begin", "end"], value_name="edge_year"
    ).dropna(subset=["edge_year"])
    merged = velocity.merge(
        edges[["artist_id", "edge_year"]], on="artist_id", how="left"
    )
    merged["dt"] = merged["year"] - merged["edge_year"]
    # Window within [-2, +2] years around a label boundary
    win = merged[merged["dt"].between(-2, 2)]
    g = win.groupby("dt", as_index=False)["rg_count"].mean().sort_values("dt")
    fig = plt.figure(figsize=(7, 4))
    ax = fig.add_subplot(111)
    ax.plot(g["dt"], g["rg_count"], marker="o")
    ax.axvline(0, linestyle="--")
    ax.set_xlabel("Years relative to label change")
    ax.set_ylabel("Avg release-groups per year")
    _save(
        fig,
        "label_change_release_velocity.png",
        "Release velocity around label changes",
        "Result, not recipe: RGs/year in a ±2y window around label begin/end.",
    )


def run():
    genre_genre_heatmap()
    avg_team_size_by_decade()
    label_change_vs_release_velocity()


if __name__ == "__main__":
    run()
