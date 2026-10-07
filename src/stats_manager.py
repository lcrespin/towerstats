"""Aggregate stats and Elo from a filtered session list."""

from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

from .data_manager import SessionDataManager
from .config import PLAYER_TO_COLOR, game_mode_label, DEFAULT_GAME_MODE
from .combat_profiles import build_combat_profiles, build_evening_curve
from .elo import EloEngine, session_ranks_from_sorted
from .session_records import build_session_records
from .session_details import build_session_details

MEDAL_BY_RANK = {1: '🥇', 2: '🥈', 3: '🥉'}


def _player_rank_map(ranking: List[Any], name_index: int = 1, rank_index: int = 0) -> Dict[str, int]:
    """Map player name -> dense rank from a ranked table."""
    return {row[name_index]: row[rank_index] for row in ranking or []}


def _career_delta_label(season_rank: int, career_rank: int | None) -> str | None:
    if career_rank is None:
        return None
    if career_rank == season_rank:
        return 'même rang'
    return f'All-time : {career_rank}e'


def _best_group_score_ranking(rankings_by_group: Dict[str, List[Any]]) -> List[tuple]:
    """Dense ranking of players by their best per-group win total."""
    best_by_player: Dict[str, int] = {}
    for ranking in (rankings_by_group or {}).values():
        for row in ranking:
            player = row[1]
            total = row[2]
            if total > best_by_player.get(player, -1):
                best_by_player[player] = total
    raw = list(best_by_player.items())
    return SessionStatsManager._add_dense_ranks(raw, score_index=1, name_index=0)


