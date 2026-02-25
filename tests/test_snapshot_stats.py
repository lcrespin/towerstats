import os
import sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.data_manager import SessionDataManager
from src.stats_manager import SessionStatsManager
SNAPSHOT_PATH = os.path.join(BASE_DIR, "tests", "data", "TowerFallStat_snapshot_2025-02-25.csv")


def build_stats_from_snapshot():
    """Helper to build stats manager from the fixed snapshot file."""
    manager = SessionDataManager(local_file=SNAPSHOT_PATH)
    manager.load_all()
    sessions = manager.get_sessions()
    assert len(sessions) == 37
    return SessionStatsManager(sessions)


def test_basic_counts_and_dates_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["total_sessions"] == 37
    assert ctx["unique_players_count"] == 6


def test_best_score_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["best_score"] == 218
    assert ctx["best_players"] == ["LOUIS"]


def test_best_win_percentage_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert round(ctx["best_percentage"], 4) == 34.4756
    assert ctx["best_percentage_players"] == ["ERIC"]

    # Classement complet % victoires: (joueur, victoires, parties, pourcentage)
    wp = ctx["win_percentage_ranking"]
    assert len(wp) == 6
    expected_wp = [
        ("ERIC", 332, 963, 34.4756),
        ("LOUIS", 319, 940, 33.9362),
        ("DAVID", 318, 957, 33.2288),
        ("BENOIT", 22, 166, 13.2530),
        ("JULIEN", 18, 154, 11.6883),
        ("MEHDI", 5, 93, 5.3763),
    ]
    for i, (player, victories, games, pct) in enumerate(wp):
        assert player == expected_wp[i][0]
        assert victories == expected_wp[i][1]
        assert games == expected_wp[i][2]
        assert round(pct, 4) == expected_wp[i][3]


def test_elo_ranking_top3_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    elo_ranking = ctx["elo_ranking"]
    assert len(elo_ranking) >= 3

    top3_names = [name for name, _elo in elo_ranking[:3]]
    assert top3_names == ["LOUIS", "ERIC", "DAVID"]


def test_elo_scores_for_all_players_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    elo_ranking = ctx["elo_ranking"]
    expected_players = {"LOUIS", "ERIC", "DAVID", "BENOIT", "MEHDI", "JULIEN"}
    assert len(elo_ranking) == 6
    assert {name for name, _ in elo_ranking} == expected_players

    # Ordre attendu du classement (sans toucher au calcul ELO)
    expected_order = ["LOUIS", "ERIC", "DAVID", "BENOIT", "MEHDI", "JULIEN"]
    actual_order = [name for name, _ in elo_ranking]
    assert actual_order == expected_order

    # ELO strictement décroissant et dans une plage raisonnable (initial 1500, K=32)
    for i, (name, elo) in enumerate(elo_ranking):
        assert 1000 <= elo <= 2000, f"{name}: ELO {elo} hors plage"
        if i < len(elo_ranking) - 1:
            assert elo >= elo_ranking[i + 1][1], "Classement ELO doit être décroissant"


def test_default_group_ranking_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["default_group"] == "DAVID-ERIC-LOUIS"
    # Classement complet du groupe par défaut (tous les joueurs du groupe)
    assert ctx["default_ranking"] == [
        ("LOUIS", 218),
        ("DAVID", 205),
        ("ERIC", 201),
    ]

