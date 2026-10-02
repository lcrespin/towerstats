"""Fiches de combat par joueur et courbe « Au fil de la soirée »."""

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any, Callable, Dict, List, Optional

from .config import canonical_player_name, get_player_color
from .data_manager import SessionDataManager

MIN_PROFILE_MATCHES = 10
MIN_RIVAL_MATCHES = 10
MIN_PHASE_MATCHES = 10
MIN_CLOSE_MATCHES = 8
MIN_BADGE_ZSCORE = 1.0
EARLY_MATCHES = 10
MIN_CURVE_PLAYER_MATCHES = 20
MIN_BUCKET_MATCHES = 5

EVENING_BUCKETS = ((1, 5), (6, 10), (11, 15), (16, 20), (21, None))
EVENING_BUCKET_LABELS = tuple(
    f"{start}+" if end is None else f"{start}–{end}" for start, end in EVENING_BUCKETS
)

# Death causes (killFrom) are nearly identical across players, so badges rely on traits that differ.
BADGES = {
    ('self_rate', 1): ('💥', 'Kamikaze'),
    ('self_rate', -1): ('🧘', 'Prudent'),
    ('kd', 1): ('🏹', 'Sniper'),
    ('kd', -1): ('🪶', 'Chair à flèches'),
    ('late_delta', 1): ('🌙', 'Noctambule'),
    ('late_delta', -1): ('🌅', 'Lève-tôt'),
    ('clutch', 1): ('🧊', 'Sang-froid'),
    ('clutch', -1): ('💔', 'Cœur fragile'),
}
DEFAULT_BADGE = ('🎯', 'Réglementaire', 'dans la moyenne partout, rien à signaler')


