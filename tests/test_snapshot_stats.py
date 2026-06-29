import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.data_manager import SessionDataManager
from src.stats_manager import SessionStatsManager

DATA_DIR = os.path.join(BASE_DIR, "tests", "data")
SNAPSHOT_2025 = os.path.join(DATA_DIR, "TowerFallStat_snapshot_2025-02-25.csv")
SNAPSHOT_2026 = os.path.join(DATA_DIR, "TowerFallStat_snapshot_2026-04-24.csv")
SNAPSHOT_PATHS_INTEGRATION = (SNAPSHOT_2025, SNAPSHOT_2026)
SNAPSHOT_PATH = SNAPSHOT_2025
MATCHS_MINIMAL = os.path.join(DATA_DIR, "TowerFallStat_matchs_minimal.csv")


def build_stats_from_path(path: str) -> SessionStatsManager:
    """Build stats manager from a local CSV path."""
    manager = SessionDataManager(local_file=path)
    manager.load_all()
    return SessionStatsManager(manager.get_sessions())


def build_stats_from_snapshot() -> SessionStatsManager:
    """Helper to build stats manager from the fixed 2025 snapshot (regression baselines)."""
    manager = SessionDataManager(local_file=SNAPSHOT_2025)
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

    # Classement complet % victoires: (rank, joueur, victoires, parties, pourcentage)
    wp = ctx["win_percentage_ranking"]
    assert len(wp) == 6
    expected_wp = [
        (1, "ERIC", 332, 963, 34.4756),
        (2, "LOUIS", 319, 940, 33.9362),
        (3, "DAVID", 318, 957, 33.2288),
        (4, "BENOIT", 22, 166, 13.2530),
        (5, "JULIEN", 18, 154, 11.6883),
        (6, "MEHDI", 5, 93, 5.3763),
    ]
    for i, row in enumerate(wp):
        assert row[0] == expected_wp[i][0]
        assert row[1] == expected_wp[i][1]
        assert row[2] == expected_wp[i][2]
        assert row[3] == expected_wp[i][3]
        assert round(row[4], 4) == expected_wp[i][4]


def test_elo_legacy_ranking_top3_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    elo_legacy_ranking = ctx["elo_legacy_ranking"]
    assert len(elo_legacy_ranking) >= 3

    top3_names = [row[1] for row in elo_legacy_ranking[:3]]
    assert set(top3_names) == {"LOUIS", "ERIC", "DAVID"}


def test_elo_legacy_scores_for_all_players_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    elo_ranking = ctx["elo_legacy_ranking"]
    expected_players = {"LOUIS", "ERIC", "DAVID", "BENOIT", "MEHDI", "JULIEN"}
    assert len(elo_ranking) == 6
    assert {row[1] for row in elo_ranking} == expected_players

    # Ordre: ELO décroissant puis nom (ex aequo en ordre alphabétique)
    actual_order = [row[1] for row in elo_ranking]
    assert set(actual_order) == set(expected_players)

    # ELO strictement décroissant (format: rank, name, elo)
    for i, row in enumerate(elo_ranking):
        name, elo = row[1], row[2]
        assert 1000 <= elo <= 2000, f"{name}: ELO {elo} hors plage"
        if i < len(elo_ranking) - 1:
            assert elo >= elo_ranking[i + 1][2], "Classement ELO doit être décroissant"


def test_elo_batch_scores_for_all_players_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    elo_ranking = ctx["elo_ranking"]
    expected_players = {"LOUIS", "ERIC", "DAVID", "BENOIT", "MEHDI", "JULIEN"}
    assert len(elo_ranking) == 6
    assert {row[1] for row in elo_ranking} == expected_players

    for i, row in enumerate(elo_ranking):
        name, elo = row[1], row[2]
        assert 1000 <= elo <= 2000, f"{name}: ELO {elo} hors plage"
        if i < len(elo_ranking) - 1:
            assert elo >= elo_ranking[i + 1][2], "Classement ELO batch doit être décroissant"


