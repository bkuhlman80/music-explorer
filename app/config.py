# app/config.py
import os

# Optional Streamlit secrets (safe to import outside Streamlit)
try:
    import streamlit as st  # type: ignore

    _SECRETS = dict(st.secrets)
except Exception:
    _SECRETS = {}


def get_env(name: str, default=None, cast=str):
    if name in _SECRETS:
        return cast(_SECRETS[name])
    val = os.getenv(name, default)
    return cast(val) if val is not None else None


# Common settings
MB_BASE_URL = get_env("MB_BASE_URL", "https://musicbrainz.org/ws/2")
USER_AGENT = get_env("USER_AGENT", "music-explorer/0.1 (you@example.com)")
MB_RATE_LIMIT_MS = int(get_env("MB_RATE_LIMIT_MS", 1100))
MB_MAX_RETRIES = int(get_env("MB_MAX_RETRIES", 3))
MB_TIMEOUT_S = int(get_env("MB_TIMEOUT_S", 30))
TZ = get_env("TZ", "UTC")
ARTISTS_SEED = [
    s.strip() for s in str(get_env("ARTISTS_SEED", "")).split(",") if s.strip()
]
REQUIRE_MARTS_ONLY = get_env("REQUIRE_MARTS_ONLY", "1") == "1"
