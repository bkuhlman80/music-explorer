#!/usr/bin/env python3
"""
Profile data dictionary from clean/ and marts/ tables.

Outputs docs/DATA_DICTIONARY_profile.csv with:
table, layer, field, dtype, n_rows, n_nonnull, pct_missing,
n_unique, min, max, example
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

DEFAULT_INPUTS = ["data/clean", "data/marts"]
OUT_PATH = Path("docs/DATA_DICTIONARY_profile.csv")


def read_table(p: Path) -> pd.DataFrame:
    if p.suffix.lower() in [".parquet", ".pq"]:
        return pd.read_parquet(p)
    if p.suffix.lower() in [".csv"]:
        return pd.read_csv(p)
    if p.suffix.lower() in [".jsonl", ".ndjson"]:
        return pd.read_json(p, lines=True)
    raise ValueError(f"Unsupported file type: {p}")


def profile_df(df: pd.DataFrame, table: str, layer: str) -> pd.DataFrame:
    n_rows = len(df)
    summ = []
    for col in df.columns:
        s = df[col]
        nonnull = s.notna().sum()
        ex = s.dropna().iloc[0] if nonnull else None
        try:
            vmin, vmax = (s.min(), s.max())
        except Exception:
            vmin = vmax = None
        summ.append(
            {
                "table": table,
                "layer": layer,
                "field": col,
                "dtype": str(s.dtype),
                "n_rows": n_rows,
                "n_nonnull": int(nonnull),
                "pct_missing": (
                    round((1 - nonnull / n_rows) * 100, 3) if n_rows else 0.0
                ),
                "n_unique": int(s.nunique(dropna=True)),
                "min": vmin,
                "max": vmax,
                "example": ex,
            }
        )
    return pd.DataFrame(summ)


def main(paths: list[str], out: str):
    rows = []
    for root in paths:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for p in root_path.rglob("*"):
            if p.is_dir():
                continue
            if p.suffix.lower() not in [".csv", ".parquet", ".pq", ".jsonl", ".ndjson"]:
                continue
            layer = (
                "clean"
                if "clean" in p.parts
                else ("mart" if "marts" in p.parts else "raw")
            )
            table = p.stem
            try:
                df = read_table(p)
            except Exception as e:
                print(f"[skip] {p} -> {e}")
                continue
            rows.append(profile_df(df, table, layer))
    if not rows:
        print("No input tables found")
        return
    out_df = pd.concat(rows, ignore_index=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out, index=False)
    print(f"Wrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--inputs",
        nargs="*",
        default=DEFAULT_INPUTS,
        help="Directories to scan (default: data/clean data/marts)",
    )
    ap.add_argument(
        "--out",
        default=str(OUT_PATH),
        help="Output CSV path (default: docs/DATA_DICTIONARY_profile.csv)",
    )
    args = ap.parse_args()
    main(args.inputs, args.out)
