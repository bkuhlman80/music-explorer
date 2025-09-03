from pathlib import Path
from app.config import get_env
from app.config import REQUIRE_MARTS_ONLY


def test_default_data_dir_is_marts():
    data_dir = Path(get_env("DATA_DIR", "data/marts")).as_posix()
    assert "data/marts" in data_dir


def test_runtime_guard_enabled_by_default():
    assert REQUIRE_MARTS_ONLY is True
