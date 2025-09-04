# app/pipeline/build_discog.py
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

RAW = Path("data/raw/recordings.jsonl")
OUT = Path("data/marts")
OUT.mkdir(parents=True, exist_ok=True)


def _yr(s: str | None) -> int | None:
    if not s or len(s) < 4:
        return None
    try:
        return int(s[:4])
    except Exception:
        return None


def run():
    if not RAW.exists():
        raise SystemExit(f"missing {RAW}")

    rows = []
    with RAW.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)

            # 1) try direct RG (rare in recordings payloads)
            rg = rec.get("release-group") or {}
            rg_id = rg.get("id")
            rg_title = rg.get("title")
            rg_primary = rg.get("primary-type")
            rg_frd = rg.get("first-release-date")

            # 2) fallback via releases -> release-group
            releases = rec.get("releases") or []
            if not rg_id and releases:
                for rel in releases:
                    rg2 = rel.get("release-group") or {}
                    rg_id = rg2.get("id") or rg_id
                    rg_title = rg2.get("title") or rg_title or rel.get("title")
                    rg_primary = rg2.get("primary-type") or rg_primary
                    # release-specific date fallback
                    rg_frd = rg2.get("first-release-date") or rel.get("date") or rg_frd

            fry = _yr(rg_frd)

            # artist credits
            for ac in rec.get("artist-credit") or []:
                art = ac.get("artist") or {}
                a_id = art.get("id")
                a_nm = art.get("name")
                if a_id and rg_id:
                    rows.append(
                        {
                            "artist_mbid": a_id,
                            "artist_name": a_nm,
                            "rg_mbid": rg_id,
                            "rg_title": rg_title,
                            "primary_type": rg_primary,
                            "first_release_date": rg_frd,
                            "first_release_year": fry,
                        }
                    )

    df = pd.DataFrame(rows)
    if df.empty:
        print("[WARN] no rows built for artist_discography")
    else:
        df = df.drop_duplicates(["artist_mbid", "rg_mbid"]).sort_values(
            ["artist_name", "first_release_year", "rg_title"], na_position="last"
        )
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / "artist_discography.parquet", index=False)
    df.to_csv(OUT / "artist_discography.csv", index=False)
    print(f"[INFO] wrote {len(df)} rows to {OUT}/artist_discography.*")


if __name__ == "__main__":
    run()
