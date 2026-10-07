import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_manager import SessionDataManager
from src.session_records import build_session_records
from src.stats_manager import SessionStatsManager

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SNAPSHOT_2026_LIVE = os.path.join(DATA_DIR, "TowerFallStat_snapshot_2026-10-03.csv")


def _today(kill, death, self_kills):
    return {"kill": kill, "death": death, "self": self_kills, "killFrom": {}, "killBy": {}}


def _session(day, today_win, today=None, matches=None):
    data = {"todayWin": today_win, "total": {}}
    if today is not None:
        data["today"] = today
    if matches is not None:
        data["matchsResults"] = matches
    return {"id": "-".join(sorted(today_win)), "date": day, "mode": "HeadHunters", "data": data}


def _records(sessions, elo_deltas=None):
    return {r["key"]: r for r in build_session_records(sessions, elo_deltas or [])}


def _holders(record):
    return [(h["player"], h["date"]) for h in record["holders"]]


def test_best_session_score_keeps_every_tied_holder_oldest_first():
    sessions = [
        _session("2026-06-08", {"ERIC": 12, "LOUIS": 3}),
        _session("2026-06-01", {"ERIC": 4, "LOUIS": 12}),
    ]
    record = _records(sessions)["best_session_score"]
    assert record["value"] == "12"
    assert _holders(record) == [("LOUIS", "2026-06-01"), ("ERIC", "2026-06-08")]
    assert [h["session_key"] for h in record["holders"]] == [
        "2026-06-01|ERIC-LOUIS|HeadHunters",
        "2026-06-08|ERIC-LOUIS|HeadHunters",
    ]


def test_best_streak_counts_consecutive_wins_inside_a_session():
    matches = [
        {"ERIC": 10, "LOUIS": 9},
        {"ERIC": 10, "LOUIS": 4},
        {"ERIC": 10, "LOUIS": 7},
        {"ERIC": 9, "LOUIS": 10},
    ]
    sessions = [_session("2026-06-01", {"ERIC": 3, "LOUIS": 1}, matches=matches)]
    record = _records(sessions)["best_streak"]
    assert record["value"] == "3"
    assert _holders(record) == [("ERIC", "2026-06-01")]


def test_most_kills_session_uses_today_stats():
    sessions = [
        _session("2026-06-01", {"ERIC": 5, "LOUIS": 5}, {
            "ERIC": _today(80, 60, 1),
            "LOUIS": _today(60, 80, 2),
        }),
    ]
    sessions[0]["data"]["total"] = {"LOUIS": {"kill": 999}}
    record = _records(sessions)["most_kills_session"]
    assert record["value"] == "80"
    assert _holders(record) == [("ERIC", "2026-06-01")]


def test_cleanest_session_ignores_sessions_below_min_matches():
    sessions = [
        _session("2026-06-01", {"ERIC": 2, "LOUIS": 2}, {
            "ERIC": _today(10, 1, 0),
            "LOUIS": _today(1, 10, 0),
        }),
        _session("2026-06-08", {"ERIC": 6, "LOUIS": 4}, {
            "ERIC": _today(50, 25, 0),
            "LOUIS": _today(25, 50, 0),
        }),
    ]
    record = _records(sessions)["cleanest_session"]
    assert record["value"] == "2,50"
    assert _holders(record) == [("ERIC", "2026-06-08")]


def test_no_self_kill_session_picks_longest_clean_session():
    sessions = [
        _session("2026-06-01", {"ERIC": 4, "LOUIS": 4}, {
            "ERIC": _today(40, 40, 0),
            "LOUIS": _today(40, 40, 1),
        }),
        _session("2026-06-08", {"ERIC": 6, "LOUIS": 6}, {
            "ERIC": _today(60, 60, 2),
            "LOUIS": _today(60, 60, 0),
        }),
    ]
    record = _records(sessions)["no_self_kill_session"]
    assert record["value"] == "12"
    assert _holders(record) == [("LOUIS", "2026-06-08")]


def test_best_elo_gain_from_session_deltas():
    first = _session("2026-06-01", {"ERIC": 5, "LOUIS": 1})
    second = _session("2026-06-08", {"ERIC": 1, "LOUIS": 5})
    deltas = [(first, {"ERIC": 16.0, "LOUIS": -16.0}), (second, {"ERIC": -17.4, "LOUIS": 17.4})]
    record = _records([first, second], deltas)["best_elo_gain"]
    assert record["value"] == "+17"
    assert _holders(record) == [("LOUIS", "2026-06-08")]


def test_records_without_data_are_omitted():
    sessions = [_session("2026-06-01", {"ERIC": 3, "LOUIS": 2})]
    assert set(_records(sessions)) == {"best_session_score"}


def test_records_on_live_snapshot():
    manager = SessionDataManager(local_file=SNAPSHOT_2026_LIVE)
    manager.load_all()
    ctx = SessionStatsManager(manager.get_sessions()).prepare_template_data()

    records = {r["key"]: r for r in ctx["session_records"]}
    assert set(records) == {
        "best_session_score", "best_streak", "most_kills_session",
        "best_elo_gain", "cleanest_session", "no_self_kill_session",
    }
    assert records["best_session_score"]["value"] == "34"
    assert _holders(records["best_session_score"]) == [("DAVID", "17/09/2025")]
    assert records["most_kills_session"]["value"] == "485"
    assert _holders(records["most_kills_session"]) == [("DAVID", "17/01/2026")]
    session_keys = {s["session_select_id"] for s in ctx["all_sessions_data"]}
    for record in records.values():
        assert record["holders"]
        assert all(h["session_key"] in session_keys for h in record["holders"])
        assert record["title"] and record["flavor"] and record["unit"]
