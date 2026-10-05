import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_manager import SessionDataManager
from src.session_details import build_session_details
from src.stats_manager import SessionStatsManager

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SNAPSHOT_2026_LIVE = os.path.join(DATA_DIR, "TowerFallStat_snapshot_2026-10-03.csv")


def _today(kill, death, self_kills, kill_from=None, kill_by=None):
    return {
        "win": 0, "kill": kill, "death": death, "self": self_kills,
        "killFrom": kill_from or {}, "killBy": kill_by or {},
    }


def _session(data):
    session = {"id": "", "date": "2026-06-01", "mode": "HeadHunters", "data": data}
    SessionDataManager.normalize_session_players(session)
    session["id"] = SessionDataManager.calculate_session_id_from_players(session)
    return session


def _awards(details):
    return {a["title"]: (a["value"], a["holders"]) for a in details["awards"]}


def test_legacy_session_only_has_hour_and_match_count():
    details = build_session_details(_session({
        "date": "2026-06-01-23",
        "todayWin": {"ERIC": 4, "LOUIS": 2},
        "totalWin": {"ERIC": 4, "LOUIS": 2},
    }))
    assert details == {
        "hour": 23,
        "match_count": 6,
        "combat": {},
        "matches": [],
        "awards": [],
        "scoreboard": [],
        "lead_changes": 0,
        "ahead_matrix": {},
        "headline": None,
        "target": None,
    }


def test_detailed_session_exposes_combat_matches_and_awards():
    details = build_session_details(_session({
        "date": "2026-06-01-22",
        "todayWin": {"ERIC": 2, "LOUIS": 1},
        "totalWin": {"ERIC": 2, "LOUIS": 1},
        "today": {
            "ERIC": _today(9, 5, 0, {"Arrow": 4, "LOUIS": 1}, {"LOUIS": 5}),
            "LOUIS": _today(5, 10, 2, {"Arrow": 7, "Lava": 3}, {"ERIC": 8, "LOUIS": 2}),
        },
        "total": {},
        "matchsResults": [{"ERIC": 3, "LOUIS": 1}, {"ERIC": 3, "LOUIS": 2}, {"ERIC": 1, "LOUIS": 3}],
    }))
    assert details["match_count"] == 3
    assert [m["winner"] for m in details["matches"]] == ["ERIC", "ERIC", "LOUIS"]
    assert details["combat"]["ERIC"]["killFrom"] == {"Arrow": 4}
    assert details["combat"]["LOUIS"]["killBy"] == {"ERIC": 8, "LOUIS": 2}
    awards = _awards(details)
    assert awards["Meilleur tueur"] == (9, [["ERIC"]])
    assert awards["Meilleure série"] == (2, [["ERIC"]])
    assert awards["Bourreau"] == (8, [["ERIC", "LOUIS"]])
    assert awards["Kamikaze"] == (2, [["LOUIS"]])


def test_awards_skip_zero_values_and_keep_ties():
    details = build_session_details(_session({
        "todayWin": {"ERIC": 1, "LOUIS": 1},
        "totalWin": {"ERIC": 1, "LOUIS": 1},
        "today": {"ERIC": _today(4, 4, 0), "LOUIS": _today(4, 4, 0)},
        "total": {},
    }))
    awards = _awards(details)
    assert awards == {"Meilleur tueur": (4, [["ERIC"], ["LOUIS"]])}


def test_matches_expose_margin_and_drama():
    details = build_session_details(_session({
        "todayWin": {"ERIC": 2, "LOUIS": 1},
        "totalWin": {"ERIC": 2, "LOUIS": 1},
        "matchsResults": [
            {"ERIC": 5, "LOUIS": 4},
            {"ERIC": 8, "LOUIS": 4},
            {"ERIC": 3, "LOUIS": 5},
        ],
    }))
    kinds = [(m["winner"], m["margin"], m["kind"]) for m in details["matches"]]
    assert kinds == [
        ("ERIC", 1, "close"),
        ("ERIC", 4, "blowout"),
        ("LOUIS", 2, "normal"),
    ]