def _assert_elo_session_and_match_invariants(snapshot_path: str) -> None:
    """ELO session + ELO match : cohérence et ordre sur un export CSV d'intégration."""
    stats = build_stats_from_path(snapshot_path)
    ctx = stats.prepare_template_data()
    n = ctx["unique_players_count"]
    assert n >= 1

    for key in ("elo_ranking", "elo_match_ranking", "elo_legacy_ranking"):
        rows = ctx[key]
        assert len(rows) == n, key
        for i, row in enumerate(rows):
            _rank, name, elo = row[0], row[1], row[2]
            assert 1000 <= elo <= 2000, f"{key} {name}: {elo}"
            if i < len(rows) - 1:
                assert elo >= rows[i + 1][2], key

    em = ctx["elo_match_by_player"]
    assert set(em.keys()) == {row[1] for row in ctx["elo_match_ranking"]}
    for _p, v in em.items():
        assert 1000 <= v <= 2000
    assert ctx["elo_match_ranking"][0][2] == ctx["best_elo_match"]
    assert set(ctx["best_elo_match_players"]) == {
        row[1] for row in ctx["elo_match_ranking"] if row[2] == ctx["best_elo_match"]
    }

    assert ctx["best_elo"] == ctx["elo_ranking"][0][2]
    assert {row[1] for row in ctx["elo_ranking"] if row[2] == ctx["best_elo"]} == set(
        ctx["best_elo_players"]
    )


def test_elo_session_and_match_invariants_on_both_snapshots():
    for path in SNAPSHOT_PATHS_INTEGRATION:
        _assert_elo_session_and_match_invariants(path)


def test_elo_match_evolution_last_day_matches_match_ranking():
    stats = build_stats_from_path(MATCHS_MINIMAL)
    evo = stats.get_elo_match_evolution()
    assert len(evo) >= 1
    by_player = {name: score for name, score in stats.get_elo_match_ranking()}
    last = evo[-1]['elo_by_player']
    assert set(last.keys()) == set(by_player.keys())
    for name in by_player:
        assert abs(last[name] - by_player[name]) < 1e-6, (name, last[name], by_player[name])


def test_elo_match_evolution_by_match_end_state_and_template():
    stats = build_stats_from_path(MATCHS_MINIMAL)
    by_match = stats.get_elo_match_evolution_by_match()
    session_evo = stats.get_elo_evolution()
    assert by_match[0]['match_index'] == 0
    assert by_match[0].get('is_chart_baseline') is True
    assert by_match[0]['date'] == session_evo[0]['date']
    assert by_match[0]['formatted_date'] == session_evo[0]['formatted_date']
    by_player = {name: score for name, score in stats.get_elo_match_ranking()}
    last = by_match[-1]['elo_by_player']
    for name in by_player:
        assert abs(last[name] - by_player[name]) < 1e-6
    ctx = stats.prepare_template_data()
    assert 'elo_match_evolution' in ctx
    assert len(ctx['elo_match_evolution']) == len(by_match)


def test_elo_match_evolution_starts_with_session_baseline_on_date_filter():
    dm = SessionDataManager(local_file=SNAPSHOT_2026)
    dm.load_all()
    stats = SessionStatsManager(
        dm.get_sessions(),
        date_start='2025-06-03',
        date_end='2026-06-24',
    )
    session_evo = stats.get_elo_evolution()
    by_match = stats.get_elo_match_evolution_by_match()
    assert session_evo
    assert by_match
    assert by_match[0]['date'] == session_evo[0]['date']
    assert by_match[0]['formatted_date'] == session_evo[0]['formatted_date']
    for player, elo in by_match[0]['elo_by_player'].items():
        assert elo == 1500.0, player

    first_match_point = next(p for p in by_match if p.get('match_index', 0) > 0)
    prematch_flat = [p for p in by_match if p.get('is_prematch_flat')]
    assert prematch_flat
    assert all(
        all(v == 1500.0 for v in p['elo_by_player'].values()) for p in prematch_flat
    )
    assert prematch_flat[-1]['date'] < first_match_point['date']


