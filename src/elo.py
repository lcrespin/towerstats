"""Session Elo and match Elo: pairwise batch updates with caches."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List

from .data_manager import SessionDataManager


def session_ranks_from_sorted(sorted_players):
    """Dense ranks: same 'today' score => same rank (avoids arbitrary Elo gap on ties)."""
    player_ranks = {}
    current_rank = 0
    prev_today = None
    for rank_pos, (player, data) in enumerate(sorted_players, start=1):
        today = data['today']
        if prev_today is None or today != prev_today:
            current_rank = rank_pos
        player_ranks[player] = current_rank
        prev_today = today
    return player_ranks


def _pairwise_elo_deltas(
    ratings: Dict[str, float], ranks: Dict[str, int], k_factor: float
) -> Dict[str, float]:
    """Batch pairwise Elo deltas from ranks at the start of this contest."""
    names = sorted(ranks)
    deltas: Dict[str, float] = defaultdict(float)
    for i, player_a in enumerate(names):
        for player_b in names[i + 1:]:
            expected_a = 1 / (1 + 10 ** ((ratings[player_b] - ratings[player_a]) / 400))
            rank_a, rank_b = ranks[player_a], ranks[player_b]
            if rank_a < rank_b:
                actual_a = 1.0
            elif rank_a == rank_b:
                actual_a = 0.5
            else:
                actual_a = 0.0
            change = k_factor * (actual_a - expected_a)
            deltas[player_a] += change
            deltas[player_b] -= change
    return dict(deltas)


def _apply_elo_deltas(ratings: Dict[str, float], deltas: Dict[str, float]) -> None:
    for player, delta in deltas.items():
        ratings[player] += delta


def _elo_cache_key(initial_elo, k_factor) -> tuple:
    return (float(initial_elo), float(k_factor))


def _day_before(date_str: str) -> str | None:
    try:
        first_dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        return (first_dt - timedelta(days=1)).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def _ranks_from_kills(match: Dict[str, int]) -> Dict[str, int]:
    sorted_by_kills = sorted(match.items(), key=lambda x: x[1], reverse=True)
    sorted_players = [(player, {'today': kills}) for player, kills in sorted_by_kills]
    return session_ranks_from_sorted(sorted_players)


def _known_players(sessions: List[Dict[str, Any]]) -> List[str]:
    players: set = set()
    for session in sessions:
        players.update(SessionDataManager.parse_session_data(session).keys())
    return sorted(players)


def _session_date_str(session: Dict[str, Any]) -> str:
    return SessionDataManager.extract_date_str(str(session.get('date', '')))


class EloEngine:
    """Session and match Elo for a filtered session list."""

    def __init__(self, sessions: List[Dict[str, Any]], format_date: Callable[..., str]):
        self.sessions = sessions
        self.format_date = format_date
        self._session_cache: Dict[tuple, dict] = {}
        self._match_cache: Dict[tuple, dict] = {}

    def _session_elo_state(self, initial_elo=1500, k_factor=32) -> dict:
        key = _elo_cache_key(initial_elo, k_factor)
        cached = self._session_cache.get(key)
        if cached is not None:
            return cached

        elo_ratings: Dict[str, float] = defaultdict(lambda: initial_elo)
        sorted_sessions = sorted(self.sessions, key=lambda x: x.get('date', ''))
        deltas_out: List[tuple] = []
        evolution: List[Dict[str, Any]] = []

        first_session_with_players = None
        first_session_date_str = None
        for session in sorted_sessions:
            players = SessionDataManager.parse_session_data(session)
            if players and len(players) >= 2:
                first_session_with_players = session
                first_session_date_str = _session_date_str(session)
                break
        if first_session_with_players and first_session_date_str:
            day_before = _day_before(first_session_date_str)
            if day_before:
                first_players = sorted(
                    SessionDataManager.parse_session_data(first_session_with_players).keys()
                )
                evolution.append({
                    'date': day_before,
                    'formatted_date': self.format_date(day_before),
                    'elo_by_player': {p: initial_elo for p in first_players},
                })

        for session in sorted_sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players or len(players) < 2:
                continue

            new_players = [p for p in sorted(players) if p not in elo_ratings]
            if new_players and session is not first_session_with_players:
                day_before = _day_before(_session_date_str(session))
                if day_before:
                    pre_elo = dict(elo_ratings)
                    for player in new_players:
                        pre_elo[player] = initial_elo
                    evolution.append({
                        'date': day_before,
                        'formatted_date': self.format_date(day_before),
                        'elo_by_player': pre_elo,
                    })

            sorted_players = sorted(
                players.items(), key=lambda x: x[1]['today'], reverse=True
            )
            session_deltas = _pairwise_elo_deltas(
                elo_ratings, session_ranks_from_sorted(sorted_players), k_factor
            )
            _apply_elo_deltas(elo_ratings, session_deltas)
            deltas_out.append((session, session_deltas))

            date_str = _session_date_str(session)
            evolution.append({
                'date': date_str,
                'formatted_date': self.format_date(date_str),
                'elo_by_player': dict(elo_ratings),
            })

        evolution.sort(key=lambda x: x['date'])
        state = {
            'deltas': deltas_out,
            'ratings': dict(sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)),
            'evolution': evolution,
        }
        self._session_cache[key] = state
        return state

    def _match_elo_state(self, initial_elo=1500, k_factor=32) -> dict:
        key = _elo_cache_key(initial_elo, k_factor)
        cached = self._match_cache.get(key)
        if cached is not None:
            return cached

        players_order = _known_players(self.sessions)
        if not players_order:
            state = {'ratings': {}, 'daily': [], 'by_match': []}
            self._match_cache[key] = state
            return state

        elo_ratings: Dict[str, float] = defaultdict(lambda: initial_elo)
        sorted_sessions = sorted(self.sessions, key=lambda x: x.get('date', ''))
        by_date: Dict[str, Dict[str, float]] = {}
        by_match: List[Dict[str, Any]] = []
        match_num = 0
        matches_started = False

        session_evo = self._session_elo_state(initial_elo, k_factor)['evolution']
        if session_evo:
            baseline = session_evo[0]
            by_match.append({
                'date': baseline['date'],
                'formatted_date': baseline['formatted_date'],
                'match_index': 0,
                'is_chart_baseline': True,
                'elo_by_player': {
                    p: float(baseline['elo_by_player'].get(p, initial_elo))
                    for p in players_order
                },
            })

        for session in sorted_sessions:
            valid_matches = [
                m for m in SessionDataManager.parse_matchs_results(session)
                if len(m) >= 2
            ]
            d = _session_date_str(session)
            if not matches_started and not valid_matches:
                by_match.append({
                    'date': d,
                    'formatted_date': self.format_date(d),
                    'match_index': 0,
                    'session_id': session.get('id', ''),
                    'session_date': session.get('date', ''),
                    'session_label': self.format_date(d),
                    'is_prematch_flat': True,
                    'elo_by_player': {p: float(initial_elo) for p in players_order},
                })
                if d:
                    by_date[d] = {
                        p: float(elo_ratings.get(p, initial_elo)) for p in players_order
                    }
                continue

            for match in valid_matches:
                player_ranks = _ranks_from_kills(match)
                match_deltas = _pairwise_elo_deltas(elo_ratings, player_ranks, k_factor)
                _apply_elo_deltas(elo_ratings, match_deltas)
                matches_started = True
                match_num += 1
                label = f"{self.format_date(d, format_short=True)} · M{match_num}"
                by_match.append({
                    'date': d,
                    'formatted_date': label,
                    'match_index': match_num,
                    'session_id': session.get('id', ''),
                    'session_date': session.get('date', ''),
                    'session_label': self.format_date(d),
                    'elo_by_player': {
                        p: float(elo_ratings.get(p, initial_elo)) for p in players_order
                    },
                })
            if d:
                by_date[d] = {
                    p: float(elo_ratings.get(p, initial_elo)) for p in players_order
                }

        state = {
            'ratings': dict(sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)),
            'daily': [
                {
                    'date': date_key,
                    'formatted_date': self.format_date(date_key),
                    'elo_by_player': by_date[date_key],
                }
                for date_key in sorted(by_date.keys())
            ],
            'by_match': [] if match_num == 0 else by_match,
        }
        self._match_cache[key] = state
        return state

    def calculate_elo_ratings(self, initial_elo=1500, k_factor=32):
        """Session Elo: pairwise deltas from session ranks, applied as one batch per session."""
        return self._session_elo_state(initial_elo, k_factor)['ratings']

    def get_elo_session_deltas(self, initial_elo=1500, k_factor=32) -> List[tuple]:
        """Batch ELO delta per player for each session, in date order."""
        return self._session_elo_state(initial_elo, k_factor)['deltas']

    def get_elo_ranking(self, initial_elo=1500, k_factor=32):
        """Session Elo ranking as [(player, rating), ...] high first."""
        return list(self.calculate_elo_ratings(initial_elo, k_factor).items())

    def calculate_elo_match_ratings(self, initial_elo=1500, k_factor=32):
        """Match Elo: one pairwise batch per match, in global date then match order."""
        return self._match_elo_state(initial_elo, k_factor)['ratings']

    def get_elo_match_evolution(self, initial_elo=1500, k_factor=32) -> List[Dict[str, Any]]:
        """Match Elo snapshot at the end of each day."""
        return self._match_elo_state(initial_elo, k_factor)['daily']

    def get_elo_match_evolution_by_match(
        self, initial_elo: float = 1500, k_factor: float = 32
    ) -> List[Dict[str, Any]]:
        """Match Elo after every match, in global date then match order."""
        return self._match_elo_state(initial_elo, k_factor)['by_match']

    def write_elo_match_evolution_log(
        self,
        file_path: str,
        initial_elo: float = 1500,
        k_factor: float = 32,
    ) -> None:
        """Write end-of-day match Elo as a human-readable log (French column headers)."""
        points = self.get_elo_match_evolution(initial_elo, k_factor)
        lines: List[str] = [
            f"# Elo match (fin de journée)  initial={initial_elo!r}  K={k_factor!r}",
            f"# Colonnes: joueur -> Elo après toutes les sessions de la date.",
            '#',
        ]
        for p in points:
            lines.append(f"{p['date']}\t{p['formatted_date']}")
            for name in sorted(p['elo_by_player'].keys()):
                v = p['elo_by_player'][name]
                lines.append(f"  {name}\t{v:.4f}")
            lines.append('')
        content = '\n'.join(lines)
        if content and not content.endswith('\n'):
            content += '\n'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def get_elo_match_ranking(self, initial_elo=1500, k_factor=32):
        """Match Elo ranking for every player seen in parse_session_data (default 1500)."""
        ratings = self.calculate_elo_match_ratings(initial_elo, k_factor)
        all_players = _known_players(self.sessions)
        if not all_players:
            return []
        out = [(p, ratings.get(p, initial_elo)) for p in all_players]
        out.sort(key=lambda x: (-x[1], x[0]))
        return out

    def get_elo_evolution(self, initial_elo=1500, k_factor=32) -> List[Dict[str, Any]]:
        """ELO after each session for chart: list of {date, formatted_date, elo_by_player}."""
        return self._session_elo_state(initial_elo, k_factor)['evolution']