def test_target_is_most_common_winning_score():
    details = build_session_details(_session({
        "todayWin": {"ERIC": 3, "LOUIS": 1},
        "totalWin": {"ERIC": 3, "LOUIS": 1},
        "matchsResults": [
            {"ERIC": 10, "LOUIS": 4},
            {"ERIC": 11, "LOUIS": 9},
            {"ERIC": 10, "LOUIS": 7},
            {"ERIC": 3, "LOUIS": 10},
        ],
    }))
    assert details["target"] == 10


def test_scoreboard_win_matrix_and_headline():
    details = build_session_details(_session({
        "todayWin": {"ERIC": 2, "LOUIS": 1, "DAVID": 1},
        "totalWin": {"ERIC": 2, "LOUIS": 1, "DAVID": 1},
        "matchsResults": [
            {"ERIC": 5, "LOUIS": 4, "DAVID": 2},
            {"ERIC": 3, "LOUIS": 8, "DAVID": 2},
            {"ERIC": 10, "LOUIS": 3, "DAVID": 1},
            {"ERIC": 4, "LOUIS": 3, "DAVID": 6},
        ],
    }))
    assert [row["leader"] for row in details["scoreboard"]] == ["ERIC", None, "ERIC", "ERIC"]
    assert details["scoreboard"][-1]["wins"] == {"ERIC": 2, "LOUIS": 1, "DAVID": 1}
    assert details["lead_changes"] == 0
    assert details["ahead_matrix"]["ERIC"] == {"LOUIS": 3, "DAVID": 3}
    assert details["ahead_matrix"]["LOUIS"] == {"ERIC": 1, "DAVID": 3}
    assert details["ahead_matrix"]["DAVID"] == {"ERIC": 1, "LOUIS": 1}
    assert details["headline"]["index"] == 3
    assert details["headline"]["winner"] == "ERIC"
    assert details["headline"]["margin"] == 7


def test_new_awards_from_session_story():
    details = build_session_details(_session({
        "todayWin": {"ERIC": 2, "LOUIS": 3, "DAVID": 1},
        "totalWin": {"ERIC": 2, "LOUIS": 3, "DAVID": 1},
        "today": {
            "ERIC": _today(20, 12, 0),
            "LOUIS": _today(22, 10, 1),
            "DAVID": _today(8, 18, 0),
        },
        "total": {},
        "matchsResults": [
            {"ERIC": 5, "LOUIS": 4, "DAVID": 2},
            {"ERIC": 8, "LOUIS": 4, "DAVID": 3},
            {"ERIC": 6, "LOUIS": 3, "DAVID": 4},
            {"ERIC": 2, "LOUIS": 6, "DAVID": 3},
            {"ERIC": 3, "LOUIS": 4, "DAVID": 3},
            {"ERIC": 2, "LOUIS": 3, "DAVID": 6},
        ],
    }))
    awards = _awards(details)
    assert awards["Comeback"] == (2, [["LOUIS"]])
    assert awards["Clutch"] == (1, [["ERIC"], ["LOUIS"]])
    assert "Finisher" not in awards
    assert "Cible" not in awards


def test_template_data_attaches_details_to_every_session_and_latest():
    manager = SessionDataManager(local_file=SNAPSHOT_2026_LIVE)
    manager.load_all()
    ctx = SessionStatsManager(manager.get_sessions()).prepare_template_data()
    entries = ctx["all_sessions_data"]
    assert entries and all("details" in e for e in entries)
    assert any(e["details"]["matches"] for e in entries)
    assert any(e["details"]["combat"] and e["details"]["awards"] for e in entries)
    latest = ctx["latest_sessions_data"]
    assert [e["session_select_id"] for e in latest] == [
        SessionDataManager.format_session_select_id(s["session"])
        for s in ctx["latest_sessions_parsed"]
    ]
