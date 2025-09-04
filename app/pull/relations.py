# app/pull/relations.py
from __future__ import annotations
import os
import time
import json
import urllib.parse as up
from pathlib import Path
from typing import Iterable, Dict, Any, List
import requests

MB_BASE_URL = os.getenv("MB_BASE_URL", "https://musicbrainz.org/ws/2")
USER_AGENT = os.getenv("USER_AGENT", "music-explorer/0.1 (example@example.com)")
RATE_LIMIT_MS = int(os.getenv("MB_RATE_LIMIT_MS", "1100"))
MAX_RETRIES = int(os.getenv("MB_MAX_RETRIES", "3"))
TIMEOUT_S = int(os.getenv("MB_TIMEOUT_S", "30"))
SEED_MBIDS = [
    s.strip() for s in os.getenv("ARTISTS_SEED_MBIDS", "").split(",") if s.strip()
]
LIMIT_PER_ARTIST = int(os.getenv("LIMIT_PER_ARTIST", "200"))

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_ARTISTS = RAW_DIR / "artist_relations.jsonl"
OUT_RGS = RAW_DIR / "release_group_relations.jsonl"

INC_ARTIST = (
    "aliases+tags+genres+recordings+release-groups+works+"
    "artist-rels+label-rels+recording-rels+release-group-rels+url-rels+work-rels"
)
INC_RG = (
    "artist-credits+releases+tags+genres+"
    "artist-rels+label-rels+recording-rels+url-rels+work-rels"
)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


def _sleep():
    time.sleep(RATE_LIMIT_MS / 1000.0)


def _get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    q = params.copy()
    q["fmt"] = "json"
    for attempt in range(1, MAX_RETRIES + 1):
        _sleep()
        try:
            r = session.get(url, params=q, timeout=TIMEOUT_S)
            if r.status_code == 503:
                time.sleep(2 * attempt)
                continue
            if 400 <= r.status_code < 500:
                # emit MB error payload to help debugging
                try:
                    detail = r.json()
                except Exception:
                    detail = r.text
                raise SystemExit(f"{r.status_code} {r.reason} on {r.url}\n{detail}")
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(1.5 * attempt)
    return {}


def _paged(
    endpoint: str, params: Dict[str, Any], item_key: str, limit: int | None = None
) -> Iterable[Dict[str, Any]]:
    offset = 0
    seen = 0
    while True:
        page = _get(f"{MB_BASE_URL}/{endpoint}", params | {"offset": offset})
        items = page.get(item_key, [])
        for it in items:
            yield it
            seen += 1
            if limit and seen >= limit:
                return
        count = page.get("count", 0)
        offset += len(items)
        if offset >= count or not items:
            break


def fetch_artist_relations(artist_mbid: str) -> Dict[str, Any]:
    return _get(f"{MB_BASE_URL}/artist/{up.quote(artist_mbid)}", {"inc": INC_ARTIST})


def fetch_artist_release_groups(
    artist_mbid: str, limit_each: int
) -> List[Dict[str, Any]]:
    # We filter to primary artist credits; MB will still return collaborations which we want
    return list(
        _paged(
            "release-group",
            {"artist": artist_mbid, "limit": 100, "inc": "artist-credits+tags+genres"},
            "release-groups",
            limit=limit_each,
        )
    )


def fetch_rg_relations(rg_mbid: str) -> Dict[str, Any]:
    return _get(f"{MB_BASE_URL}/release-group/{up.quote(rg_mbid)}", {"inc": INC_RG})


def run():
    if not SEED_MBIDS:
        raise SystemExit("ARTISTS_SEED_MBIDS is empty. Provide artist MBIDs in .env")

    with OUT_ARTISTS.open("w", encoding="utf-8") as fa, OUT_RGS.open(
        "w", encoding="utf-8"
    ) as frg:
        for a in SEED_MBIDS:
            # Artist object with relations
            a_obj = fetch_artist_relations(a)
            a_obj["_seed_mbid"] = a
            fa.write(json.dumps(a_obj, ensure_ascii=False) + "\n")

            # Enumerate a bounded set of release-groups for this artist
            rgs = fetch_artist_release_groups(a, LIMIT_PER_ARTIST)
            for rg in rgs:
                rg_mbid = rg.get("id")
                if not rg_mbid:
                    continue
                rg_full = fetch_rg_relations(rg_mbid)
                rg_full["_seed_artist_mbid"] = a
                frg.write(json.dumps(rg_full, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    run()