def test_elo_batch_differs_from_legacy_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["elo_ranking"] != ctx["elo_legacy_ranking"]


def test_elo_batch_is_deterministic_on_both_snapshots():
    for snapshot_path in SNAPSHOT_PATHS_INTEGRATION:
        stats_1 = build_stats_from_path(snapshot_path)
        stats_2 = build_stats_from_path(snapshot_path)

        ctx_1 = stats_1.prepare_template_data()
        ctx_2 = stats_2.prepare_template_data()

        assert ctx_1["elo_ranking"] == ctx_2["elo_ranking"]
        assert ctx_1["elo_match_ranking"] == ctx_2["elo_match_ranking"]


def test_default_group_ranking_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["default_group"] == "DAVID-ERIC-LOUIS"
    # Classement complet du groupe par défaut (rank, player, total)
    assert ctx["default_ranking"] == [
        (1, "LOUIS", 218),
        (2, "DAVID", 205),
        (3, "ERIC", 201),
    ]


def test_group_sessions_by_date_on_both_snapshots():
    for snapshot_path in SNAPSHOT_PATHS_INTEGRATION:
        stats = build_stats_from_path(snapshot_path)

        sessions_by_date = stats.group_sessions_by_date()
        all_sessions = stats.sessions

        total_grouped = sum(len(v) for v in sessions_by_date.values())
        assert total_grouped == len(all_sessions)

        expected_dates = {session["date"][:10] for session in all_sessions if session.get("date")}
        assert set(sessions_by_date.keys()) == expected_dates


def test_detailed_stats_and_kill_relationships_on_both_snapshots():
    for snapshot_path in SNAPSHOT_PATHS_INTEGRATION:
        stats = build_stats_from_path(snapshot_path)
        ctx = stats.prepare_template_data()

        assert ctx["has_detailed_stats"] is True

        kill_death_ranking = ctx["kill_death_ranking"]
        assert len(kill_death_ranking) == ctx["unique_players_count"]
        for row in kill_death_ranking:
            player, kills, deaths, self_kills, kd_ratio = row[1], row[2], row[3], row[4], row[5]
            assert isinstance(player, str)
            assert kills >= 0
            assert deaths >= 0
            assert self_kills >= 0
            assert kd_ratio >= 0

        kill_relationships = ctx["kill_relationships"]
        players = {row[1] for row in kill_death_ranking}

        assert isinstance(kill_relationships, dict)
        assert set(kill_relationships.keys()).issubset(players)
        for killer, victims in kill_relationships.items():
            assert killer in players
            assert isinstance(victims, dict)
            assert set(victims.keys()).issubset(players)


EXPECTED_TEMPLATE_KEYS = frozenset({
    "unique_groups", "sorted_groups", "default_group", "rankings_by_group",
    "default_ranking", "date_debut", "date_fin", "date_debut_raw", "date_fin_raw",
    "date_debut_detailed", "date_debut_detailed_raw",
    "total_sessions", "unique_players_count", "best_players", "best_score",
    "best_percentage_players", "best_percentage", "win_percentage_ranking",
    "elo_ranking", "elo_evolution", "elo_match_evolution", "win_rate_evolution", "best_elo_players", "best_elo",
    "elo_legacy_ranking", "best_elo_legacy_players", "best_elo_legacy",
    "elo_match_ranking", "elo_match_by_player", "best_elo_match", "best_elo_match_players",
    "latest_date",
    "latest_sessions_parsed", "sessions_by_date", "all_sessions_data",
    "player_colors", "has_detailed_stats", "kill_death_ranking",
    "kill_sources_aggregated", "kill_relationships", "kill_relationships_totals",
    "all_players_for_matrix", "max_kills_in_matrix", "max_kills_in_matrix_totals",
    "top_killers", "top_deaths", "top_self_kills",
    "least_deaths_row", "least_self_kills_row",
    "best_kd_ratio", "best_kd_value",
})


