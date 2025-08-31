from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

M = Path("data/marts")
D = Path("docs/figures")
D.mkdir(parents=True, exist_ok=True)

# 1) Hero: release groups per decade with fallbacks → docs/figures/rg_per_year.png
def _rg_by_year_fallback() -> pd.DataFrame:
    p = M / "release_groups_by_year.csv"
    if p.exists():
        df = pd.read_csv(p)
        if len(df):
            return df.rename(columns=str.lower)[["year", "count"]]
    # fallback from release_groups
    p = M / "release_groups.csv"
    if p.exists():
        df = pd.read_csv(p).rename(columns=str.lower)
        if "first_release_year" in df and df["first_release_year"].notna().any():
            out = (df.dropna(subset=["first_release_year"])
                     .assign(year=lambda d: d["first_release_year"].astype(int))
                     .groupby("year").size().reset_index(name="count"))
            if len(out):
                return out
    # last resort from artist_discography
    p = M / "artist_discography.csv"
    if p.exists():
        df = pd.read_csv(p)
        if "first_release_year" in df and df["first_release_year"].notna().any():
            out = (df.dropna(subset=["first_release_year"])
                     .assign(year=lambda d: d["first_release_year"].astype(int))
                     .groupby("year").size().reset_index(name="count"))
            return out
    return pd.DataFrame(columns=["year", "count"])

rg_year = _rg_by_year_fallback()
# aggregate to decades: 1960s, 1970s, …
if len(rg_year):
    rg_dec = (rg_year.assign(decade=lambda d: (d["year"] // 10) * 10)
                      .groupby("decade", as_index=False)["count"].sum()
                      .sort_values("decade"))
    labels = [f"{d}s" for d in rg_dec["decade"]]
    plt.figure(figsize=(10, 4))
    plt.bar(labels, rg_dec["count"])
    plt.title("New release groups per decade")
    plt.xlabel("Decade")
    plt.ylabel("Count")
    plt.tight_layout()
else:
    plt.figure(figsize=(10, 4))
    plt.title("New release groups per decade (no data)")
    plt.xlabel("Decade")
    plt.ylabel("Count")
plt.savefig(D / "rg_per_year.png", dpi=150)  # keep filename expected by tests
plt.close()

# 2) Top-5 genres by decade  → docs/figures/genre_trend_<genre>.png
gpath = M / "genres_by_decade.csv"
if gpath.exists():
    gbd = pd.read_csv(gpath)
    # total per genre, pick top 5
    top5 = (
        gbd.groupby("genre")["count"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )
    for g in top5:
        df = gbd[gbd["genre"] == g].sort_values("decade")
        plt.figure(figsize=(6, 3.5))
        plt.plot(df["decade"], df["count"])
        plt.title(f"{g}: release groups per decade")
        plt.xlabel("Decade")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(D / f"genre_trend_{g}.png", dpi=150)
        plt.close()

# 3) One artist discography timeline  → docs/figures/discography_<artist>.png
adpath = M / "artist_discography.csv"
if adpath.exists():
    ad = pd.read_csv(adpath)
    if not ad.empty:
        # pick most frequent artist
        artist = ad["artist_name"].value_counts().idxmax()
        sub = (
            ad[ad["artist_name"] == artist]
            .dropna(subset=["first_release_year"])
            .sort_values("first_release_year")
        )
        if not sub.empty:
            # cumulative count over years
            y = sub["first_release_year"].astype(int)
            c = y.rank(method="first")  # simple 1..N
            plt.figure(figsize=(7, 3.5))
            plt.bar(y.astype(str), c)
            plt.title(f"{artist}: release-group timeline")
            plt.xlabel("Year")
            plt.ylabel("Cumulative RG count")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(D / f"discography_{artist}.png", dpi=150)
            plt.close()

print(f"Wrote figures to {D}")
