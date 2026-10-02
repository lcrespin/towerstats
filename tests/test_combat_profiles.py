import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.combat_profiles import (
    EVENING_BUCKET_LABELS,
    build_combat_profiles,
    build_evening_curve,
    session_own_matches,
)
from src.data_manager import SessionDataManager
from src.stats_manager import SessionStatsManager

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SNAPSHOT_2026_LIVE = os.path.join(DATA_DIR, "TowerFallStat_snapshot_2026-06-30.csv")


def _today(kill, death, self_kills, kill_from, kill_by):
    return {
        "kill": kill,
        "death": death,
        "self": self_kills,
        "killFrom": kill_from,
        "killBy": kill_by,
    }


def _session(day, today_win, today, matches=None):
    data = {"todayWin": today_win, "today": today, "total": {}}
    if matches is not None:
        data["matchsResults"] = matches
    return {
        "id": "-".join(sorted(today_win)),
        "date": day,
        "mode": "HeadHunters",
        "data": data,
    }


def _by_player(profiles):
    return {p["player"]: p for p in profiles}


def test_session_own_matches_drops_matches_carried_over_from_previous_sessions():
    previous = [{"ERIC": 10, "LOUIS": 3}, {"ERIC": 2, "LOUIS": 10}]
    tonight = [{"ERIC": 10, "LOUIS": 9}]
    session = _session("2026-06-02", {"ERIC": 1, "LOUIS": 0}, {}, previous + tonight)
    assert session_own_matches(session) == tonight


def test_session_own_matches_keeps_everything_when_counts_match():
    matches = [{"ERIC": 10, "LOUIS": 3}, {"ERIC": 2, "LOUIS": 10}]
    session = _session("2026-06-02", {"ERIC": 1, "LOUIS": 1}, {}, matches)
    assert session_own_matches(session) == matches


def test_session_own_matches_without_scores():
    session = _session("2026-06-02", {"ERIC": 1, "LOUIS": 1}, {})
    assert session_own_matches(session) == []


def test_profile_uses_today_stats_not_cumulative_totals():
    sessions = [
        _session("2026-06-01", {"ERIC": 6, "LOUIS": 4}, {
            "ERIC": _today(60, 40, 2, {"Arrow": 40}, {"LOUIS": 38, "ERIC": 2}),
            "LOUIS": _today(40, 60, 1, {"Arrow": 60}, {"ERIC": 59, "LOUIS": 1}),
        }),
        _session("2026-06-08", {"ERIC": 5, "LOUIS": 5}, {
            "ERIC": _today(50, 50, 0, {"Arrow": 50}, {"LOUIS": 50}),
            "LOUIS": _today(50, 50, 0, {"Arrow": 50}, {"ERIC": 50}),
        }),
    ]
    sessions[1]["data"]["total"] = {"ERIC": {"kill": 999, "death": 999}}

    eric = _by_player(build_combat_profiles(sessions))["ERIC"]
    assert eric["matches"] == 20
    assert eric["kills"] == 110
    assert eric["deaths"] == 90
    assert eric["kd"] == "1,22"


def test_badge_kamikaze_for_self_kill_outlier_others_stay_regular():
    today = {
        "ERIC": _today(50, 50, 20, {}, {}),
        "LOUIS": _today(50, 50, 2, {}, {}),
        "DAVID": _today(50, 50, 2, {}, {}),
        "BENOIT": _today(50, 50, 2, {}, {}),
    }
    sessions = [_session("2026-06-01", {"ERIC": 5, "LOUIS": 5, "DAVID": 5, "BENOIT": 5}, today)]
    profiles = _by_player(build_combat_profiles(sessions))
    assert profiles["ERIC"]["badge"]["title"] == "Kamikaze"
    assert "1,00 fois par match" in profiles["ERIC"]["badge"]["detail"]
    for player in ("LOUIS", "DAVID", "BENOIT"):
        assert profiles[player]["badge"]["title"] == "Réglementaire"


def test_badge_sniper_for_kd_outlier():
    today = {
        "ERIC": _today(150, 50, 0, {}, {}),
        "LOUIS": _today(50, 50, 0, {}, {}),
        "DAVID": _today(50, 50, 0, {}, {}),
        "BENOIT": _today(50, 50, 0, {}, {}),
    }
    sessions = [_session("2026-06-01", {"ERIC": 5, "LOUIS": 5, "DAVID": 5, "BENOIT": 5}, today)]
    eric = _by_player(build_combat_profiles(sessions))["ERIC"]
    assert eric["badge"]["title"] == "Sniper"
    assert eric["badge"]["detail"] == "K/D de 3,00, contre 1,50 en moyenne"


def test_badge_night_owl_and_early_bird_from_session_phases():
    matches = [{"ERIC": 4, "LOUIS": 10}] * 10 + [{"ERIC": 10, "LOUIS": 4}] * 10
    today = {
        "ERIC": _today(140, 140, 0, {}, {}),
        "LOUIS": _today(140, 140, 0, {}, {}),
    }
    sessions = [_session("2026-06-01", {"ERIC": 10, "LOUIS": 10}, today, matches)]
    profiles = _by_player(build_combat_profiles(sessions))
    assert profiles["ERIC"]["badge"]["title"] == "Noctambule"
    assert profiles["ERIC"]["badge"]["detail"] == "100 % de victoires après le 10e match, contre 0 % avant"
    assert profiles["LOUIS"]["badge"]["title"] == "Lève-tôt"


