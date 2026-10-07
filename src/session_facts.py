"""Shared facts derived from a single session: matches, combat, streaks."""

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import canonical_player_name
from .data_manager import SessionDataManager


def format_fr(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace('.', ',')


def as_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(int(value), 0)


def session_win_count(data: Dict[str, Any]) -> int:
    today_win = data.get('todayWin')
    if not isinstance(today_win, dict):
        return 0
    return sum(as_count(v) for v in today_win.values())


def session_own_matches(session: Dict[str, Any]) -> List[Dict[str, int]]:
    """Matches actually played in this session, with at least two players."""
    return [m for m in SessionDataManager.parse_matchs_results(session) if len(m) >= 2]


def session_today_stats(session: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    today = (session.get('data') or {}).get('today')
    if not isinstance(today, dict):
        return {}
    players: Dict[str, Dict[str, Any]] = {}
    for name, stats in today.items():
        player = canonical_player_name(name)
        if player is None or not isinstance(stats, dict):
            continue
        entry = players.setdefault(
            player, {'kill': 0, 'death': 0, 'self': 0, 'killBy': defaultdict(int)}
        )
        for field in ('kill', 'death', 'self'):
            entry[field] += as_count(stats.get(field))
        for killer, n in SessionDataManager._filter_kill_counts(
            stats.get('killBy'), keep_sources=False
        ).items():
            entry['killBy'][killer] += as_count(n)
    return players


def match_outcome(match: Dict[str, int]):
    """(winner, runner_up, margin); winner is None on a tie for first."""
    ranked = sorted(match.items(), key=lambda x: x[1], reverse=True)
    if ranked[0][1] == ranked[1][1]:
        return None, None, 0
    runner_up = ranked[1][0] if len(ranked) < 3 or ranked[1][1] != ranked[2][1] else None
    return ranked[0][0], runner_up, ranked[0][1] - ranked[1][1]


def best_win_streaks(contests: Iterable[Tuple[Iterable[str], Optional[str]]]) -> Dict[str, int]:
    """Longest consecutive wins per player. contests: (players, winner)."""
    streak: Dict[str, int] = {}
    best: Dict[str, int] = {}
    for players, winner in contests:
        for player in players:
            streak[player] = streak.get(player, 0) + 1 if player == winner else 0
            best[player] = max(best.get(player, 0), streak[player])
    return best
