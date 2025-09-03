# app/schema.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable
import pandas as pd

DD_PATH = Path("DATA_DICTIONARY.csv")

SINGULAR = {
    "artists": "artist",
    "recordings": "recording",
    "release_groups": "release_group",
    "releases": "release",
    "tracks": "track",
    "entity_genres": "entity",
}

ALIAS = {
    "artists": {
        "mbid": "artist_mbid",
        "gid": "artist_mbid",
        "artist_id": "artist_mbid",
        "id": "artist_mbid",
        "artist_name": "name",
        "title": "name",
    },
    "release_groups": {
        "release_group_mbid": "rg_mbid",
        "release_group_id": "rg_mbid",
        "mbid": "rg_mbid",
        "gid": "rg_mbid",
        "id": "rg_mbid",
        "name": "title",
        "first-release-date": "first_release_date",
        "primary-type": "primary_type",
        "artist-credit": "artist_credit",
    },
    "recordings": {
        "mbid": "recording_mbid",
        "gid": "recording_mbid",
        "id": "recording_mbid",
        "title": "name",
        "artist-credit": "artist_credit",
        "artist_credit_name": "artist_name",
        "artist-credit[].name": "artist_name",
    },
    "entity_genres": {"entity-type": "entity_type", "entity-mbid": "entity_mbid"},
}

EMPTY_SCHEMA = {
    "artists": ["artist_mbid", "name"],
    "release_groups": [
        "rg_mbid",
        "title",
        "primary_type",
        "first_release_date",
        "artist_credit",
    ],
    "recordings": ["recording_mbid", "name", "artist_credit", "artist_name"],
    "entity_genres": ["entity_type", "entity_mbid", "genre"],
}


class SchemaResolver:
    def __init__(self, path: Path = DD_PATH):
        try:
            self.dd = pd.read_csv(path) if path.exists() else pd.DataFrame()
        except Exception:
            self.dd = pd.DataFrame()

    def _target_mbid(self, table: str) -> str:
        return (
            "rg_mbid"
            if table == "release_groups"
            else f"{SINGULAR.get(table, table)}_mbid"
        )

    def _apply_aliases(self, table: str, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        mapping = ALIAS.get(table, {})
        to_rename: dict[str, str] = {c: mapping[c] for c in mapping if c in df.columns}
        # dash→underscore variants
        for c in list(df.columns):
            cu = c.replace("-", "_")
            if cu != c and cu in mapping and c not in to_rename:
                to_rename[c] = mapping[cu]
        if to_rename:
            df = df.rename(columns=to_rename)
        return df

    def _ensure_id(self, table: str, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        target = self._target_mbid(table)
        if target in df.columns:
            return df
        if table == "release_groups":
            candidates = [
                "rg_mbid",
                "release_group_mbid",
                "release_group_id",
                "mbid",
                "gid",
                "id",
            ]
        elif table == "artists":
            candidates = ["artist_mbid", "artist_id", "mbid", "gid", "id"]
        elif table == "recordings":
            candidates = ["recording_mbid", "mbid", "gid", "id"]
        else:
            candidates = [f"{SINGULAR.get(table, table)}_mbid", "mbid", "gid", "id"]
        for c in candidates:
            if c in df.columns:
                return df.rename(columns={c: target})
        return df

    def canonicalize(self, table: str, df: pd.DataFrame) -> pd.DataFrame:
        df = self._apply_aliases(table, df)
        df = self._ensure_id(table, df)
        if df is not None and not df.empty:
            if (
                table == "release_groups"
                and "title" not in df.columns
                and "name" in df.columns
            ):
                df = df.rename(columns={"name": "title"})
            if (
                table == "artists"
                and "name" not in df.columns
                and "artist_name" in df.columns
            ):
                df = df.rename(columns={"artist_name": "name"})
            if (
                table == "recordings"
                and "name" not in df.columns
                and "title" in df.columns
            ):
                df = df.rename(columns={"title": "name"})
        return df

    def empty(self, table: str, required: Iterable[str] | None = None) -> pd.DataFrame:
        cols = list(required) if required else EMPTY_SCHEMA.get(table, [])
        return pd.DataFrame(columns=cols)

    def require(
        self,
        table: str,
        df: pd.DataFrame,
        required: list[str],
        *,
        allow_empty: bool = True,
    ) -> pd.DataFrame:
        df = self.canonicalize(table, df)
        if df is None or df.empty:
            return (
                self.empty(table, required)
                if allow_empty
                else self._raise(table, [], required)
            )
        missing = [c for c in required if c not in df.columns]
        if missing:
            self._raise(table, list(df.columns), required)
        return df

    @staticmethod
    def _raise(table: str, present: list[str], required: list[str]) -> None:
        raise KeyError(
            f"{table}: missing {sorted(set(required) - set(present))}. "
            f"present={present}. Canonicalization could not satisfy requirements."
        )
