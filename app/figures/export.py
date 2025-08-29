import os
import pandas as pd
import matplotlib.pyplot as plt

FIGDIR = "docs/figures"
DATADIR = "data/marts"
os.makedirs(FIGDIR, exist_ok=True)

# 1) Hero: release groups per year (all artists)
gt = pd.read_csv(f"{DATADIR}/genre_trends.csv")
rg_per_year = (gt.groupby("year", as_index=False)["release_groups"].sum()
                 .sort_values("year"))
plt.figure()
plt.plot(rg_per_year["year"], rg_per_year["release_groups"])
plt.title("New release groups per year")
plt.xlabel("Year")
plt.ylabel("Count")
plt.savefig(f"{FIGDIR}/rg_per_year.png", bbox_inches="tight")
plt.close()

# 2) Top-5 genres trend lines
top5 = (gt.groupby("genre")["release_groups"].sum()
          .sort_values(ascending=False).head(5).index)
for g in top5:
    df = gt[gt["genre"] == g].sort_values("year")
    plt.figure()
    plt.plot(df["year"], df["release_groups"])
    plt.title(f"{g}: release-group trend")
    plt.xlabel("Year")
    plt.ylabel("Count")
    plt.savefig(f"{FIGDIR}/genre_trend_{g}.png", bbox_inches="tight")
    plt.close()

# 3) Artist discography bar (pick most frequent artist in mart)
ad = pd.read_csv(f"{DATADIR}/artist_discography.csv")
if not ad.empty:
    a = (ad["artist_name"].value_counts().idxmax())
    sub = ad[ad["artist_name"] == a].sort_values("first_release_year")
    plt.figure()
    plt.bar(sub["first_release_year"].astype("Int64").astype(str), sub["rg_mbid"].rank(method="first"))
    plt.title(f"{a}: release-group timeline")
    plt.xlabel("Year")
    plt.ylabel("Cumulative RG count")
    plt.xticks(rotation=45)
    plt.savefig(f"{FIGDIR}/discography_{a}.png", bbox_inches="tight")
    plt.close()

print(f"Wrote figures to {FIGDIR}")
