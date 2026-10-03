"""Détails d'une session pour les archives : combat, déroulé des matchs et récompenses."""

from typing import Any, Dict, List, Optional

from .combat_profiles import _match_outcome, session_own_matches
from .config import canonical_player_name
from .data_manager import SessionDataManager

AWARDS = (
    ('kill', '🏹', 'Meilleur tueur', 'kills'),
    ('streak', '🔥', 'Meilleure série', "victoires d'affilée"),
    ('duel', '🎯', 'Bourreau', 'kills sur la même cible'),
    ('self', '💥', 'Kamikaze', 'auto-kills'),
)


def _session_hour(session: Dict[str, Any]) -> Optional[int]:
    raw = (session.get('data') or {}).get('date') or session.get('date') or ''
    _date, hour = SessionDataManager.parse_date_with_hour(str(raw))
    return hour


def _combat(players: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    combat = {}
    for player, stats in players.items():
        detailed = stats.get('detailed')
        if not detailed:
            continue
        combat[player] = {
            'kill': detailed['kill'],
            'death': detailed['death'],
            'self': detailed['self'],
            'killFrom': {
                source: count for source, count in detailed['killFrom'].items()
                if canonical_player_name(source) is None
            },
            'killBy': dict(detailed['killBy']),
        }
    return combat


def _matches(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {'scores': match, 'winner': _match_outcome(match)[0]}
        for match in session_own_matches(session)
    ]


def _best_streaks(matches: List[Dict[str, Any]]) -> Dict[str, int]:
    streak: Dict[str, int] = {}
    best: Dict[str, int] = {}
    for match in matches:
        for player in match['scores']:
            streak[player] = streak.get(player, 0) + 1 if player == match['winner'] else 0
            best[player] = max(best.get(player, 0), streak[player])
    return best


def _award_candidates(combat, matches) -> Dict[str, Dict[tuple, int]]:
    duels = {
        (killer, victim): count
        for victim, stats in combat.items()
        for killer, count in stats['killBy'].items()
        if killer != victim
    }
    return {
        'kill': {(p,): s['kill'] for p, s in combat.items()},
        'streak': {(p,): n for p, n in _best_streaks(matches).items() if n > 1},
        'duel': duels,
        'self': {(p,): s['self'] for p, s in combat.items()},
    }


def _awards(combat, matches) -> List[Dict[str, Any]]:
    candidates = _award_candidates(combat, matches)
    awards = []
    for key, emoji, title, unit in AWARDS:
        scores = candidates[key]
        best = max(scores.values(), default=0)
        if best <= 0:
            continue
        holders = sorted(list(h) for h, score in scores.items() if score == best)
        awards.append({'emoji': emoji, 'title': title, 'value': best, 'unit': unit, 'holders': holders})
    return awards


def build_session_details(session: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-ready details; empty fields when the source row predates detailed stats or match results."""
    players = SessionDataManager.parse_session_data(session)
    combat = _combat(players)
    matches = _matches(session)
    return {
        'hour': _session_hour(session),
        'match_count': len(matches) or sum(s['today'] for s in players.values()),
        'combat': combat,
        'matches': matches,
        'awards': _awards(combat, matches),
    }
