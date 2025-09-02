#!/usr/bin/env python3
"""
Pull recordings with artist credits from MusicBrainz.

Modes:
1) Seeded: --seed "Kanye West,Jay-Z,..."  (names or MBIDs)
2) Parquet: if --seed omitted, read data/clean/artists.parquet and use artist MBIDs

Output: data/raw/recordings.jsonl  (override with --out)
"""

import argparse
import json
import sys
import time
import re
from pathlib import Path

import pandas as pd
import requests


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--base-url", required=True, help="e.g. https://musicbrainz.org/ws/2"
    )
    p.add_argument("--user-agent", required=True, help="Descriptive UA per MB rules")
    p.add_argument("--rate-limit-ms", type=int, default=1100)
    p.add_argument("--timeout-s", type=int, default=30)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--limit-per-artist", type=int, default=200, help="cap per artist")
    p.add_argument("--seed", default="", help="Comma-separated names or MBIDs")
    p.add_argument("--out", default="data/raw/recordings.jsonl")
    return p.parse_args()


_MBID_RE = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$", re.I)


def is_mbid(s: str) -> bool:
    return bool(_MBID_RE.match(s.strip()))


def get_with_retries(
    s: requests.Session,
    url: str,
    headers: dict,
    params: dict,
    timeout: int,
    retries: int,
):
    last = None
    for i in range(retries):
        r = s.get(url, headers=headers, params=params, timeout=timeout)
        if r.status_code == 200:
            return r
        last = r
        time.sleep(0.5 * (i + 1))
    return last


def iter_recordings_for_artist(
    session: requests.Session,
    base_url: str,
    hdr: dict,
    artist_token: str,
    limit_per_artist: int,
    timeout_s: int,
    retries: int,
    rate_limit_ms: int,
):
    """
    Use /recording search with either artist MBID (artist=) or name (query='artist:"name"').
    Paginate by offset. Yield recording dicts.
    """
    endpoint = f"{base_url.rstrip('/')}/recording"  # correct endpoint
    fetched = 0
    offset = 0
    page_size = 100

    while fetched < limit_per_artist:
        if is_mbid(artist_token):
            params = {
                "artist": artist_token,
                "limit": page_size,
                "offset": offset,
                "fmt": "json",
                "inc": "artist-credits",
            }
        else:
            # name search
            params = {
                "query": f'artist:"{artist_token}"',
                "limit": page_size,
                "offset": offset,
                "fmt": "json",
                "inc": "artist-credits",
            }

        time.sleep(rate_limit_ms / 1000.0)
        r = get_with_retries(session, endpoint, hdr, params, timeout_s, retries)
        if r is None or r.status_code != 200:
            print(
                f"[WARN] {artist_token}: HTTP {None if r is None else r.status_code}",
                file=sys.stderr,
            )
            return

        data = r.json()
        recs = data.get("recordings", [])
        if not recs:
            return

        for rec in recs:
            yield rec

        fetched += len(recs)
        offset += page_size


def load_artist_tokens(seed: str):
    if seed.strip():
        return [s.strip() for s in seed.split(",") if s.strip()]
    # fallback to parquet MBIDs
    arts = pd.read_parquet("data/clean/artists.parquet")
    tokens = arts["artist_mbid"].dropna().astype(str).unique().tolist()
    return tokens


def main():
    args = parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tokens = load_artist_tokens(args.seed)
    if not tokens:
        print(
            "[ERROR] No artists found from --seed or artists.parquet", file=sys.stderr
        )
        sys.exit(2)

    s = requests.Session()
    hdr = {"User-Agent": args.user_agent}

    total = 0
    with out_path.open("w", encoding="utf-8") as f:
        for t in tokens:
            count = 0
            for rec in iter_recordings_for_artist(
                s,
                args.base_url,
                hdr,
                t,
                args.limit_per_artist,
                args.timeout_s,
                args.retries,
                args.rate_limit_ms,
            ):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                count += 1
                total += 1
            print(f"[INFO] {t}: {count} recordings")

    print(f"[INFO] wrote {total} recordings to {out_path}")


if __name__ == "__main__":
    main()