def leaderboard_career_deltas(season_data: Dict[str, Any], career_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Ghost career ranks for leaderboard cards (player -> label)."""
    deltas: Dict[str, Dict[str, str]] = {
        'win_pct': {},
        'elo': {},
        'elo_match': {},
        'group_score': {},
    }
    career_win = _player_rank_map(career_data.get('win_percentage_ranking') or [])
    career_elo = _player_rank_map(career_data.get('elo_ranking') or [])
    career_elo_match = _player_rank_map(career_data.get('elo_match_ranking') or [])
    career_score = _player_rank_map(_best_group_score_ranking(career_data.get('rankings_by_group') or {}))

    for player in season_data.get('best_percentage_players') or []:
        label = _career_delta_label(1, career_win.get(player))
        if label:
            deltas['win_pct'][player] = label
    for player in season_data.get('best_elo_players') or []:
        label = _career_delta_label(1, career_elo.get(player))
        if label:
            deltas['elo'][player] = label
    for player in season_data.get('best_elo_match_players') or []:
        label = _career_delta_label(1, career_elo_match.get(player))
        if label:
            deltas['elo_match'][player] = label
    for player in season_data.get('best_players') or []:
        label = _career_delta_label(1, career_score.get(player))
        if label:
            deltas['group_score'][player] = label
    return deltas


class SessionStatsManager:
    """Rankings, Elo, and template payloads for a filtered session window."""

    def __init__(
        self,
        sessions: List[Dict[str, Any]],
        date_start: str | None = None,
        date_end: str | None = None,
    ):
        """Optionally restrict sessions to an inclusive YYYY-MM-DD window."""
        self.sessions = SessionDataManager.filter_sessions_by_date(
            sessions, date_start, date_end
        )
        self._elo = EloEngine(self.sessions, self.format_date)

    def _session_date_str(self, session: Dict[str, Any]) -> str:
        """Normalised YYYY-MM-DD date string for a session."""
        return SessionDataManager.extract_date_str(str(session.get('date', '')))

    def _window_running_totals(self) -> Dict[int, Dict[str, int]]:
        """Cumulative today-wins per player within the current session window, per group+mode."""
        running: Dict[int, Dict[str, int]] = {}
        sessions_by_group: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
        for session in self.sessions:
            sessions_by_group[SessionDataManager._session_group_mode_key(session)].append(session)
        for group_sessions in sessions_by_group.values():
            group_sessions.sort(key=lambda s: s.get('date', ''))
            totals: Dict[str, int] = defaultdict(int)
            for session in group_sessions:
                players = SessionDataManager.parse_session_data(session)
                for player, stats in players.items():
                    totals[player] += stats.get('today', 0)
                running[id(session)] = dict(totals)
        return running

    def _ranked_session_players(self, session, window_totals):
        """(rank, player, stats) for one session, with season totals in stats['total']."""
        players = SessionDataManager.parse_session_data(session)
        if not players:
            return None
        season_totals = window_totals.get(id(session), {})
        ranked_players = {
            player: {**stats, 'total': season_totals.get(player, stats.get('today', 0))}
            for player, stats in players.items()
        }
        sorted_players = sorted(ranked_players.items(), key=lambda x: (-x[1]['today'], x[0]))
        ranks = session_ranks_from_sorted(sorted_players)
        return [(ranks[p], p, s) for p, s in sorted_players]

    def _session_entry(self, session, players_list):
        mode = session.get('mode', DEFAULT_GAME_MODE)
        return {
            'id': session['id'],
            'group': session['id'],
            'date': session['date'],
            'formatted_date': self.format_date(self._session_date_str(session)),
            'game_mode': mode,
            'game_mode_label': game_mode_label(mode),
            'session_select_id': SessionDataManager.format_session_select_id(session),
            'players': [
                {'rank': r, 'name': p, 'today': s['today'], 'total': s['total']}
                for r, p, s in players_list
            ],
            'details': build_session_details(session),
        }

    def build_session_entry(self, session, window_totals=None):
        """JSON card for one session, as shown in the archives; None when it has no players."""
        if window_totals is None:
            window_totals = self._window_running_totals()
        players_list = self._ranked_session_players(session, window_totals)
        if not players_list:
            return None
        return self._session_entry(session, players_list)

    @staticmethod
    def _add_dense_ranks(items, score_index, name_index=0):
        """Sort by score desc then name asc; assign dense rank. Returns list of (rank, *item)."""
        if not items:
            return []
        sorted_items = sorted(
            items,
            key=lambda x: (-x[score_index] if isinstance(x[score_index], (int, float)) else 0, x[name_index])
        )
        result = []
        current_rank = 0
        prev_score = None
        for i, row in enumerate(sorted_items):
            s = row[score_index]
            if prev_score is None or s != prev_score:
                current_rank = i + 1
            result.append((current_rank,) + row)
            prev_score = s
        return result

    def get_unique_groups(self):
        """Distinct group ids (already canonicalized to declared players only)."""
        groups = set()
        for session in self.sessions:
            if session.get('id'):
                groups.add(session['id'])
        return sorted(list(groups))

    def get_global_ranking(self, group_id=None):
        """Sum of session today-wins per player (recomputed under date filters)."""
        player_totals = defaultdict(int)

        for session in self.sessions:
            if group_id and session['id'] != group_id:
                continue
            players = SessionDataManager.parse_session_data(session)
            for player, stats in players.items():
                player_totals[player] += stats['today']

        ranking = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)
        return ranking

    def group_sessions_by_date(self):
        """Sessions keyed by YYYY-MM-DD, newest date first."""
        sessions_by_date = defaultdict(list)
        for session in self.sessions:
            date_str = self._session_date_str(session)
            sessions_by_date[date_str].append(session)
        sorted_dates = sorted(sessions_by_date.keys(), reverse=True)
        return {date: sessions_by_date[date] for date in sorted_dates}

    def format_date(self, date_str, format_short=False):
        """French display date (dd/mm/yyyy, or dd/mm/yy when short)."""
        try:
            if len(date_str) >= 10:
                date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
                if format_short:
                    return date_obj.strftime('%d/%m/%y')
                return date_obj.strftime('%d/%m/%Y')
        except:
            pass
        return date_str

    def get_win_percentage_ranking(self):
        """Win %: wins = sum of today; games = session size for every session the player was in."""
        player_victories = defaultdict(int)
        player_games_played = defaultdict(int)

        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players:
                continue

            total_games_in_session = sum(stats['today'] for stats in players.values())

            for player, stats in players.items():
                player_victories[player] += stats['today']
                player_games_played[player] += total_games_in_session

        player_stats = []
        for player in player_victories.keys():
            victories = player_victories[player]
            games_played = player_games_played[player]

            if games_played > 0:
                win_percentage = (victories / games_played) * 100
            else:
                win_percentage = 0.0

            player_stats.append((player, victories, games_played, win_percentage))

        return sorted(player_stats, key=lambda x: x[3], reverse=True)

    def get_medal(self, rank):
        """Medal emoji for ranks 1–3, else ''."""
        return MEDAL_BY_RANK.get(rank, '')

    def calculate_elo_ratings(self, initial_elo=1500, k_factor=32):
        """Session Elo: pairwise deltas from session ranks, applied as one batch per session."""
        return self._elo.calculate_elo_ratings(initial_elo, k_factor)

    def get_elo_session_deltas(self, initial_elo=1500, k_factor=32) -> List[tuple]:
        """Batch ELO delta per player for each session, in date order: [(session, {player: delta})]."""
        return self._elo.get_elo_session_deltas(initial_elo, k_factor)

    def get_elo_ranking(self, initial_elo=1500, k_factor=32):
        """Session Elo ranking as [(player, rating), ...] high first."""
        return self._elo.get_elo_ranking(initial_elo, k_factor)

    def calculate_elo_match_ratings(self, initial_elo=1500, k_factor=32):
        """Match Elo: one pairwise batch per match, in global date then match order.

        Ranks come from that match's kills only; same pairing rule as session Elo.
        """
        return self._elo.calculate_elo_match_ratings(initial_elo, k_factor)

    def get_elo_match_evolution(self, initial_elo=1500, k_factor=32) -> List[Dict[str, Any]]:
        """Match Elo snapshot at the end of each day."""
        return self._elo.get_elo_match_evolution(initial_elo, k_factor)

    def get_elo_match_evolution_by_match(
        self, initial_elo: float = 1500, k_factor: float = 32
    ) -> List[Dict[str, Any]]:
        """Match Elo after every match, in global date then match order."""
        return self._elo.get_elo_match_evolution_by_match(initial_elo, k_factor)

    def write_elo_match_evolution_log(
        self,
        file_path: str,
        initial_elo: float = 1500,
        k_factor: float = 32,
    ) -> None:
        """Write end-of-day match Elo as a human-readable log (French column headers)."""
        self._elo.write_elo_match_evolution_log(file_path, initial_elo, k_factor)

    def get_elo_match_ranking(self, initial_elo=1500, k_factor=32):
        """Match Elo ranking for every player seen in parse_session_data (default 1500)."""
        return self._elo.get_elo_match_ranking(initial_elo, k_factor)

    def get_elo_evolution(self, initial_elo=1500, k_factor=32) -> List[Dict[str, Any]]:
        """Returns ELO after each session for chart: list of {date, formatted_date, elo_by_player}."""
        return self._elo.get_elo_evolution(initial_elo, k_factor)

    def get_win_rate_evolution(self) -> List[Dict[str, Any]]:
        """Returns win rate (cumulative wins/games) after each session for chart."""
        cumulative_wins = defaultdict(int)
        cumulative_games = defaultdict(int)
        sorted_sessions = sorted(self.sessions, key=lambda x: x.get('date', ''))
        evolution = []

        for session in sorted_sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players:
                continue
            total_games = sum(stats['today'] for stats in players.values())
            if total_games <= 0:
                continue
            for player, stats in players.items():
                cumulative_wins[player] += stats['today']
                cumulative_games[player] += total_games

            win_rate_by_player = {}
            for player in cumulative_games:
                g = cumulative_games[player]
                win_rate_by_player[player] = cumulative_wins[player] / g if g else 0.0

            date_str = self._session_date_str(session)
            evolution.append({
                'date': date_str,
                'formatted_date': self.format_date(date_str),
                'win_rate_by_player': win_rate_by_player,
            })

        return evolution

    def has_detailed_stats(self) -> bool:
        """True if any session in the window has combat stats."""
        for session in self.sessions:
            if SessionDataManager.has_detailed_stats(session):
                return True
        return False

    def _get_player_games_played(self, detailed_only: bool = False) -> Dict[str, int]:
        """Total games played per player (sum of session games where player participated).

        For each session counted:
        - total_games_in_session = sum of 'today' (wins) over all players in that session
          (= number of rounds/games in the session, since each game has one winner).
        - That same number is added to each player present in the session.

        If detailed_only=True, only sessions with combat/detailed stats are counted.
        So "Parties" in the table = sum of (games in session) for every session that
        has detailed stats and where the player participated.
        """
        player_games = defaultdict(int)
        for session in self.sessions:
            if detailed_only and not SessionDataManager.has_detailed_stats(session):
                continue
            players = SessionDataManager.parse_session_data(session)
            if not players:
                continue
            total_games_in_session = sum(stats['today'] for stats in players.values())
            for player in players:
                player_games[player] += total_games_in_session
        return dict(player_games)

    def _get_kill_death_totals_in_detailed_sessions_only(self):
        """Kills/deaths/self_kills summed over sessions that have detailed stats.

        Same sessions as "Parties", so numerator and denominator refer to the same period.
        """
        player_kills = defaultdict(int)
        player_deaths = defaultdict(int)
        player_self_kills = defaultdict(int)
        for session in self.sessions:
            if not SessionDataManager.has_detailed_stats(session):
                continue
            players = SessionDataManager.parse_session_data(session)
            for player, stats in players.items():
                if 'detailed' not in stats:
                    continue
                d = stats['detailed']
                player_kills[player] += d.get('kill', 0)
                player_deaths[player] += d.get('death', 0)
                player_self_kills[player] += d.get('self', 0)
        return player_kills, player_deaths, player_self_kills

    def get_kill_death_stats(self):
        """Kills/deaths/self and per-game rates, counted only on sessions that have combat stats."""
        player_kills, player_deaths, player_self_kills = self._get_kill_death_totals_in_detailed_sessions_only()
        player_games = self._get_player_games_played(detailed_only=True)
        player_stats = []
        for player in player_kills.keys():
            kills = player_kills[player]
            deaths = player_deaths[player]
            self_kills = player_self_kills[player]
            games = player_games.get(player, 0) or 1
            kills_per_game = kills / games
            deaths_per_game = deaths / games
            self_per_game = self_kills / games
            if deaths > 0:
                kd_ratio = kills / deaths
            else:
                kd_ratio = kills if kills > 0 else 0.0
            player_stats.append((
                player, kills, deaths, self_kills, kd_ratio,
                player_games.get(player, 0), kills_per_game, deaths_per_game, self_per_game
            ))
        return sorted(player_stats, key=lambda x: x[4], reverse=True)
    
    def get_kill_relationships(self):
        """Who-kills-whom matrix: per-game averages and totals per (killer, victim) pair."""
        total_kills = defaultdict(lambda: defaultdict(int))
        total_games = defaultdict(lambda: defaultdict(int))

        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players:
                continue
            total_games_in_session = sum(stats['today'] for stats in players.values())
            for player, stats in players.items():
                if 'detailed' in stats:
                    kill_by = stats['detailed'].get('killBy', {})
                    for killer, count in kill_by.items():
                        total_kills[killer][player] += count
                    for killer in set(players) | set(kill_by):
                        total_games[killer][player] += total_games_in_session

        relationships_avg = defaultdict(dict)
        relationships_totals = defaultdict(dict)
        for killer in total_kills:
            for victim in total_kills[killer]:
                kills = total_kills[killer][victim]
                games = total_games[killer][victim]
                relationships_totals[killer][victim] = kills
                relationships_avg[killer][victim] = (kills / games) if games > 0 else 0.0

        return dict(relationships_avg), dict(relationships_totals)

    @staticmethod
    def _ranking_leaders(ranking, value_index, empty_value=0):
        if not ranking:
            return [], empty_value
        best = ranking[0][value_index]
        return [row[1] for row in ranking if row[value_index] == best], best

    def session_entries(self, window_totals=None) -> List[Dict[str, Any]]:
        """Archive cards for every session in the current window."""
        if window_totals is None:
            window_totals = self._window_running_totals()
        entries: List[Dict[str, Any]] = []
        for date_sessions in self.group_sessions_by_date().values():
            for session in date_sessions:
                entry = self.build_session_entry(session, window_totals)
                if entry:
                    entries.append(entry)
        return entries

    def leaderboard_rankings(self) -> Dict[str, Any]:
        """Win %, Elo, and group-score tables used by the homepage and career deltas."""
        unique_groups = self.get_unique_groups()
        rankings_by_group = {
            group_id: self._add_dense_ranks(
                self.get_global_ranking(group_id), score_index=1, name_index=0
            )
            for group_id in unique_groups
        }
        all_player_totals: Dict[str, int] = defaultdict(int)
        for ranking in rankings_by_group.values():
            for _rank, player, total in ranking:
                if total > all_player_totals[player]:
                    all_player_totals[player] = total
        best_players: List[str] = []
        best_score = 0
        if all_player_totals:
            best_score = max(all_player_totals.values())
            best_players = [p for p, total in all_player_totals.items() if total == best_score]

        win_percentage_ranking = self._add_dense_ranks(
            self.get_win_percentage_ranking(), score_index=3, name_index=0
        )
        best_percentage_players, best_percentage = self._ranking_leaders(
            win_percentage_ranking, 4, empty_value=0.0
        )

        try:
            elo_raw = self.get_elo_ranking()
            elo_ranking = self._add_dense_ranks(
                list(elo_raw) if elo_raw else [], score_index=1, name_index=0
            )
        except Exception:
            elo_ranking = []
        best_elo_players, best_elo = self._ranking_leaders(elo_ranking, 2, empty_value=0.0)

        try:
            elo_match_list = self.get_elo_match_ranking() or []
            elo_match_ranking = self._add_dense_ranks(
                list(elo_match_list), score_index=1, name_index=0
            )
            elo_match_by_player = dict(elo_match_list)
        except Exception:
            elo_match_ranking = []
            elo_match_by_player = {}
        best_elo_match_players, best_elo_match = self._ranking_leaders(
            elo_match_ranking, 2, empty_value=0.0
        )

        return {
            'unique_groups': unique_groups,
            'rankings_by_group': rankings_by_group,
            'best_players': best_players,
            'best_score': best_score,
            'win_percentage_ranking': win_percentage_ranking,
            'best_percentage_players': best_percentage_players,
            'best_percentage': best_percentage,
            'elo_ranking': elo_ranking,
            'best_elo_players': best_elo_players,
            'best_elo': best_elo,
            'elo_match_ranking': elo_match_ranking,
            'elo_match_by_player': elo_match_by_player,
            'best_elo_match': best_elo_match,
            'best_elo_match_players': best_elo_match_players,
        }

    def prepare_template_data(self):
        """Full homepage template dict."""
        boards = self.leaderboard_rankings()
        unique_groups = boards['unique_groups']
        rankings_by_group = boards['rankings_by_group']
        sessions_by_date = self.group_sessions_by_date()
        latest_date = list(sessions_by_date.keys())[0] if sessions_by_date else None
        latest_sessions = sessions_by_date[latest_date] if latest_date else []

        sorted_groups = SessionDataManager.sorted_group_ids_by_session_count(self.sessions)
        default_group = sorted_groups[0] if sorted_groups else None
        default_ranking = rankings_by_group.get(default_group, []) if default_group else []

        date_debut = min(sessions_by_date.keys()) if sessions_by_date else None
        date_fin = max(sessions_by_date.keys()) if sessions_by_date else None
        date_debut_formatted = self.format_date(date_debut, format_short=True) if date_debut else "N/A"
        date_fin_formatted = self.format_date(date_fin, format_short=True) if date_fin else "N/A"

        dates_with_detailed = [
            self._session_date_str(s) for s in self.sessions
            if SessionDataManager.has_detailed_stats(s) and self._session_date_str(s)
        ]
        date_debut_detailed = min(dates_with_detailed) if dates_with_detailed else None
        date_debut_detailed_formatted = self.format_date(date_debut_detailed, format_short=True) if date_debut_detailed else "N/A"

        total_sessions = len(self.sessions)
        total_games = 0
        unique_players = set()
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            unique_players.update(players.keys())
            total_games += sum(stats['today'] for stats in players.values())

        try:
            elo_evolution = self.get_elo_evolution()
        except Exception:
            elo_evolution = []
        try:
            elo_match_evolution = self.get_elo_match_evolution_by_match()
        except Exception:
            elo_match_evolution = []
        try:
            win_rate_evolution = self.get_win_rate_evolution()
        except Exception:
            win_rate_evolution = []

        window_totals = self._window_running_totals()
        latest_sessions_parsed = []
        for session in latest_sessions:
            players_list = self._ranked_session_players(session, window_totals)
            if players_list:
                latest_sessions_parsed.append({'session': session, 'players': players_list})
        latest_sessions_data = [
            self._session_entry(entry['session'], entry['players'])
            for entry in latest_sessions_parsed
        ]
        all_sessions_data = self.session_entries(window_totals)

        has_detailed = self.has_detailed_stats()
        kill_death_ranking = []
        combat_profiles = []
        kill_relationships = {}
        all_players_for_matrix = []
        top_killers = []
        top_deaths = []
        top_self_kills = []
        least_deaths_row = None
        least_self_kills_row = None
        best_kd_ratio = []
        best_kd_value = 0.0
        kills_per_game_ranking = []
        best_kills_players = []
        best_kills_value = 0.0
        max_kills_in_matrix = 1
        max_kills_in_matrix_totals = 1
        kill_relationships_totals = {}

        if has_detailed:
            kill_death_ranking = self._add_dense_ranks(
                self.get_kill_death_stats(), score_index=4, name_index=0
            )
            combat_profiles = build_combat_profiles(self.sessions, format_date=self.format_date)
            kill_relationships, kill_relationships_totals = self.get_kill_relationships()

            all_players_set = set()
            for row in kill_death_ranking:
                all_players_set.add(row[1])
            for killer in kill_relationships.keys():
                all_players_set.add(killer)
                for victim in kill_relationships[killer].keys():
                    all_players_set.add(victim)
            all_players_for_matrix = sorted(list(all_players_set))

            max_kills_in_matrix_totals = 1
            for killer, victims in kill_relationships.items():
                for victim, count in victims.items():
                    if count > max_kills_in_matrix:
                        max_kills_in_matrix = count
            for killer, victims in kill_relationships_totals.items():
                for victim, count in victims.items():
                    if count > max_kills_in_matrix_totals:
                        max_kills_in_matrix_totals = count

            if kill_death_ranking:
                top_killers = sorted(kill_death_ranking, key=lambda x: x[7], reverse=True)[:5]
                by_deaths = sorted(kill_death_ranking, key=lambda x: x[8], reverse=True)
                top_deaths = by_deaths[:5]
                least_deaths_row = by_deaths[-1]
                by_self = sorted(kill_death_ranking, key=lambda x: x[9], reverse=True)
                top_self_kills = [(r[1], r[4], r[9]) for r in by_self[:5]]
                least_self_kills_row = by_self[-1]
                best_kd_value = kill_death_ranking[0][5]
                best_kd_ratio = [row[1] for row in kill_death_ranking if row[5] == best_kd_value]
                kills_per_game_ranking = self._add_dense_ranks(
                    [(row[1], row[7], row[6]) for row in kill_death_ranking],
                    score_index=1, name_index=0,
                )
                best_kills_value = kills_per_game_ranking[0][2]
                best_kills_players = [
                    row[1] for row in kills_per_game_ranking if row[2] == best_kills_value
                ]

        try:
            elo_session_deltas = self.get_elo_session_deltas()
        except Exception:
            elo_session_deltas = []
        session_records = build_session_records(
            self.sessions, elo_session_deltas, format_date=self.format_date
        )
        
        return {
            'unique_groups': unique_groups,
            'sorted_groups': sorted_groups,
            'default_group': default_group,
            'rankings_by_group': rankings_by_group,
            'default_ranking': default_ranking,
            'date_debut': date_debut_formatted,
            'date_fin': date_fin_formatted,
            'date_debut_raw': date_debut,
            'date_fin_raw': date_fin,
            'date_debut_detailed': date_debut_detailed_formatted,
            'date_debut_detailed_raw': date_debut_detailed,
            'total_sessions': total_sessions,
            'unique_players_count': len(unique_players),
            'best_players': boards['best_players'],
            'best_score': boards['best_score'],
            'best_percentage_players': boards['best_percentage_players'],
            'best_percentage': boards['best_percentage'],
            'win_percentage_ranking': boards['win_percentage_ranking'],
            'elo_ranking': boards['elo_ranking'],
            'elo_evolution': elo_evolution,
            'elo_match_evolution': elo_match_evolution,
            'win_rate_evolution': win_rate_evolution,
            'best_elo_players': boards['best_elo_players'],
            'best_elo': boards['best_elo'],
            'elo_match_ranking': boards['elo_match_ranking'],
            'elo_match_by_player': boards['elo_match_by_player'],
            'best_elo_match': boards['best_elo_match'],
            'best_elo_match_players': boards['best_elo_match_players'],
            'latest_date': latest_date,
            'latest_sessions_parsed': latest_sessions_parsed,
            'latest_sessions_data': latest_sessions_data,
            'sessions_by_date': sessions_by_date,
            'all_sessions_data': all_sessions_data,
            'player_colors': PLAYER_TO_COLOR,
            'has_detailed_stats': has_detailed,
            'kill_death_ranking': kill_death_ranking,
            'combat_profiles': combat_profiles,
            'evening_curve': build_evening_curve(self.sessions),
            'kill_relationships': kill_relationships,
            'kill_relationships_totals': kill_relationships_totals,
            'all_players_for_matrix': all_players_for_matrix,
            'max_kills_in_matrix': max_kills_in_matrix,
            'max_kills_in_matrix_totals': max_kills_in_matrix_totals,
            'top_killers': top_killers,
            'top_deaths': top_deaths,
            'top_self_kills': top_self_kills,
            'least_deaths_row': least_deaths_row,
            'least_self_kills_row': least_self_kills_row,
            'best_kd_ratio': best_kd_ratio,
            'best_kd_value': best_kd_value,
            'kills_per_game_ranking': kills_per_game_ranking,
            'best_kills_players': best_kills_players,
            'best_kills_value': best_kills_value,
            'total_games': total_games,
            'session_records': session_records,
        }

