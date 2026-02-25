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


def test_elo_legacy_ranking_top3_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    elo_legacy_ranking = ctx["elo_legacy_ranking"]
    assert len(elo_legacy_ranking) >= 3

    top3_names = [name for name, _elo in elo_legacy_ranking[:3]]
    assert top3_names == ["LOUIS", "ERIC", "DAVID"]


def test_elo_legacy_scores_for_all_players_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    elo_ranking = ctx["elo_legacy_ranking"]
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


def test_elo_batch_scores_for_all_players_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    elo_ranking = ctx["elo_ranking"]
    expected_players = {"LOUIS", "ERIC", "DAVID", "BENOIT", "MEHDI", "JULIEN"}
    assert len(elo_ranking) == 6
    assert {name for name, _ in elo_ranking} == expected_players

    for i, (name, elo) in enumerate(elo_ranking):
        assert 1000 <= elo <= 2000, f"{name}: ELO {elo} hors plage"
        if i < len(elo_ranking) - 1:
            assert elo >= elo_ranking[i + 1][1], "Classement ELO batch doit être décroissant"


def test_elo_batch_differs_from_legacy_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["elo_ranking"] != ctx["elo_legacy_ranking"]


def test_elo_batch_is_deterministic_from_snapshot():
    stats_1 = build_stats_from_snapshot()
    stats_2 = build_stats_from_snapshot()

    ctx_1 = stats_1.prepare_template_data()
    ctx_2 = stats_2.prepare_template_data()

    assert ctx_1["elo_ranking"] == ctx_2["elo_ranking"]


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


def test_group_sessions_by_date_from_snapshot():
    stats = build_stats_from_snapshot()

    sessions_by_date = stats.group_sessions_by_date()
    all_sessions = stats.sessions

    # Toutes les sessions sont présentes dans le regroupement
    total_grouped = sum(len(v) for v in sessions_by_date.values())
    assert total_grouped == len(all_sessions)

    # Les clés du dict correspondent aux dates distinctes des sessions
    expected_dates = {session["date"][:10] for session in all_sessions if session.get("date")}
    assert set(sessions_by_date.keys()) == expected_dates


def test_detailed_stats_and_kill_relationships_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["has_detailed_stats"] is True

    # Classement K/D cohérent avec le nombre de joueurs uniques
    kill_death_ranking = ctx["kill_death_ranking"]
    assert len(kill_death_ranking) == ctx["unique_players_count"]
    for row in kill_death_ranking:
        player, kills, deaths, self_kills, kd_ratio = row[0], row[1], row[2], row[3], row[4]
        assert isinstance(player, str)
        assert kills >= 0
        assert deaths >= 0
        assert self_kills >= 0
        assert kd_ratio >= 0

    # Relations de kills cohérentes avec la liste des joueurs
    kill_relationships = ctx["kill_relationships"]
    players = {p for p, *_ in kill_death_ranking}

    assert isinstance(kill_relationships, dict)
    assert set(kill_relationships.keys()).issubset(players)
    for killer, victims in kill_relationships.items():
        assert killer in players
        assert isinstance(victims, dict)
        assert set(victims.keys()).issubset(players)


EXPECTED_TEMPLATE_KEYS = frozenset({
    "unique_groups", "sorted_groups", "default_group", "rankings_by_group",
    "default_ranking", "date_debut", "date_fin", "date_debut_raw", "date_fin_raw",
    "total_sessions", "unique_players_count", "best_players", "best_score",
    "best_percentage_players", "best_percentage", "win_percentage_ranking",
    "elo_ranking", "best_elo_players", "best_elo",
    "elo_legacy_ranking", "best_elo_legacy_players", "best_elo_legacy",
    "latest_date",
    "latest_sessions_parsed", "sessions_by_date", "all_sessions_data",
    "player_colors", "has_detailed_stats", "kill_death_ranking",
    "kill_sources_aggregated", "kill_relationships", "all_players_for_matrix",
    "max_kills_in_matrix", "top_killers", "top_deaths", "top_self_kills",
    "least_deaths_row", "least_self_kills_row",
    "best_kd_ratio", "best_kd_value",
})