def test_nemesis_and_victim_are_normalized_by_matches_played_together():
    sessions = [
        _session("2026-06-01", {"ERIC": 5, "LOUIS": 5, "DAVID": 10}, {
            "ERIC": _today(30, 40, 0, {"Arrow": 40}, {"LOUIS": 10, "DAVID": 30}),
            "LOUIS": _today(30, 40, 0, {"Arrow": 40}, {"ERIC": 25, "DAVID": 15}),
            "DAVID": _today(45, 25, 0, {"Arrow": 25}, {"ERIC": 5, "LOUIS": 20}),
        }),
        _session("2026-06-08", {"ERIC": 30, "LOUIS": 30}, {
            "ERIC": _today(240, 60, 0, {"Arrow": 60}, {"LOUIS": 60}),
            "LOUIS": _today(60, 240, 0, {"Arrow": 240}, {"ERIC": 240}),
        }),
    ]
    eric = _by_player(build_combat_profiles(sessions))["ERIC"]
    assert eric["nemesis"]["player"] == "DAVID"
    assert eric["nemesis"]["per_match"] == "1,5"
    assert eric["victim"]["player"] == "LOUIS"
    assert eric["self_kills"] == 0


def test_close_matches_and_best_streak_from_own_matches():
    matches = [
        {"ERIC": 10, "LOUIS": 9},
        {"ERIC": 10, "LOUIS": 4},
        {"ERIC": 10, "LOUIS": 7},
        {"ERIC": 9, "LOUIS": 10},
        {"ERIC": 3, "LOUIS": 10},
    ]
    sessions = [
        _session("2026-06-01", {"ERIC": 3, "LOUIS": 2}, {
            "ERIC": _today(42, 33, 0, {"Arrow": 33}, {"LOUIS": 33}),
            "LOUIS": _today(40, 42, 0, {"Arrow": 42}, {"ERIC": 42}),
        }, matches),
    ]
    profiles = _by_player(build_combat_profiles(sessions, min_matches=1))
    eric, louis = profiles["ERIC"], profiles["LOUIS"]
    assert eric["scored_matches"] == 5
    assert (eric["close_wins"], eric["heartbreaks"]) == (1, 1)
    assert (louis["close_wins"], louis["heartbreaks"]) == (1, 1)
    assert eric["best_streak"]["length"] == 3
    assert louis["best_streak"]["length"] == 2


def test_players_below_min_matches_have_no_profile():
    sessions = [
        _session("2026-06-01", {"ERIC": 3, "LOUIS": 2}, {
            "ERIC": _today(30, 20, 0, {"Arrow": 20}, {"LOUIS": 20}),
            "LOUIS": _today(20, 30, 0, {"Arrow": 30}, {"ERIC": 30}),
        }),
    ]
    assert build_combat_profiles(sessions) == []


def test_evening_curve_buckets_matches_by_rank_in_session():
    matches = [{"ERIC": 10, "LOUIS": 5}] * 5 + [{"ERIC": 5, "LOUIS": 10}] * 5
    sessions = [_session("2026-06-01", {"ERIC": 5, "LOUIS": 5}, {}, matches)]

    curve = build_evening_curve(sessions, min_player_matches=1)

    assert curve["labels"] == list(EVENING_BUCKET_LABELS)
    eric = curve["players"]["ERIC"]
    assert eric[0] == {"rate": 1.0, "wins": 5, "played": 5}
    assert eric[1] == {"rate": 0.0, "wins": 0, "played": 5}
    assert eric[2] == {"rate": None, "wins": 0, "played": 0}


def test_evening_curve_hides_small_buckets():
    matches = [{"ERIC": 10, "LOUIS": 5}] * 7
    sessions = [_session("2026-06-01", {"ERIC": 7, "LOUIS": 0}, {}, matches)]
    eric = build_evening_curve(sessions, min_player_matches=1)["players"]["ERIC"]
    assert eric[0]["rate"] == 1.0
    assert eric[1] == {"rate": None, "wins": 2, "played": 2}


def test_profiles_and_curve_on_live_snapshot():
    manager = SessionDataManager(local_file=SNAPSHOT_2026_LIVE)
    manager.load_all()
    stats = SessionStatsManager(manager.get_sessions())
    ctx = stats.prepare_template_data()

    profiles = ctx["combat_profiles"]
    assert profiles
    for profile in profiles:
        assert profile["matches"] >= 10
        assert profile["badge"]["title"]
        assert profile["close_wins"] + profile["heartbreaks"] <= profile["scored_matches"]
        if profile["nemesis"]:
            assert profile["nemesis"]["player"] != profile["player"]

    curve = ctx["evening_curve"]
    assert curve["labels"] == list(EVENING_BUCKET_LABELS)
    for buckets in curve["players"].values():
        assert len(buckets) == len(EVENING_BUCKET_LABELS)
        for bucket in buckets:
            assert bucket["wins"] <= bucket["played"]
