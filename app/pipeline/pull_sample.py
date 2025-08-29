
from pathlib import Path
from dotenv import load_dotenv

# Load env/.env explicitly so running `python -m ...` works
load_dotenv(dotenv_path=Path("env/.env"))


import os, sys, time, json, argparse
from urllib.parse import urlencode, quote
import requests
from datetime import datetime, timezone
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def env(name, default=None, required=False):
    v = os.getenv(name, default)
    if required and not v:
        sys.exit(f"Missing env var: {name}")
    return v

def get(url, params=None, outpath=None, ua=None, timeout=30):
    headers = {"User-Agent": ua}
    if params:
        url = f"{url}?{urlencode(params)}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if outpath:
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("MB_BASE_URL", "https://musicbrainz.org/ws/2"))
    ap.add_argument("--user-agent", default=os.getenv("USER_AGENT"), required=False)
    ap.add_argument("--seed", required=True, help="Artist name, e.g., 'Radiohead'")
    ap.add_argument("--outdir", default="data/raw")
    ap.add_argument("--rate-limit-ms", type=int, default=int(os.getenv("MB_RATE_LIMIT_MS", "1100")))
    ap.add_argument("--timeout", type=int, default=int(os.getenv("MB_TIMEOUT_S", "30")))
    args = ap.parse_args()

    if not args.user_agent:
        sys.exit("Set USER_AGENT in env or pass --user-agent (format: app/vers (email))")

    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = os.path.join(args.outdir, f"sample_{stamp}")
    base = args.base_url.rstrip("/")

    # 1) search artist
    time.sleep(args.rate_limit_ms/1000)
    q = f'artist:{args.seed}'
    asearch = get(
        f"{base}/artist",
        {"query": q, "fmt": "json", "limit": 1},
        outpath=os.path.join(outdir, f"artist_search_{quote(args.seed)}.json"),
        ua=args.user_agent, timeout=args.timeout,
    )
    if not asearch.get("artists"):
        sys.exit(f"No artist found for seed '{args.seed}'")
    artist = asearch["artists"][0]
    artist_mbid = artist["id"]

    # 2) artist detail
    time.sleep(args.rate_limit_ms/1000)
    adetail = get(
        f"{base}/artist/{artist_mbid}",
        {"fmt": "json", "inc": "aliases+genres+tags+url-rels+area-rels"},
        outpath=os.path.join(outdir, f"artist_detail_{artist_mbid}.json"),
        ua=args.user_agent, timeout=args.timeout,
    )

    # 3) release-groups by artist
    time.sleep(args.rate_limit_ms/1000)
    rgs = get(
        f"{base}/release-group",
        {"artist": artist_mbid, "fmt": "json", "limit": 100, "inc": "genres+tags"},
        outpath=os.path.join(outdir, f"release_groups_by_artist_{artist_mbid}.json"),
        ua=args.user_agent, timeout=args.timeout,
    )
    rg_list = rgs.get("release-groups", [])
    first_rg = rg_list[0]["id"] if rg_list else None

    # 4) releases for first release-group with labels+recordings
    if first_rg:
        time.sleep(args.rate_limit_ms/1000)
        _ = get(
            f"{base}/release",
            {"release-group": first_rg, "fmt": "json", "inc": "labels+recordings"},
            outpath=os.path.join(outdir, f"releases_by_rg_{first_rg}.json"),
            ua=args.user_agent, timeout=args.timeout,
        )

    # 5) recordings by artist
    time.sleep(args.rate_limit_ms/1000)
    _ = get(
        f"{base}/recording",
        {"artist": artist_mbid, "fmt": "json", "limit": 100, "inc": "artist-credits+work-rels"},
        outpath=os.path.join(outdir, f"recordings_by_artist_{artist_mbid}.json"),
        ua=args.user_agent, timeout=args.timeout,
    )

    print(f"Saved raw JSON under {outdir}")

if __name__ == "__main__":
    main()
