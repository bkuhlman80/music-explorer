from pathlib import Path
import pandas as pd

DD_PATH = Path("DATA_DICTIONARY.csv")
SINGULAR = {
    "artists": "artist",
    "recordings": "recording",
    "release_groups": "release_group",
    "releases": "release",
    "tracks": "track",
}


class SchemaResolver:
    def __init__(self, path: Path = DD_PATH):
        self.dd = pd.read_csv(path)

    def canonicalize(self, table: str, df: pd.DataFrame) -> pd.DataFrame:
        # 1) MBIDs: rename 'id' → '<entity>_mbid'
        mbid_col = f"{SINGULAR.get(table, table)}_mbid"
        if "id" in df.columns and mbid_col not in df.columns:
            df = df.rename(columns={"id": mbid_col})

        # 2) Titles: standardize to 'name' where appropriate
        if "title" in df.columns and "name" not in df.columns:
            df = df.rename(columns={"title": "name"})

        # 3) Artist-credit fallbacks (flattened exports often provide either)
        if table == "recordings":
            # prefer the credited display name if present
            for c in ["artist_credit_name", "artist-credit[].name"]:
                if c in df.columns and "artist_name" not in df.columns:
                    df = df.rename(columns={c: "artist_name"})
                    break

        return df

    def require(
        self, table: str, df: pd.DataFrame, required: list[str]
    ) -> pd.DataFrame:
        df = self.canonicalize(table, df)
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(
                f"{table}: missing {missing}. present={list(df.columns)}. "
                f"Dictionary-driven canonicalization could not satisfy requirements."
            )
        return df
