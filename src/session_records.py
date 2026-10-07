"""Best single-session feats (records to beat)."""

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .session_facts import (
    best_win_streaks,
    format_fr,
    match_outcome,
    session_own_matches,
    session_today_stats,
    session_win_count,
)
from .config import get_player_color
from .data_manager import SessionDataManager

MIN_RECORD_MATCHES = 5

RECORDS = (
    ('best_session_score', '🏆', 'Meilleur score en une soirée', 'Soirée de légende', 'victoires'),
    ('best_streak', '🔥', 'Plus longue série', 'Inarrêtable', "victoires d'affilée"),
    ('most_kills_session', '🏹', 'Plus de kills en une soirée', 'Moissonneuse', 'kills'),
    ('best_elo_gain', '📈', 'Plus gros gain ELO', 'Le casse du siècle', 'pts en une soirée'),
    ('cleanest_session', '🛋️', 'Soirée la plus propre', 'Survivant du canapé', 'morts /partie'),
    ('no_self_kill_session', '🧘', 'Zéro auto-kill', 'Zéro bavure', 'parties sans se suicider'),
)

# Candidate = (score where higher is better, player, session).
Candidate = Tuple[float, str, Dict[str, Any]]


def _best(candidates: Iterable[Candidate]) -> Tuple[Optional[float], List[Candidate]]:
    best_score: Optional[float] = None
    holders: List[Candidate] = []
    for candidate in candidates:
        score = candidate[0]
        if best_score is None or score > best_score:
            best_score, holders = score, [candidate]
        elif score == best_score:
            holders.append(candidate)
    return best_score, holders


def _session_scores(sessions):
    for session in sessions:
        for player, stats in SessionDataManager.parse_session_data(session).items():
            if stats['today'] > 0:
                yield stats['today'], player, session


def _streaks(sessions):
    for session in sessions:
        contests = (
            (match, match_outcome(match)[0]) for match in session_own_matches(session)
        )
        for player, length in best_win_streaks(contests).items():
            if length > 1:
                yield length, player, session


def _session_combat(sessions):
    for session in sessions:
        today = session_today_stats(session)
        if not today:
            continue
        played = session_win_count(session.get('data') or {}) or len(session_own_matches(session))
        for player, stats in today.items():
            yield session, player, stats, played


def _kills(sessions):
    for session, player, stats, _played in _session_combat(sessions):
        if stats['kill'] > 0:
            yield stats['kill'], player, session


def _clean(sessions):
    for session, player, stats, played in _session_combat(sessions):
        if played >= MIN_RECORD_MATCHES:
            yield -round(stats['death'] / played, 2), player, session


def _no_self_kill(sessions):
    for session, player, stats, played in _session_combat(sessions):
        if stats['self'] == 0 and played >= MIN_RECORD_MATCHES:
            yield played, player, session


def _elo_gains(elo_deltas):
    for session, deltas in elo_deltas:
        for player, delta in deltas.items():
            if delta > 0:
                yield round(delta), player, session


def build_session_records(
    sessions: List[Dict[str, Any]],
    elo_deltas: List[Tuple[Dict[str, Any], Dict[str, float]]],
    format_date: Optional[Callable[[str], str]] = None,
) -> List[Dict[str, Any]]:
    """One card per record that has data; ties keep every holder, oldest first."""
    sources = {
        'best_session_score': (_session_scores(sessions), lambda v: str(int(v))),
        'best_streak': (_streaks(sessions), lambda v: str(int(v))),
        'most_kills_session': (_kills(sessions), lambda v: str(int(v))),
        'best_elo_gain': (_elo_gains(elo_deltas), lambda v: f"+{int(v)}"),
        'cleanest_session': (_clean(sessions), lambda v: format_fr(-v, 2)),
        'no_self_kill_session': (_no_self_kill(sessions), lambda v: str(int(v))),
    }
    records = []
    for key, emoji, title, flavor, unit in RECORDS:
        candidates, fmt = sources[key]
        score, holders = _best(candidates)
        if score is None:
            continue
        seen = set()
        holder_rows = []
        for _score, player, session in sorted(holders, key=lambda c: (c[2].get('date', ''), c[1])):
            day = (session.get('date') or '')[:10]
            session_key = SessionDataManager.format_session_select_id(session)
            if (player, session_key) in seen:
                continue
            seen.add((player, session_key))
            holder_rows.append({
                'player': player,
                'color': get_player_color(player),
                'date': format_date(day) if format_date else day,
                'session_key': session_key,
            })
        records.append({
            'key': key,
            'emoji': emoji,
            'title': title,
            'flavor': flavor,
            'value': fmt(score),
            'unit': unit,
            'holders': holder_rows,
        })
    return records
