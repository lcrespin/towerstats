"""Gestion des données de sessions : récupération, parsing, filtrage et correction."""

import urllib.request
import csv
import io
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any

from .config import CSV_URL, DEFAULT_GAME_MODE, normalize_game_mode


class SessionDataManager:
    """Gère la récupération, le parsing, le filtrage et la correction des sessions."""
    
    def __init__(self, csv_url=None, local_file=None):
        self.csv_url = csv_url or CSV_URL
        self.local_file = local_file
        self.sessions = []

    def fetch(self) -> None:
        """Télécharge et parse les données sources."""
        try:
            # Récupère le CSV depuis un fichier local ou depuis l'URL distante
            if self.local_file:
                with open(self.local_file, 'r', encoding='utf-8') as f:
                    csv_data = f.read()
            else:
                # Télécharge le CSV distant
                with urllib.request.urlopen(self.csv_url) as response:
                    csv_data = response.read().decode('utf-8')
            
            # Parse le CSV
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            sessions = []
            
            for row in csv_reader:
                if not row.get('value'):
                    continue
                
                try:
                    data = json.loads(row['value'])
                    session = {
                        'id': '',  # Sera recalculé plus tard
                        'date': row['date'],
                        'data': data
                    }
                    # Normaliser les joueurs pour s'assurer que tous sont dans todayWin/totalWin
                    SessionDataManager.normalize_session_players(session)
                    # Recalculer l'ID à partir des joueurs présents dans la session
                    calculated_id = SessionDataManager.calculate_session_id_from_players(session)
                    if not calculated_id:
                        # Si aucun joueur valide, ignorer la session
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
        """Filtre les sessions qui passent minuit."""
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
        """Corrige les incohérences dans les sessions (today/total)."""
        sessions_by_group = defaultdict(list)
        for session in self.sessions:
            if session.get('id'):
                sessions_by_group[SessionDataManager._session_group_mode_key(session)].append(session)
        
        for _group_mode_key, group_sessions in sessions_by_group.items():
            # Trier les sessions par date (croissante, de la plus ancienne à la plus récente)
            group_sessions.sort(key=lambda x: x['date'])
            
            # Dictionnaire pour stocker le total précédent de chaque joueur
            previous_totals = {}
            
            # Parcourir les sessions dans l'ordre chronologique
            for session in group_sessions:
                # Normaliser les joueurs pour s'assurer que tous sont dans todayWin/totalWin
                SessionDataManager.normalize_session_players(session)
                
                players = SessionDataManager.parse_session_data(session)
                data = session['data']
                
                # Pour chaque joueur de la session
                for player, stats in players.items():
                    current_total = stats['total']
                    current_today = stats['today']
                    
                    # Si on a un total précédent pour ce joueur
                    if player in previous_totals:
                        previous_total = previous_totals[player]
                        # Calculer la différence attendue
                        expected_today = current_total - previous_total
                        
                        # Si la différence ne correspond pas au today actuel
                        if expected_today != current_today and expected_today >= 0:
                            # Corriger le today dans les données
                            if 'todayWin' in data and player in data['todayWin']:
                                data['todayWin'][player] = expected_today
                    
                    # Mettre à jour le total précédent
                    previous_totals[player] = current_total

    def recompute_totals_from_today(self) -> None:
        """Recompute totalWin from cumulative sum of todayWin per group (fixes source inconsistencies)."""
        sessions_by_group = defaultdict(list)
        for session in self.sessions:
            if session.get('id'):
                sessions_by_group[SessionDataManager._session_group_mode_key(session)].append(session)
        for _group_mode_key, group_sessions in sessions_by_group.items():
            group_sessions.sort(key=lambda x: x['date'])
            cumulative = defaultdict(int)
            for session in group_sessions:
                SessionDataManager.normalize_session_players(session)
                data = session['data']
                if 'todayWin' not in data:
                    continue
                if 'totalWin' not in data:
                    data['totalWin'] = {}
                for player, today in data['todayWin'].items():
                    if SessionDataManager.should_ignore_player(player):
                        continue
                    cumulative[player] += today
                    data['totalWin'][player] = cumulative[player]

    def load_all(self) -> None:
        """Charge toutes les données : fetch, filter, correct, et tri."""
        self.fetch()
        self.filter_sessions()
        self.correct_sessions()
        self.recompute_totals_from_today()
        # Trier par date (plus récent en premier)
        self.sessions.sort(key=lambda x: x['date'], reverse=True)

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Renvoie la liste finale des sessions prêtes pour stats/affichage."""
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
    def filter_sessions_by_game_mode(
        sessions: List[Dict[str, Any]], game_mode: str
    ) -> List[Dict[str, Any]]:
        """Keep only sessions matching the given game mode."""
        mode = normalize_game_mode(game_mode)
        return [s for s in sessions if s.get('mode', DEFAULT_GAME_MODE) == mode]

    @staticmethod
    def game_modes_present(sessions: List[Dict[str, Any]]) -> List[str]:
        """Return configured game mode ids that appear in sessions (config order)."""
        from .config import GAME_MODES
        present = {s.get('mode', DEFAULT_GAME_MODE) for s in sessions}
        return [m for m in GAME_MODES if m in present]

    # ---- Static helpers (date, ID, etc) ----
    @staticmethod
    def extract_date_str(date_str: str) -> str:
        """Extrait la date au format YYYY-MM-DD depuis une chaîne de date."""
        return date_str[:10] if len(date_str) >= 10 else date_str

    @staticmethod
    def parse_date_with_hour(date_str: str):
        """Parse une date au format 'YYYY-MM-DD-HH' et retourne (date, heure).
        
        Args:
            date_str: Date au format 'YYYY-MM-DD-HH' (ex: '2025-11-27-23')
        
        Returns:
            tuple: (date_obj, heure) où date_obj est un objet datetime et heure est un int (0-23)
            Retourne (None, None) si le format est invalide
        """
        try:
            # Format attendu: 'YYYY-MM-DD-HH'
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
        """Calcule l'ID d'une session à partir des joueurs présents.
        
        Extrait les joueurs de la session, les filtre, les trie par ordre alphabétique
        et les concatène avec des tirets pour créer l'ID.
        
        Args:
            session: Dictionnaire de session avec 'data' contenant les données JSON
        
        Returns:
            str: ID de la session calculé (ex: 'DAVID-ERIC-LOUIS')
        """
        all_player_names = SessionDataManager.extract_player_names(session)
        if any(SessionDataManager.should_ignore_player(name) for name in all_player_names):
            return ''

        players = SessionDataManager.parse_session_data(session)
        if not players:
            return ''

        player_names = sorted(players.keys())
        
        # Concaténer avec des tirets
        return '-'.join(player_names)

    @staticmethod
    def extract_player_names(session) -> List[str]:
        """Retourne tous les noms de joueurs présents, sans filtrage."""
        data = session.get('data', {})
        player_names = set()
        # Ajouter les joueurs de todayWin
        if 'todayWin' in data:
            player_names.update(data['todayWin'].keys())
        # Ajouter aussi les joueurs de today (même ceux avec 0 victoires)
        if 'today' in data:
            player_names.update(data['today'].keys())
        return list(player_names)

    @staticmethod
    def should_ignore_player(player_name: str) -> bool:
        """Vérifie si un joueur doit être ignoré (AIJIMMY, P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, etc.)."""
        if not player_name:
            return True
        player_upper = player_name.upper().replace(' ', '')
        # Ignorer AIJIMMY, P1, P2, P3, P4, P5, P6, P7, P8, P9, P10
        return 'AIJIMMY' in player_upper or player_upper in ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10']

    @staticmethod
    def normalize_session_players(session: Dict[str, Any]) -> None:
        """Normalise les données d'une session pour s'assurer que tous les joueurs présents 
        dans today/total sont aussi dans todayWin/totalWin, même s'ils ont 0 victoires.
        
        Args:
            session: Dictionnaire de session avec 'data' contenant les données JSON
        """
        data = session.get('data', {})
        if 'today' not in data:
            return
        
        # Initialiser todayWin et totalWin si nécessaire
        if 'todayWin' not in data:
            data['todayWin'] = {}
        if 'totalWin' not in data:
            data['totalWin'] = {}
        
        # Pour chaque joueur présent dans today
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
            
            # Si le joueur n'est pas dans totalWin, récupérer depuis total ou mettre 0
            if player not in data['totalWin']:
                total_win = data.get('total', {}).get(player, {}).get('win', 0)
                data['totalWin'][player] = total_win

        # Nettoyer les stats détaillées (killBy/killFrom) des joueurs ignorés
        SessionDataManager._clean_detailed_stats_ignored_players(data)

    @staticmethod
    def _clean_detailed_stats_ignored_players(data: Dict[str, Any]) -> None:
        """Nettoie les stats détaillées en retirant les entrées concernant les joueurs ignorés
        dans les dictionnaires killBy / killFrom."""
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
                    filtered = {
                        name: count
                        for name, count in raw.items()
                        if not SessionDataManager.should_ignore_player(name)
                    }
                    player_stats[field] = filtered

    @staticmethod
    def has_detailed_stats(session: Dict[str, Any]) -> bool:
        """Vérifie si une session contient des statistiques détaillées.
        
        Args:
            session: Dictionnaire de session avec 'data' contenant les données JSON
        
        Returns:
            bool: True si la session contient des stats détaillées (today/total avec kill, death, etc.)
        """
        data = session.get('data', {})
        return 'today' in data and 'total' in data
    
    @staticmethod
    def parse_session_data(session: Dict[str, Any]) -> Dict[str, Any]:
        """Parse les données d'une session.
        
        Retourne les données de base (today/total wins) et les stats détaillées si disponibles.
        """
        data = session['data']
        players = {}
        has_detailed = SessionDataManager.has_detailed_stats(session)
        
        # Collecter tous les joueurs : ceux de todayWin et ceux de today (même avec 0 victoires)
        all_players = set()
        if 'todayWin' in data:
            all_players.update(data['todayWin'].keys())
        if 'today' in data:
            all_players.update(data['today'].keys())
        
        for player in all_players:
            if not SessionDataManager.should_ignore_player(player):
                # Récupérer today_wins depuis todayWin, ou 0 si absent
                today_wins = data.get('todayWin', {}).get(player, 0)
                # Récupérer total_wins depuis totalWin, ou depuis total.win si absent
                total_wins = data.get('totalWin', {}).get(player, 
                    data.get('total', {}).get(player, {}).get('win', 0))
                
                player_data = {
                    'today': today_wins,
                    'total': total_wins
                }
                
                # Ajouter les stats détaillées si disponibles
                if has_detailed:
                    today_stats = data.get('today', {}).get(player, {})
                    total_stats = data.get('total', {}).get(player, {})
                    
                    if today_stats or total_stats:
                        player_data['detailed'] = {
                            'kill': total_stats.get('kill', 0),
                            'death': total_stats.get('death', 0),
                            'self': total_stats.get('self', 0),
                            'killFrom': total_stats.get('killFrom', {}),
                            'killBy': total_stats.get('killBy', {})
                        }
                
                players[player] = player_data
        
        return players

    @staticmethod
    def parse_matchs_results(session: Dict[str, Any]) -> List[Dict[str, int]]:
        """Extrait et valide `data['matchsResults']` pour une session.

        Schéma attendu :
            ``data['matchsResults']`` : liste d'objets ; chaque élément est un match,
            dictionnaire **joueur → nombre de kills** (entier >= 0).
            L'ordre de la liste est l'ordre chronologique des matchs.

        Les joueurs listés par `should_ignore_player` sont exclus. Les kills
        négatifs ou non numériques sont ignorés. Les matchs qui n'ont pas au
        moins 2 joueurs valides restants peuvent être ignorés par l'appelant.

        Returns:
            Liste de dictionnaires ``{joueur: kills}`` (un par match, dans l'ordre),
            chaque dict ne contenant que des joueurs valides et des kills >= 0.
        """
        data = session.get('data') or {}
        raw = data.get('matchsResults')
        if not raw or not isinstance(raw, list):
            return []
        out: List[Dict[str, int]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            match: Dict[str, int] = {}
            for name, value in entry.items():
                if SessionDataManager.should_ignore_player(name):
                    continue
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)):
                    k = int(value)
                    if k < 0:
                        continue
                    match[name] = k
            out.append(match)
        return out

