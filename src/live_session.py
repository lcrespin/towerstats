"""Detect a live TowerFall session from the last sheet write."""

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from .config import DEFAULT_GAME_MODE
from .data_manager import SessionDataManager
from .seasons import get_current_season_id, season_date_bounds
from .stats_manager import SessionStatsManager

PARIS = ZoneInfo("Europe/Paris")
LIVE_WINDOW_HOURS = 2
LIVE_DEMO_ENV = "TOWERSTATS_LIVE_DEMO"


def is_live_demo() -> bool:
    """True when local demo mode is enabled via TOWERSTATS_LIVE_DEMO=1."""
    return os.environ.get(LIVE_DEMO_ENV) == "1"


def _aware(now: Optional[datetime]) -> datetime:
    current = now or datetime.now(PARIS)
    if current.tzinfo is None:
        return current.replace(tzinfo=PARIS)
    return current.astimezone(PARIS)


def _session_write_dt(session: Dict[str, Any], require_hour: bool) -> Optional[datetime]:
    raw = (session.get("data") or {}).get("date") or ""
    date_obj, hour = SessionDataManager.parse_date_with_hour(str(raw))
    if date_obj is not None and hour is not None:
        return datetime(date_obj.year, date_obj.month, date_obj.day, hour, tzinfo=PARIS)
    if require_hour:
        return None
    day = SessionDataManager.extract_date_str(str(session.get("date", "")))
    try:
        parsed = date.fromisoformat(day)
    except ValueError:
        return None
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=PARIS)


def find_live_session(
    sessions: List[Dict[str, Any]],
    now: Optional[datetime] = None,
    demo: bool = False,
) -> Optional[Dict[str, Any]]:
    """Return the most recently written session inside the live window, or None."""
    now = _aware(now)
    scored = []
    for session in sessions:
        write_dt = _session_write_dt(session, require_hour=not demo)
        if write_dt is not None:
            scored.append((write_dt, session))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    if demo:
        return scored[0][1]
    now_hour = now.replace(minute=0, second=0, microsecond=0)
    for write_dt, session in scored:
        delta_hours = (now_hour - write_dt).total_seconds() / 3600
        if 0 <= delta_hours < LIVE_WINDOW_HOURS:
            return session
    return None


def build_live_session_entry(
    all_sessions: List[Dict[str, Any]],
    live: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Archive card for the live session; totals use the same group, mode and season as the archives."""
    if not live:
        return None
    mode = live.get("mode", DEFAULT_GAME_MODE)
    day = SessionDataManager.extract_date_str(str(live.get("date", "")))
    try:
        session_day = date.fromisoformat(day)
    except ValueError:
        session_day = date.today()
    season_start, season_end = season_date_bounds(get_current_season_id(session_day))
    sessions = SessionDataManager.filter_sessions_by_game_mode(all_sessions, mode)
    sessions = SessionDataManager.filter_sessions_by_date(sessions, season_start, season_end)
    sessions = [s for s in sessions if s.get("id") == live.get("id")]
    return SessionStatsManager(sessions).build_session_entry(live)


def get_live_session_payload(
    sessions: List[Dict[str, Any]],
    now: Optional[datetime] = None,
    demo: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Find the live session and return its archive entry, or None."""
    if demo is None:
        demo = is_live_demo()
    live = find_live_session(sessions, now=now, demo=demo)
    return build_live_session_entry(sessions, live)
