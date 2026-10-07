"""Fetch, parse, and correct session CSV rows."""

import urllib.request
import csv
import io
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any

from .config import CSV_URL, DEFAULT_GAME_MODE, canonical_player_name, normalize_game_mode

CSV_CACHE_SECONDS = 60
_CSV_CACHE: Dict[str, tuple] = {}


def _download_csv(url: str) -> str:
    """Remote CSV text, reused for CSV_CACHE_SECONDS so live polling does not hit Google on every request."""
    cached = _CSV_CACHE.get(url)
    if cached and time.monotonic() - cached[0] < CSV_CACHE_SECONDS:
        return cached[1]
    with urllib.request.urlopen(url) as response:
        text = response.read().decode('utf-8')
    _CSV_CACHE[url] = (time.monotonic(), text)
    return text


class SessionDataManager:
    """Load sessions from the sheet CSV and apply midnight / today-total fixes."""
    
    def __init__(self, csv_url=None, local_file=None):
        self.csv_url = csv_url or CSV_URL
        self.local_file = local_file
        self.sessions = []

    def fetch(self) -> None:
        """Download the source CSV and parse JSON rows into sessions."""
        try:
            if self.local_file:
                with open(self.local_file, 'r', encoding='utf-8') as f:
                    csv_data = f.read()
            else:
                csv_data = _download_csv(self.csv_url)

            csv_reader = csv.DictReader(io.StringIO(csv_data))
            sessions = []

            for row in csv_reader:
                if not row.get('value'):
                    continue

                try:
                    data = json.loads(row['value'])
                    session = {
                        'id': '',
                        'date': row['date'],
                        'data': data
                    }
                    SessionDataManager.normalize_session_players(session)
                    calculated_id = SessionDataManager.calculate_session_id_from_players(session)
                    if not calculated_id:
                        continue
                    session['id'] = calculated_id
                    session['mode'] = normalize_game_mode(data.get('mode'))
                    sessions.append(session)
                except json.JSONDecodeError:
                    continue
            
            self.sessions = sessions
        except Exception as e:
            raise Exception(f"Erreur lors de la récupération des données: {e}")

    def filter_sessions(self) -> None:
        """Drop the pre-midnight half of a session that continues after 00:00."""
        if not self.sessions:
            return

        sessions_sorted = sorted(self.sessions, key=lambda x: x['date'], reverse=True)
        sessions_to_keep = []

        for i, session in enumerate(sessions_sorted):
            data = session.get('data', {})
            date_with_hour = data.get('date', session['date'])
            date_obj, hour = SessionDataManager.parse_date_with_hour(date_with_hour)

            if date_obj is not None and hour is not None:
                next_day = date_obj + timedelta(days=1)
                def is_next_day_early_hours(other):
                    other_data = other.get('data', {})
                    other_date_with_hour = other_data.get('date', other['date'])
                    other_date_obj, other_hour = SessionDataManager.parse_date_with_hour(other_date_with_hour)
                    return (other_date_obj and other_hour is not None and
                            other_date_obj.date() == next_day.date() and 0 <= other_hour <= 5)
                if SessionDataManager._has_matching_next_day_session(sessions_sorted, i, session, is_next_day_early_hours):
                    continue
            else:
                try:
                    current_date = datetime.strptime(session['date'], '%Y-%m-%d')
                    next_day_date = current_date + timedelta(days=1)
                    def is_next_day_date(other):
                        try:
                            other_date = datetime.strptime(other['date'], '%Y-%m-%d')
                            return other_date.date() == next_day_date.date()
                        except (ValueError, KeyError):
                            return False
                    if SessionDataManager._has_matching_next_day_session(sessions_sorted, i, session, is_next_day_date):
                        continue
                except (ValueError, KeyError):
                    pass

            sessions_to_keep.append(session)

        self.sessions = sessions_to_keep

    @staticmethod
    def _session_group_mode_key(session: Dict[str, Any]) -> tuple:
        """Grouping key for corrections and midnight dedup: (group_id, game_mode)."""
        return (session.get('id', ''), session.get('mode', DEFAULT_GAME_MODE))

    @staticmethod
    def _has_matching_next_day_session(sessions_sorted, i, session, is_next_day_fn) -> bool:
        """True if a session with same group+mode exists at a later index and is_next_day_fn(other) is True."""
        session_key = SessionDataManager._session_group_mode_key(session)
        for j, other in enumerate(sessions_sorted):
            if j >= i or SessionDataManager._session_group_mode_key(other) != session_key:
                continue
            if is_next_day_fn(other):
                return True
        return False

    def correct_sessions(self) -> None:
        """Rewrite todayWin when it does not match the jump in totalWin (skip real resets)."""
        sessions_by_group = defaultdict(list)
        for session in self.sessions:
            if session.get('id'):
                sessions_by_group[SessionDataManager._session_group_mode_key(session)].append(session)

        for _group_mode_key, group_sessions in sessions_by_group.items():
            group_sessions.sort(key=lambda x: x['date'])
            previous_totals = {}
            kinds = SessionDataManager._cumulative_row_kinds(group_sessions)

            for session, kind in zip(group_sessions, kinds):
                if kind == 'partial':
                    continue
                players = SessionDataManager.parse_session_data(session)
                data = session['data']

                for player, stats in players.items():
                    current_total = stats['total']
                    current_today = stats['today']

                    if player in previous_totals and kind != 'reset':
                        previous_total = previous_totals[player]
                        expected_today = current_total - previous_total
                        if expected_today != current_today and expected_today >= 0:
                            if 'todayWin' in data and player in data['todayWin']:
                                data['todayWin'][player] = expected_today

                    previous_totals[player] = current_total

    @staticmethod
    def _cumulative_row_kinds(group_sessions: List[Dict[str, Any]]) -> List[str]:
        """Classify each chronological row of a group by its source totalWin: normal, reset or partial.

        When totals drop below the source cumulative, the row is a real reset if the next row
        builds on it (or there is no next row); otherwise it is a partial export to ignore.
        """
        for session in group_sessions:
            SessionDataManager.normalize_session_players(session)
        parsed = [SessionDataManager.parse_session_data(s) for s in group_sessions]
        kinds: List[str] = []
        source_totals: Dict[str, int] = {}
        for index, players in enumerate(parsed):
            dropped = any(
                stats['total'] < source_totals[player]
                for player, stats in players.items()
                if player in source_totals
            )
            kind = 'normal'
            if dropped:
                next_players = parsed[index + 1] if index + 1 < len(parsed) else None
                builds_on = not next_players or all(
                    player in players
                    and stats['total'] - stats['today'] == players[player]['total']
                    for player, stats in next_players.items()
                )
                kind = 'reset' if builds_on else 'partial'
            kinds.append(kind)
            if kind != 'partial':
                source_totals.update({p: s['total'] for p, s in players.items()})
        return kinds

    def recompute_totals_from_today(self) -> None:
        """Recompute totalWin from cumulative sum of todayWin per group (fixes source inconsistencies)."""
        sessions_by_group = defaultdict(list)
        for session in self.sessions:
            if session.get('id'):
                sessions_by_group[SessionDataManager._session_group_mode_key(session)].append(session)
        for _group_mode_key, group_sessions in sessions_by_group.items():
            group_sessions.sort(key=lambda x: x['date'])
            cumulative = defaultdict(int)
            kinds = SessionDataManager._cumulative_row_kinds(group_sessions)
            for session, kind in zip(group_sessions, kinds):
                data = session['data']
                if 'todayWin' not in data:
                    continue
                players = SessionDataManager.parse_session_data(session)
                if kind == 'partial':
                    if 'totalWin' not in data:
                        data['totalWin'] = {}
                    for player in players:
                        if SessionDataManager.should_ignore_player(player):
                            continue
                        data['totalWin'][player] = cumulative.get(player, 0)
                    continue
                if 'totalWin' not in data:
                    data['totalWin'] = {}
                for player, today in data['todayWin'].items():
                    if SessionDataManager.should_ignore_player(player):
                        continue
                    cumulative[player] += today
                    data['totalWin'][player] = cumulative[player]

    def load_all(self) -> None:
        """Fetch, midnight-filter, correct today/total, then sort newest first."""
        self.fetch()
        self.filter_sessions()
        self.correct_sessions()
        self.recompute_totals_from_today()
        self.sessions.sort(key=lambda x: x['date'], reverse=True)

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Sessions after load_all (newest first)."""
        return self.sessions

    @staticmethod
    def sorted_group_ids_by_session_count(sessions: List[Dict[str, Any]]) -> List[str]:
        """Return group ids sorted by number of sessions (descending)."""
        count: Dict[str, int] = defaultdict(int)
        for s in sessions:
            gid = s.get('id')
            if gid:
                count[gid] += 1
        return sorted(count.keys(), key=lambda g: -count[g])

    @staticmethod
    def format_session_select_id(session: Dict[str, Any]) -> str:
        """URL/form value for a single session: date|group_id|mode."""
        return f"{session.get('date', '')}|{session.get('id', '')}|{session.get('mode', DEFAULT_GAME_MODE)}"

    @staticmethod
    def filter_sessions_by_session_id(
        sessions: List[Dict[str, Any]], session_id: str | None
    ) -> List[Dict[str, Any]]:
        """Filter sessions by session_id (format 'date|id|mode' or legacy 'date|id')."""
        if not session_id or not session_id.strip():
            return sessions
        parts = [p.strip() for p in session_id.split('|')]
        if len(parts) == 3:
            date_str, sid, mode = parts
            if not date_str or not sid:
                return sessions
            mode = normalize_game_mode(mode)
            return [
                s for s in sessions
                if s.get('date') == date_str
                and s.get('id') == sid
                and s.get('mode', DEFAULT_GAME_MODE) == mode
            ]
        if len(parts) == 2:
            date_str, sid = parts
            if not date_str or not sid:
                return sessions
            return [s for s in sessions if s.get('date') == date_str and s.get('id') == sid]
        return sessions

    @staticmethod
    def filter_sessions_by_group_id(
        sessions: List[Dict[str, Any]], group_id: str | None
    ) -> List[Dict[str, Any]]:
        """Keep only sessions whose group id equals group_id."""
        if not group_id or not group_id.strip():
            return sessions
        return [s for s in sessions if s.get('id') == group_id]

    @staticmethod
    def filter_sessions_by_game_mode(
        sessions: List[Dict[str, Any]], game_mode: str
    ) -> List[Dict[str, Any]]:
        """Keep only sessions matching the given game mode."""
        mode = normalize_game_mode(game_mode)
        return [s for s in sessions if s.get('mode', DEFAULT_GAME_MODE) == mode]

    @staticmethod
    def filter_sessions_by_date(
        sessions: List[Dict[str, Any]],
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Keep sessions whose YYYY-MM-DD date falls in the inclusive window."""
        if not date_start and not date_end:
            return sessions
        filtered: List[Dict[str, Any]] = []
        for session in sessions:
            date_str = SessionDataManager.extract_date_str(str(session.get('date', '')))
            if not date_str:
                continue
            if date_start and date_str < date_start:
                continue
            if date_end and date_str > date_end:
                continue
            filtered.append(session)
        return filtered

    @staticmethod
    def extract_date_str(date_str: str) -> str:
        """YYYY-MM-DD prefix of a session date (source dates may include an hour)."""
        return date_str[:10] if len(date_str) >= 10 else date_str

    @staticmethod
    def parse_date_with_hour(date_str: str):
        """Parse 'YYYY-MM-DD-HH' into (datetime, hour); (None, None) if invalid."""
        try:
            parts = date_str.split('-')
            if len(parts) >= 4:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                hour = int(parts[3])
                date_obj = datetime(year, month, day)
                return date_obj, hour
        except (ValueError, IndexError):
            pass
        return None, None

    @staticmethod
    def calculate_session_id_from_players(session):
        """Sorted declared-player names joined by dashes, or '' if any name is unknown."""
        all_player_names = SessionDataManager.extract_player_names(session)
        if any(SessionDataManager.should_ignore_player(name) for name in all_player_names):
            return ''

        players = SessionDataManager.parse_session_data(session)
        if not players:
            return ''

        player_names = sorted(players.keys())
        return '-'.join(player_names)

    @staticmethod
    def extract_player_names(session) -> List[str]:
        """Raw names from todayWin and today, including 0-win players not listed in todayWin."""
        data = session.get('data', {})
        player_names = set()
        if 'todayWin' in data:
            player_names.update(data['todayWin'].keys())
        if 'today' in data:
            player_names.update(data['today'].keys())
        return list(player_names)

    @staticmethod
    def should_ignore_player(player_name: str) -> bool:
        """True when the name is not a declared player in PLAYER_TO_COLOR."""
        return canonical_player_name(player_name) is None

    @staticmethod
    def _is_kill_source(name: str) -> bool:
        """Kill sources (Arrow, Lava, JumpedOn) are not player names."""
        letters = ''.join(ch for ch in name if ch.isalpha())
        return bool(letters) and not letters.isupper()

    @staticmethod
    def _filter_kill_counts(raw, keep_sources: bool) -> Dict[str, Any]:
        """Keep declared players, and kill sources when keep_sources is set."""
        if not isinstance(raw, dict):
            return {}
        filtered: Dict[str, Any] = {}
        for name, count in raw.items():
            if not isinstance(name, str):
                continue
            canonical = canonical_player_name(name)
            if canonical is not None:
                key = canonical
            elif keep_sources and SessionDataManager._is_kill_source(name):
                key = name
            else:
                continue
            if (
                key in filtered
                and isinstance(filtered[key], (int, float))
                and isinstance(count, (int, float))
                and not isinstance(count, bool)
            ):
                filtered[key] += count
            else:
                filtered[key] = count
        return filtered

    @staticmethod
    def _rename_player_mapping(mapping: Dict[str, Any], nested_stats: bool) -> Dict[str, Any]:
        """Rename declared players to their canonical id. Unknown names stay, so the session can be dropped."""
        renamed: Dict[str, Any] = {}
        for name, value in mapping.items():
            canonical = canonical_player_name(name) if isinstance(name, str) else None
            key = canonical if canonical is not None else name
            if nested_stats and isinstance(value, dict):
                value = dict(value)
                for field in ('killBy', 'killFrom'):
                    if isinstance(value.get(field), dict):
                        value[field] = SessionDataManager._filter_kill_counts(
                            value[field], keep_sources=(field == 'killFrom')
                        )
            if (
                key in renamed
                and isinstance(renamed[key], (int, float))
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                renamed[key] += value
            elif key not in renamed:
                renamed[key] = value
        return renamed

    @staticmethod
    def _canonicalize_declared_player_keys(data: Dict[str, Any]) -> None:
        """Rewrite declared player keys (ALEXANDRE -> ALEX) inside a session payload."""
        if not isinstance(data, dict):
            return
        for key in ('todayWin', 'totalWin', 'today', 'total'):
            block = data.get(key)
            if isinstance(block, dict):
                data[key] = SessionDataManager._rename_player_mapping(
                    block, nested_stats=(key in ('today', 'total'))
                )
        matches = data.get('matchsResults')
        if isinstance(matches, list):
            data['matchsResults'] = [
                SessionDataManager._rename_player_mapping(entry, nested_stats=False)
                if isinstance(entry, dict) else entry
                for entry in matches
            ]

    @staticmethod
    def normalize_session_players(session: Dict[str, Any]) -> None:
        """Ensure every player in today/total also appears in todayWin/totalWin, even at 0 wins."""
        data = session.get('data', {})
        SessionDataManager._canonicalize_declared_player_keys(data)
        if 'today' not in data:
            return

        if 'todayWin' not in data:
            data['todayWin'] = {}
        if 'totalWin' not in data:
            data['totalWin'] = {}

        for player in data['today'].keys():
            if SessionDataManager.should_ignore_player(player):
                continue

            if player not in data['todayWin']:
                today_val = data['today'].get(player)
                if isinstance(today_val, dict):
                    today_wins = today_val.get('win', 0)
                elif isinstance(today_val, (int, float)):
                    today_wins = int(today_val)
                else:
                    today_wins = 0
                data['todayWin'][player] = today_wins

            if player not in data['totalWin']:
                total_win = data.get('total', {}).get(player, {}).get('win', 0)
                data['totalWin'][player] = total_win

        SessionDataManager._clean_detailed_stats_ignored_players(data)

    @staticmethod
    def _clean_detailed_stats_ignored_players(data: Dict[str, Any]) -> None:
        """Drop undeclared players from killBy/killFrom nested maps."""
        for key in ('today', 'total'):
            stats_by_player = data.get(key, {})
            if not isinstance(stats_by_player, dict):
                continue

            for player_stats in stats_by_player.values():
                if not isinstance(player_stats, dict):
                    continue

                for field in ('killBy', 'killFrom'):
                    raw = player_stats.get(field)
                    if not isinstance(raw, dict):
                        continue
                    player_stats[field] = SessionDataManager._filter_kill_counts(
                        raw, keep_sources=(field == 'killFrom')
                    )

    @staticmethod
    def has_detailed_stats(session: Dict[str, Any]) -> bool:
        """True when the row has combat blocks (`today` and `total`)."""
        data = session.get('data', {})
        return 'today' in data and 'total' in data

    @staticmethod
    def parse_session_data(session: Dict[str, Any]) -> Dict[str, Any]:
        """Per-player today/total wins, plus this session's combat stats when present."""
        data = session['data']
        players = {}
        has_detailed = SessionDataManager.has_detailed_stats(session)

        all_players = set()
        if 'todayWin' in data:
            all_players.update(data['todayWin'].keys())
        if 'today' in data:
            all_players.update(data['today'].keys())

        for player in all_players:
            canonical = canonical_player_name(player)
            if canonical is None:
                continue
            today_wins = data.get('todayWin', {}).get(player, 0)
            total_wins = data.get('totalWin', {}).get(player,
                data.get('total', {}).get(player, {}).get('win', 0))

            player_data = {
                'today': today_wins,
                'total': total_wins
            }

            # Detailed `total` is cumulative per group in the source; only `today` is per session.
            if has_detailed:
                today_stats = data.get('today', {}).get(player, {})

                if isinstance(today_stats, dict) and today_stats:
                    player_data['detailed'] = {
                        'kill': today_stats.get('kill', 0),
                        'death': today_stats.get('death', 0),
                        'self': today_stats.get('self', 0),
                        'killFrom': SessionDataManager._filter_kill_counts(
                            today_stats.get('killFrom', {}), keep_sources=True
                        ),
                        'killBy': SessionDataManager._filter_kill_counts(
                            today_stats.get('killBy', {}), keep_sources=False
                        ),
                    }

            if canonical in players:
                players[canonical]['today'] += player_data['today']
                players[canonical]['total'] += player_data['total']
            else:
                players[canonical] = player_data

        return players

    @staticmethod
    def parse_matchs_results(session: Dict[str, Any]) -> List[Dict[str, int]]:
        """This session's matches as [{player: kills}, ...] in chronological order.

        The sheet prepends earlier sessions of the same group; keep only the last N
        entries, where N is the session win count. Undeclared players and negative
        kills are dropped.
        """
        data = session.get('data') or {}
        raw = data.get('matchsResults')
        if not raw or not isinstance(raw, list):
            return []
        session_wins = sum(
            stats['today'] for stats in SessionDataManager.parse_session_data(session).values()
        )
        if session_wins < len(raw):
            raw = raw[len(raw) - session_wins:]
        out: List[Dict[str, int]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            match: Dict[str, int] = {}
            for name, value in entry.items():
                canonical = canonical_player_name(name)
                if canonical is None:
                    continue
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)):
                    k = int(value)
                    if k < 0:
                        continue
                    match[canonical] = match.get(canonical, 0) + k
            out.append(match)
        return out

