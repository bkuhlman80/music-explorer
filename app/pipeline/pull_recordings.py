# app/pipeline/pull_recordings.py
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import pandas as pd
import requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--user-agent", required=True)
    ap.add_argument("--rate-limit-ms", type=int, default=1100)
    ap.add_argument("--limit-per-artist", type=int, default=200)
    ap.add_argument("--outdir", default="data/raw")
    args = ap.parse_args()

    arts = pd.read_parquet("data/clean/artists.parquet")
    artist_ids = arts["artist_mbid"].dropna().unique().tolist()

    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    out = Path(args.outdir) / "recordings.jsonl"

    s = requests.Session()
    hdr = {"User-Agent": args.user_agent}

    with out.open("w") as f:
        for aid in artist_ids:
            fetched = 0
            offset = 0
            while fetched < args.limit_per_artist:
                p = {
                    "artist": aid,
                    "limit": 100,
                    "offset": offset,
                    "fmt": "json",
                    "inc": "artist-credits",
                }
                r = s.get(
                    f"{args.base_url}/recording", headers=hdr, params=p, timeout=45
                )
                r.raise_for_status()
                recs = r.json().get("recordings", [])
                if not recs:
                    break
                for rec in recs:
                    f.write(json.dumps(rec) + "\n")
                fetched += len(recs)
                offset += 100
                time.sleep(args.rate_limit_ms / 1000)


if __name__ == "__main__":
    main()
