import os, re, json, csv, sys, argparse
from collections import defaultdict
from typing import Any

PATTERNS = [
    (re.compile(r"artist_detail_"), "artists"),
    (re.compile(r"artist_search_"), "artists"),
    (re.compile(r"release_groups_by_artist_"), "release_groups"),
    (re.compile(r"releases_by_rg_"), "releases"),
    (re.compile(r"recordings_by_artist_"), "recordings"),
]
ARRAY_ROOT_HINTS = {
    "artists": "artists",
    "release-groups": "release_groups",
    "releases": "releases",
    "recordings": "recordings",
    "works": "works",
    "labels": "labels",
}


def infer_table_from_filename(fn: str):
    for pat, tbl in PATTERNS:
        if pat.search(fn):
            return tbl
    return None


def walk(prefix: str, node: Any, acc: dict):
    t = type(node).__name__.lower()
    acc[prefix or "$"] = t
    if isinstance(node, dict):
        for k, v in node.items():
            walk(f"{prefix}.{k}" if prefix else k, v, acc)
    elif isinstance(node, list):
        if node:
            walk(f"{prefix}[]", node[0], acc)
        else:
            acc[f"{prefix}[]"] = "list(empty)"


def emit_rows(table: str, acc: dict):
    rows = []
    for path, typ in sorted(acc.items()):
        if path == "$":
            continue
        field = path.split(".", 1)[1] if path.startswith(table + ".") else path
        rows.append((table, field, typ))
    return rows


def process_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tables_to_scan = set()
    base_tbl = infer_table_from_filename(os.path.basename(path))
    if base_tbl:
        tables_to_scan.add(base_tbl)
    if isinstance(data, dict):
        for k, tbl in ARRAY_ROOT_HINTS.items():
            if k in data and isinstance(data[k], list):
                tables_to_scan.add(tbl)

    results = defaultdict(list)
    for tbl in tables_to_scan:
        acc = {}
        root = None
        if base_tbl == tbl and isinstance(data, dict) and data.get("id"):
            root = data
        elif isinstance(data, dict):
            for k, tname in ARRAY_ROOT_HINTS.items():
                if tname == tbl and k in data and isinstance(data[k], list):
                    root = data[k][0] if data[k] else {}
                    break
        if root is None:
            continue

        walk(tbl, root, acc)
        results[tbl].extend(emit_rows(tbl, acc))

        if tbl == "artists":
            aliases = root.get("aliases", [])
            if isinstance(aliases, list) and aliases:
                acc2 = {}
                walk("artist_aliases", aliases[0], acc2)
                results["artist_aliases"].extend(emit_rows("artist_aliases", acc2))

        if tbl == "releases":
            media = root.get("media", [])
            if isinstance(media, list) and media and media[0].get("tracks"):
                acc3 = {}
                walk("tracks", media[0]["tracks"][0], acc3)
                results["tracks"].extend(emit_rows("tracks", acc3))

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default="data/raw")
    ap.add_argument("--out", default="DATA_DICTIONARY.csv")
    args = ap.parse_args()

    aggregates = defaultdict(set)
    for root, _, files in os.walk(args.indir):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            try:
                res = process_file(os.path.join(root, fn))
                for tbl, rows in res.items():
                    for _, field, typ in rows:
                        aggregates[tbl].add((field, typ))
            except Exception as e:
                print(f"warn: {fn}: {e}", file=sys.stderr)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["table", "field", "type", "unit", "description", "source_field"])
        for tbl in sorted(aggregates.keys()):
            for field, typ in sorted(aggregates[tbl]):
                w.writerow([tbl.replace("-", "_"), field, typ, "", "", field])

    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