def test_template_context_contract():
    """Ensure prepare_template_data() returns all keys expected by the template (no regression)."""
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()
    actual_keys = set(ctx.keys())
    missing = EXPECTED_TEMPLATE_KEYS - actual_keys
    extra = actual_keys - EXPECTED_TEMPLATE_KEYS
    assert not missing, f"Missing template keys: {missing}"
    assert not extra, f"Unexpected keys (update EXPECTED_TEMPLATE_KEYS if intentional): {extra}"


def test_best_elo_and_dates_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["best_elo"] == ctx["elo_ranking"][0][1]
    assert 1000 <= ctx["best_elo"] <= 2000
    assert ctx["best_elo_legacy_players"] == ["LOUIS"]
    assert ctx["best_elo_legacy"] == ctx["elo_legacy_ranking"][0][1]
    assert 1000 <= ctx["best_elo_legacy"] <= 2000

    assert ctx["date_debut_raw"] == "2025-06-03"
    assert ctx["date_fin_raw"] == "2026-02-25"

    assert ctx["rankings_by_group"][ctx["default_group"]] == ctx["default_ranking"]
    assert ctx["sorted_groups"][0] == "DAVID-ERIC-LOUIS"


def test_top_killers_deaths_and_kd_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    # Top killers by kills per game (average; period = sessions with detailed stats only)
    top_killers = ctx["top_killers"]
    assert len(top_killers) == 5
    assert [t[0] for t in top_killers] == ["DAVID", "LOUIS", "ERIC", "MEHDI", "BENOIT"]

    # Top deaths by deaths per game (average); "Moins de Deaths" = last = least
    top_deaths = ctx["top_deaths"]
    assert len(top_deaths) == 5
    assert [t[0] for t in top_deaths] == ["MEHDI", "ERIC", "DAVID", "LOUIS", "JULIEN"]

    # Top self-kills: (player, total_self_kills, self_kills_per_game), sorted by per_game desc
    top_self_kills = ctx["top_self_kills"]
    assert len(top_self_kills) == 5
    assert [t[0] for t in top_self_kills] == ["DAVID", "ERIC", "LOUIS", "MEHDI", "BENOIT"]
    for row in top_self_kills:
        assert len(row) == 3

    assert ctx["best_kd_ratio"] == ["DAVID"]
    assert round(ctx["best_kd_value"], 4) == 1.0161
    assert ctx["max_kills_in_matrix"] > 1
    assert len(ctx["all_players_for_matrix"]) == 6


def test_date_filtering_reduces_sessions():
    """Regression: filtering by date range must reduce sessions and update stats."""
    manager = SessionDataManager(local_file=SNAPSHOT_PATH)
    manager.load_all()
    sessions = manager.get_sessions()

    full = SessionStatsManager(sessions)
    full_ctx = full.prepare_template_data()
    assert full_ctx["total_sessions"] == 37

    filtered = SessionStatsManager(sessions, date_start="2026-01-01", date_end="2026-02-25")
    filtered_ctx = filtered.prepare_template_data()
    assert filtered_ctx["total_sessions"] < 37
    assert filtered_ctx["date_debut_raw"] >= "2026-01-01"
    assert filtered_ctx["date_fin_raw"] <= "2026-02-25"


def test_normalize_session_players_adds_zero_win_players_to_today_win():
    """Players in today but missing from todayWin (e.g. 0 wins) are added to todayWin with correct value."""
    session = {
        "data": {
            "todayWin": {"ALICE": 2},
            "totalWin": {"ALICE": 2},
            "today": {
                "ALICE": {"win": 2, "kill": 5, "death": 1},
                "BOB": {"win": 0, "kill": 1, "death": 5},
            },
            "total": {
                "ALICE": {"win": 2, "kill": 5, "death": 1},
                "BOB": {"win": 0, "kill": 1, "death": 5},
            },
            "date": "2025-12-08-12",
        }
    }
    SessionDataManager.normalize_session_players(session)
    data = session["data"]
    assert "todayWin" in data
    assert data["todayWin"].get("ALICE") == 2
    assert data["todayWin"].get("BOB") == 0
    assert data["totalWin"].get("BOB") == 0