def test_template_context_contract_on_both_snapshots():
    """Ensure prepare_template_data() returns all keys expected by the template (no regression)."""
    for snapshot_path in SNAPSHOT_PATHS_INTEGRATION:
        stats = build_stats_from_path(snapshot_path)
        ctx = stats.prepare_template_data()
        actual_keys = set(ctx.keys())
        missing = EXPECTED_TEMPLATE_KEYS - actual_keys
        extra = actual_keys - EXPECTED_TEMPLATE_KEYS
        assert not missing, f"Missing template keys: {missing}"
        assert not extra, f"Unexpected keys (update EXPECTED_TEMPLATE_KEYS if intentional): {extra}"


def test_best_elo_and_dates_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    assert ctx["best_elo"] == ctx["elo_ranking"][0][2]
    assert 1000 <= ctx["best_elo"] <= 2000
    assert ctx["best_elo_legacy_players"] == ["LOUIS"]
    assert ctx["best_elo_legacy"] == ctx["elo_legacy_ranking"][0][2]
    assert 1000 <= ctx["best_elo_legacy"] <= 2000
    assert ctx["best_elo_match"] == ctx["elo_match_ranking"][0][2]
    assert 1000 <= ctx["best_elo_match"] <= 2000

    assert ctx["date_debut_raw"] == "2025-06-03"
    assert ctx["date_fin_raw"] == "2026-02-25"

    assert ctx["rankings_by_group"][ctx["default_group"]] == ctx["default_ranking"]
    assert ctx["sorted_groups"][0] == "DAVID-ERIC-LOUIS"


def test_top_killers_deaths_and_kd_from_snapshot():
    stats = build_stats_from_snapshot()
    ctx = stats.prepare_template_data()

    # Top killers: rows are (rank, player, ...); player at index 1
    top_killers = ctx["top_killers"]
    assert len(top_killers) == 5
    assert [t[1] for t in top_killers] == ["DAVID", "LOUIS", "ERIC", "MEHDI", "BENOIT"]

    # Top deaths: same structure
    top_deaths = ctx["top_deaths"]
    assert len(top_deaths) == 5
    assert [t[1] for t in top_deaths] == ["MEHDI", "ERIC", "DAVID", "LOUIS", "JULIEN"]

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
    cases = [
        (SNAPSHOT_2025, "2026-01-01", "2026-02-25"),
        (SNAPSHOT_2026, "2026-01-01", "2026-04-23"),
    ]
    for snapshot_path, date_start, date_end in cases:
        manager = SessionDataManager(local_file=snapshot_path)
        manager.load_all()
        sessions = manager.get_sessions()
        full_n = len(sessions)

        full = SessionStatsManager(sessions)
        full_ctx = full.prepare_template_data()
        assert full_ctx["total_sessions"] == full_n

        filtered = SessionStatsManager(sessions, date_start=date_start, date_end=date_end)
        filtered_ctx = filtered.prepare_template_data()
        assert filtered_ctx["total_sessions"] < full_n
        assert filtered_ctx["date_debut_raw"] >= date_start
        assert filtered_ctx["date_fin_raw"] <= date_end


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


def test_matchs_minimal_parse_and_session_without_field():
    """matchsResults: session avec / sans champ ; algorithme ELO match ne lève pas."""
    m = SessionDataManager(local_file=MATCHS_MINIMAL)
    m.load_all()
    sessions = sorted(m.get_sessions(), key=lambda s: s.get("date", ""))
    assert len(sessions) == 3
    assert SessionDataManager.parse_matchs_results(sessions[0]) == [{"A": 3, "B": 1}]
    assert len(SessionDataManager.parse_matchs_results(sessions[1])) == 3
    assert SessionDataManager.parse_matchs_results(sessions[2]) == []

    sm = SessionStatsManager(m.get_sessions())
    r = sm.calculate_elo_match_ratings()
    assert isinstance(r, dict)
    _ = sm.prepare_template_data()


if __name__ == "__main__":
    g = globals()
    for _name in sorted(g):
        if not _name.startswith("test_"):
            continue
        g[_name]()
    print("ok:", len([n for n in g if n.startswith("test_")]), "tests")
