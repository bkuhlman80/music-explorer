from pathlib import Path


def test_hero_exists():
    assert Path("docs/figures/rg_per_year.png").is_file()


def test_collab_exists():
    assert Path("docs/figures/collab_network.png").is_file()


def test_genre_evolution_exists():
    assert Path("docs/figures/genre_evolution.png").is_file()
