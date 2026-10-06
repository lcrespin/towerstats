import os
import random
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.taglines import (
    HEADER_SUBTITLES,
    load_tagline_mashups,
    pick_header_subtitle,
    pick_taglines,
    TAGLINE_SLOTS,
)


def test_load_tagline_mashups_from_repo_file():
    mashups = load_tagline_mashups()
    assert len(mashups) >= len(TAGLINE_SLOTS)
    assert all(mashups)


def test_load_tagline_mashups_skips_blank_and_comments(tmp_path):
    path = tmp_path / "mashups.txt"
    path.write_text("# header\n\nAlpha\n  \n# skip\nBeta\n", encoding="utf-8")
    assert load_tagline_mashups(str(path)) == ["Alpha", "Beta"]


def test_load_tagline_mashups_returns_empty_on_missing_file(tmp_path):
    assert load_tagline_mashups(str(tmp_path / "missing.txt")) == []


def test_pick_taglines_samples_unique_mashups():
    pool = [f"m{i}" for i in range(20)]
    picked = pick_taglines(mashups=pool, rng=random.Random(1))
    assert set(picked) == set(TAGLINE_SLOTS)
    assert len(set(picked.values())) == len(TAGLINE_SLOTS)
    assert set(picked.values()).issubset(set(pool))


def test_pick_taglines_repeats_when_pool_is_small():
    picked = pick_taglines(mashups=["only"], rng=random.Random(1))
    assert all(value == "only" for value in picked.values())


def test_pick_taglines_favors_first_lines():
    pool = [f"fav{i}" for i in range(40)] + [f"other{i}" for i in range(40)]
    rng = random.Random(42)
    total = 0
    favorites = 0
    for _ in range(2000):
        values = pick_taglines(mashups=pool, rng=rng).values()
        total += len(values)
        favorites += sum(value.startswith("fav") for value in values)
    assert 0.87 < favorites / total < 0.93


def test_pick_taglines_falls_back_when_favorites_exhausted():
    pool = ["fav0", "fav1", "other0", "other1", "other2", "other3"]
    picked = pick_taglines(mashups=pool, rng=random.Random(1), favorite_count=2)
    assert sorted(picked.values()) == sorted(pool)


def test_pick_taglines_empty_pool():
    picked = pick_taglines(mashups=[])
    assert picked == {slot: "" for slot in TAGLINE_SLOTS}


def test_header_subtitles_are_the_five_agreed_lines():
    assert HEADER_SUBTITLES == (
        "Toutes les soirées où ça aurait dû s'arrêter à minuit.",
        "L'historique officiel des excuses après TowerFall.",
        "Des soirées. Des flèches. Très peu de dignité.",
        "On garde les scores. On oublie qui a commencé.",
        "Preuves que ça durait trop, saison après saison.",
    )


def test_pick_header_subtitle_uses_rng():
    picked = pick_header_subtitle(rng=random.Random(1))
    assert picked in HEADER_SUBTITLES
    assert pick_header_subtitle(rng=random.Random(1)) == picked