def _fr(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace('.', ',')


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(int(value), 0)


def _session_win_count(data: Dict[str, Any]) -> int:
    today_win = data.get('todayWin')
    if not isinstance(today_win, dict):
        return 0
    return sum(_count(v) for v in today_win.values())


def session_own_matches(session: Dict[str, Any]) -> List[Dict[str, int]]:
    """Matches actually played in this session, with at least two players."""
    return [m for m in SessionDataManager.parse_matchs_results(session) if len(m) >= 2]


def _session_today_stats(session: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    today = (session.get('data') or {}).get('today')
    if not isinstance(today, dict):
        return {}
    players: Dict[str, Dict[str, Any]] = {}
    for name, stats in today.items():
        player = canonical_player_name(name)
        if player is None or not isinstance(stats, dict):
            continue
        entry = players.setdefault(player, {'kill': 0, 'death': 0, 'self': 0, 'killBy': defaultdict(int)})
        for field in ('kill', 'death', 'self'):
            entry[field] += _count(stats.get(field))
        for killer, n in SessionDataManager._filter_kill_counts(stats.get('killBy'), keep_sources=False).items():
            entry['killBy'][killer] += _count(n)
    return players


def _match_outcome(match: Dict[str, int]):
    """(winner, runner_up, margin); winner is None on a tie for first."""
    ranked = sorted(match.items(), key=lambda x: x[1], reverse=True)
    if ranked[0][1] == ranked[1][1]:
        return None, None, 0
    runner_up = ranked[1][0] if len(ranked) < 3 or ranked[1][1] != ranked[2][1] else None
    return ranked[0][0], runner_up, ranked[0][1] - ranked[1][1]


def _badge_detail(trait: str, direction: int, stats: Dict[str, Any], group_mean: float) -> str:
    if trait == 'self_rate':
        return (
            f"se suicide {_fr(stats['self_rate'], 2)} fois par match, "
            f"contre {_fr(group_mean, 2)} en moyenne"
        )
    if trait == 'kd':
        return f"K/D de {_fr(stats['kd'], 2)}, contre {_fr(group_mean, 2)} en moyenne"
    if trait == 'late_delta':
        return (
            f"{round(stats['late_rate'] * 100)} % de victoires après le {EARLY_MATCHES}e match, "
            f"contre {round(stats['early_rate'] * 100)} % avant"
        )
    if direction > 0:
        return f"gagne {stats['close_wins']} de ses {stats['close_total']} matchs serrés"
    return f"perd {stats['close_total'] - stats['close_wins']} de ses {stats['close_total']} matchs serrés"


def _assign_badges(traits: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Give each player the trait where they stand out most, one badge per player and per title."""
    candidates = []
    for trait in ('self_rate', 'kd', 'late_delta', 'clutch'):
        values = {p: t[trait] for p, t in traits.items() if t.get(trait) is not None}
        if len(values) < 2:
            continue
        avg, spread = mean(values.values()), pstdev(values.values())
        if spread <= 0:
            continue
        for player, value in values.items():
            z = (value - avg) / spread
            if abs(z) >= MIN_BADGE_ZSCORE:
                candidates.append((abs(z), player, trait, 1 if z > 0 else -1, avg))

    badges: Dict[str, Dict[str, str]] = {}
    used = set()
    for _, player, trait, direction, avg in sorted(candidates, key=lambda c: (-c[0], c[1], c[2])):
        if player in badges or (trait, direction) in used:
            continue
        emoji, title = BADGES[(trait, direction)]
        badges[player] = {
            'emoji': emoji,
            'title': title,
            'detail': _badge_detail(trait, direction, traits[player], avg),
        }
        used.add((trait, direction))
    for player in traits:
        if player not in badges:
            emoji, title, detail = DEFAULT_BADGE
            badges[player] = {'emoji': emoji, 'title': title, 'detail': detail}
    return badges


def _pick_rival(player, rates):
    eligible = [(rate, other) for other, rate in rates.items() if other != player and rate > 0]
    if not eligible:
        return None
    rate, other = max(eligible, key=lambda x: (x[0], x[1]))
    return {'player': other, 'color': get_player_color(other), 'per_match': _fr(rate)}


def build_combat_profiles(
    sessions: List[Dict[str, Any]],
    format_date: Optional[Callable[[str], str]] = None,
    min_matches: int = MIN_PROFILE_MATCHES,
) -> List[Dict[str, Any]]:
    """One profile per player, from each session's own (non-cumulative) stats."""
    matches = defaultdict(int)
    kills = defaultdict(int)
    deaths = defaultdict(int)
    self_kills = defaultdict(int)
    killed_by = defaultdict(lambda: defaultdict(int))
    together = defaultdict(lambda: defaultdict(int))
    scored = defaultdict(int)
    close_wins = defaultdict(int)
    heartbreaks = defaultdict(int)
    phase_wins = defaultdict(lambda: [0, 0])
    phase_played = defaultdict(lambda: [0, 0])
    best_streak: Dict[str, Dict[str, Any]] = {}

    for session in sorted(sessions, key=lambda s: s.get('date', '')):
        today = _session_today_stats(session)
        if not today:
            continue
        own = session_own_matches(session)
        played = _session_win_count(session.get('data') or {}) or len(own)
        for player, stats in today.items():
            matches[player] += played
            kills[player] += stats['kill']
            deaths[player] += stats['death']
            self_kills[player] += stats['self']
            for killer, n in stats['killBy'].items():
                killed_by[player][killer] += n
            for other in today:
                if other != player:
                    together[player][other] += played

        streak = defaultdict(int)
        session_day = (session.get('date') or '')[:10]
        for rank, match in enumerate(own, start=1):
            winner, runner_up, margin = _match_outcome(match)
            phase = 0 if rank <= EARLY_MATCHES else 1
            for player in match:
                scored[player] += 1
                phase_played[player][phase] += 1
                if player == winner:
                    phase_wins[player][phase] += 1
                streak[player] = streak[player] + 1 if player == winner else 0
                if streak[player] and streak[player] > best_streak.get(player, {}).get('length', 0):
                    best_streak[player] = {
                        'length': streak[player],
                        'date': format_date(session_day) if format_date else session_day,
                    }
            if winner is not None and margin == 1:
                close_wins[winner] += 1
                if runner_up is not None:
                    heartbreaks[runner_up] += 1

    eligible = [p for p in matches if matches[p] >= min_matches]
    traits: Dict[str, Dict[str, Any]] = {}
    for player in eligible:
        early_played, late_played = phase_played[player]
        has_phases = early_played >= MIN_PHASE_MATCHES and late_played >= MIN_PHASE_MATCHES
        early_rate = phase_wins[player][0] / early_played if early_played else None
        late_rate = phase_wins[player][1] / late_played if late_played else None
        close_total = close_wins[player] + heartbreaks[player]
        traits[player] = {
            'self_rate': self_kills[player] / matches[player],
            'kd': kills[player] / deaths[player] if deaths[player] else None,
            'early_rate': early_rate,
            'late_rate': late_rate,
            'late_delta': late_rate - early_rate if has_phases else None,
            'close_wins': close_wins[player],
            'close_total': close_total,
            'clutch': close_wins[player] / close_total if close_total >= MIN_CLOSE_MATCHES else None,
        }
    badges = _assign_badges(traits)

    profiles = []
    for player in eligible:
        nemesis_rates = {
            other: killed_by[player][other] / n
            for other, n in together[player].items() if n >= MIN_RIVAL_MATCHES
        }
        victim_rates = {
            other: killed_by[other][player] / n
            for other, n in together[player].items() if n >= MIN_RIVAL_MATCHES
        }
        profiles.append({
            'player': player,
            'color': get_player_color(player),
            'matches': matches[player],
            'kills': kills[player],
            'deaths': deaths[player],
            'self_kills': self_kills[player],
            'kd': _fr(kills[player] / deaths[player], 2) if deaths[player] else '∞',
            'badge': badges[player],
            'nemesis': _pick_rival(player, nemesis_rates),
            'victim': _pick_rival(player, victim_rates),
            'scored_matches': scored[player],
            'close_wins': close_wins[player],
            'heartbreaks': heartbreaks[player],
            'best_streak': best_streak.get(player),
        })
    profiles.sort(key=lambda p: (-p['matches'], p['player']))
    return profiles


def _bucket_index(rank: int) -> int:
    for i, (start, end) in enumerate(EVENING_BUCKETS):
        if rank >= start and (end is None or rank <= end):
            return i
    return len(EVENING_BUCKETS) - 1


def build_evening_curve(
    sessions: List[Dict[str, Any]],
    min_player_matches: int = MIN_CURVE_PLAYER_MATCHES,
) -> Dict[str, Any]:
    """Win rate per player by match rank within the session."""
    wins = defaultdict(lambda: [0] * len(EVENING_BUCKETS))
    played = defaultdict(lambda: [0] * len(EVENING_BUCKETS))
    for session in sessions:
        for rank, match in enumerate(session_own_matches(session), start=1):
            bucket = _bucket_index(rank)
            winner, _, _ = _match_outcome(match)
            for player in match:
                played[player][bucket] += 1
                if player == winner:
                    wins[player][bucket] += 1

    players = {}
    for player in sorted(played):
        if sum(played[player]) < min_player_matches:
            continue
        players[player] = [
            {
                'rate': (w / p) if p >= MIN_BUCKET_MATCHES else None,
                'wins': w,
                'played': p,
            }
            for w, p in zip(wins[player], played[player])
        ]
    return {'labels': list(EVENING_BUCKET_LABELS), 'players': players}
