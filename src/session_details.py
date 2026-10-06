"""Archive extras for one session: combat, match rundown, and awards."""

from typing import Any, Dict, List, Optional, Tuple

from .session_facts import best_win_streaks, match_outcome, session_own_matches
from .config import canonical_player_name
from .data_manager import SessionDataManager

AWARDS = (
    ('kill', '🏹', 'Meilleur tueur', 'kills'),
    ('streak', '🔥', 'Meilleure série', "victoires d'affilée"),
    ('duel', '🎯', 'Bourreau', 'kills sur la même cible'),
    ('self', '💥', 'Kamikaze', 'auto-kills'),
    ('clutch', '🧊', 'Clutch', 'matchs serrés'),
    ('comeback', '📈', 'Comeback', 'victoires de plus en 2e mi-temps'),
)

CLOSE_MARGIN = 1
BLOWOUT_MARGIN = 3


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


def _match_kind(margin: int, winner: Optional[str]) -> str:
    if winner is None:
        return 'tie'
    if margin <= CLOSE_MARGIN:
        return 'close'
    if margin >= BLOWOUT_MARGIN:
        return 'blowout'
    return 'normal'


def _matches(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    matches = []
    for match in session_own_matches(session):
        winner, _runner, margin = match_outcome(match)
        matches.append({
            'scores': match,
            'winner': winner,
            'margin': margin,
            'kind': _match_kind(margin, winner),
        })
    return matches


def _scoreboard(matches: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    wins: Dict[str, int] = {}
    rows: List[Dict[str, Any]] = []
    prev_leader = None
    lead_changes = 0
    for match in matches:
        for player in match['scores']:
            wins.setdefault(player, 0)
        if match['winner']:
            wins[match['winner']] += 1
        best = max(wins.values()) if wins else 0
        leaders = sorted(player for player, count in wins.items() if count == best and best > 0)
        leader = leaders[0] if len(leaders) == 1 else None
        if prev_leader and leader and leader != prev_leader:
            lead_changes += 1
        if leader:
            prev_leader = leader
        rows.append({'wins': dict(wins), 'leader': leader})
    return rows, lead_changes


def _ahead_matrix(matches: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """matrix[a][b]: matches where a scored more kills than b."""
    matrix: Dict[str, Dict[str, int]] = {}
    for match in matches:
        scores = match['scores']
        for player, score in scores.items():
            row = matrix.setdefault(player, {})
            for other, other_score in scores.items():
                if other == player:
                    continue
                row.setdefault(other, 0)
                if score > other_score:
                    row[other] += 1
    return matrix


def _target(matches: List[Dict[str, Any]]) -> Optional[int]:
    """Points needed to win: the source has no field, so use the most common winning score."""
    counts: Dict[int, int] = {}
    for match in matches:
        if match['winner']:
            score = match['scores'][match['winner']]
            counts[score] = counts.get(score, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda score: (counts[score], -score))


def _half_deltas(matches: List[Dict[str, Any]]) -> Dict[str, int]:
    mid = len(matches) // 2
    if mid == 0:
        return {}

    def wins(chunk: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for match in chunk:
            winner = match['winner']
            if winner:
                counts[winner] = counts.get(winner, 0) + 1
        return counts

    first = wins(matches[:mid])
    second = wins(matches[mid:])
    players = set(first) | set(second)
    return {player: second.get(player, 0) - first.get(player, 0) for player in players}


def _award_candidates(combat, matches) -> Dict[str, Dict[tuple, int]]:
    duels = {
        (killer, victim): count
        for victim, stats in combat.items()
        for killer, count in stats['killBy'].items()
        if killer != victim
    }
    clutch = {}
    for match in matches:
        if match['kind'] == 'close' and match['winner']:
            key = (match['winner'],)
            clutch[key] = clutch.get(key, 0) + 1
    return {
        'kill': {(p,): s['kill'] for p, s in combat.items()},
        'streak': {
            (p,): n
            for p, n in best_win_streaks((m['scores'], m['winner']) for m in matches).items()
            if n > 1
        },
        'duel': duels,
        'self': {(p,): s['self'] for p, s in combat.items()},
        'clutch': clutch,
        'comeback': {(p,): n for p, n in _half_deltas(matches).items() if n > 0},
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
    scoreboard, lead_changes = _scoreboard(matches)
    return {
        'hour': _session_hour(session),
        'match_count': len(matches) or sum(s['today'] for s in players.values()),
        'combat': combat,
        'matches': matches,
        'awards': _awards(combat, matches),
        'scoreboard': scoreboard,
        'lead_changes': lead_changes,
        'ahead_matrix': _ahead_matrix(matches),
        'target': _target(matches),
    }
