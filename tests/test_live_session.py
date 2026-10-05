import os
import sys
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_manager import SessionDataManager
from src.live_session import (
    LIVE_WINDOW_HOURS,
    build_live_session_entry,
    find_live_session,
    is_live_demo,
)
from src.seasons import get_current_season_id, season_date_bounds
from src.stats_manager import SessionStatsManager

PARIS = ZoneInfo("Europe/Paris")


def _session(day, hour, wins, group="ERIC-LOUIS", mode="HeadHunters"):
    return {
        "id": group,
        "date": day,
        "mode": mode,
        "data": {
            "todayWin": dict(wins),
            "totalWin": dict(wins),
            "date": f"{day}-{hour:02d}",
        },
    }


def test_session_written_this_hour_is_live():
    now = datetime(2026, 10, 4, 22, 30, tzinfo=PARIS)
    live = _session("2026-10-04", 22, {"ERIC": 2, "LOUIS": 1})
    assert find_live_session([live], now=now) is live


def test_session_written_previous_hour_is_live():
    now = datetime(2026, 10, 4, 22, 5, tzinfo=PARIS)
    live = _session("2026-10-04", 21, {"ERIC": 2, "LOUIS": 1})
    assert find_live_session([live], now=now) is live
    assert LIVE_WINDOW_HOURS == 2


def test_session_written_two_hours_ago_is_not_live():
    now = datetime(2026, 10, 4, 22, 30, tzinfo=PARIS)
    old = _session("2026-10-04", 20, {"ERIC": 2, "LOUIS": 1})
    assert find_live_session([old], now=now) is None


def test_session_crossing_midnight_is_still_live():
    now = datetime(2026, 10, 5, 0, 20, tzinfo=PARIS)
    live = _session("2026-10-04", 23, {"ERIC": 2, "LOUIS": 1})
    assert find_live_session([live], now=now) is live


def test_most_recent_write_wins_when_several_are_live():
    now = datetime(2026, 10, 4, 22, 40, tzinfo=PARIS)
    earlier = _session("2026-10-04", 21, {"ERIC": 1, "LOUIS": 1}, group="DAVID-ERIC")
    later = _session("2026-10-04", 22, {"ERIC": 3, "MEHDI": 2}, group="ERIC-MEHDI")
    assert find_live_session([earlier, later], now=now) is later


def test_demo_mode_returns_latest_session_even_when_stale():
    now = datetime(2026, 10, 4, 22, 30, tzinfo=PARIS)
    older = _session("2026-09-01", 20, {"ERIC": 1, "LOUIS": 2})
    latest = _session("2026-09-10", 23, {"ERIC": 4, "LOUIS": 1})
    assert find_live_session([older, latest], now=now) is None
    assert find_live_session([older, latest], now=now, demo=True) is latest


def test_is_live_demo_reads_env_flag():
    with patch.dict(os.environ, {"TOWERSTATS_LIVE_DEMO": "1"}, clear=False):
        assert is_live_demo() is True
    with patch.dict(os.environ, {"TOWERSTATS_LIVE_DEMO": "0"}, clear=False):
        assert is_live_demo() is False


def test_live_entry_matches_archive_entry_for_same_session():
    previous = _session("2026-08-20", 20, {"ERIC": 2, "LOUIS": 1})
    other_group = _session("2026-08-25", 21, {"DAVID": 4, "ERIC": 1}, group="DAVID-ERIC")
    live = _session("2026-09-01", 22, {"ERIC": 3, "LOUIS": 4})
    sessions = [previous, other_group, live]
    with patch.object(SessionStatsManager, "prepare_template_data", side_effect=AssertionError):
        entry = build_live_session_entry(sessions, live)
    season_id = get_current_season_id(date.fromisoformat(live["date"]))
    start, end = season_date_bounds(season_id)
    filtered = SessionDataManager.filter_sessions_by_game_mode(sessions, live["mode"])
    filtered = SessionDataManager.filter_sessions_by_date(filtered, start, end)
    archive = SessionStatsManager(filtered).prepare_template_data()["all_sessions_data"]
    expected = next(
        item
        for item in archive
        if item["session_select_id"] == SessionDataManager.format_session_select_id(live)
    )
    assert entry == expected
    assert entry["details"]
    assert entry["players"]


def _fake_load_all(self):
    self.sessions = [
        _session("2026-08-14", 20, {"ERIC": 1, "LOUIS": 3}),
        _session("2026-08-26", 21, {"ERIC": 5, "LOUIS": 1}),
    ]


def _get_client():
    from src.main import app
    app.config["TESTING"] = True
    return app.test_client()


@patch.dict(os.environ, {"TOWERSTATS_LIVE_DEMO": ""})
@patch("src.main.load_win_messages", return_value={})
@patch("src.main.SessionDataManager.load_all", _fake_load_all)
def test_api_live_is_false_when_latest_session_is_stale(_messages):
    response = _get_client().get("/api/live")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"live": False, "session": None}


@patch.dict(os.environ, {"TOWERSTATS_LIVE_DEMO": "1"})
@patch("src.main.load_win_messages", return_value={})
@patch("src.main.SessionDataManager.load_all", _fake_load_all)
def test_demo_mode_exposes_latest_session_as_live(_messages):
    client = _get_client()
    html = client.get("/").get_data(as_text=True)
    assert 'id="live-button" class="live-button"' in html
    assert "live-button is-hidden" not in html
    assert "ERIC-LOUIS" in html
    payload = client.get("/api/live").get_json()
    assert payload["live"] is True
    assert payload["session"]["session_select_id"] == "2026-08-26|ERIC-LOUIS|HeadHunters"
