from app import Main


def test_app_reads_marts_only():
    assert "data/marts" in Main.DATA_DIR.as_posix()
