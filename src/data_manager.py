"""Gestion des données de sessions : récupération, parsing, filtrage et correction."""

import urllib.request
import csv
import io
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any

from .config import CSV_URL


class SessionDataManager:
    """Gère la récupération, le parsing, le filtrage et la correction des sessions."""
    
    def __init__(self, csv_url=None, local_file=None):
        self.csv_url = csv_url or CSV_URL
        self.local_file = local_file
        self.sessions = []

    def fetch(self) -> None:
        """Télécharge et parse les données sources."""
        try:
            # Télécharge le CSV
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
                    # Recalculer l'ID à partir des joueurs présents dans la session
                    calculated_id = SessionDataManager.calculate_session_id_from_players(session)
                    if not calculated_id:
                        # Si aucun joueur valide, ignorer la session
                        continue
                    session['id'] = calculated_id
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
        
        # Trier par date décroissante (plus récent en premier)
        sessions_sorted = sorted(self.sessions, key=lambda x: x['date'], reverse=True)
        
        sessions_to_keep = []
        
        # Parcourir les sessions et détecter les paires qui passent minuit
        for i, session in enumerate(sessions_sorted):
            # Vérifier s'il y a une session le jour suivant avec le même ID
            # L'heure peut être dans data['date'] ou dans session['date']
            data = session.get('data', {})
            date_with_hour = data.get('date', session['date'])
            date_obj, hour = SessionDataManager.parse_date_with_hour(date_with_hour)
            
            if date_obj is not None and hour is not None:
                # Format avec heure : chercher session entre 00h-05h le jour suivant
                next_day = date_obj + timedelta(days=1)
                found_next = False
                for j, other_session in enumerate(sessions_sorted):
                    if j >= i or other_session['id'] != session['id']:
                        continue
                    other_data = other_session.get('data', {})
                    other_date_with_hour = other_data.get('date', other_session['date'])
                    other_date_obj, other_hour = SessionDataManager.parse_date_with_hour(other_date_with_hour)
                    if (other_date_obj and other_hour is not None and
                        other_date_obj.date() == next_day.date() and 0 <= other_hour <= 5):
                        found_next = True
                        break
                if found_next:
                    continue
            else:
                # Format sans heure : chercher session le jour suivant
                try:
                    current_date = datetime.strptime(session['date'], '%Y-%m-%d')
                    next_day_date = current_date + timedelta(days=1)
                    found_next = False
                    for j, other_session in enumerate(sessions_sorted):
                        if j >= i or other_session['id'] != session['id']:
                            continue
                        try:
                            other_date = datetime.strptime(other_session['date'], '%Y-%m-%d')
                            if other_date.date() == next_day_date.date():
                                found_next = True
                                break
                        except (ValueError, KeyError):
                            continue
                    if found_next:
                        continue
                except (ValueError, KeyError):
                    pass
            
            # Garder la session
            sessions_to_keep.append(session)
        
        self.sessions = sessions_to_keep

    def correct_sessions(self) -> None:
        """Corrige les incohérences dans les sessions (today/total)."""
        # Grouper les sessions par ID (groupe)
        sessions_by_group = defaultdict(list)
        for session in self.sessions:
            if session.get('id'):
                sessions_by_group[session['id']].append(session)
        
        # Pour chaque groupe, corriger les sessions
        for group_id, group_sessions in sessions_by_group.items():
            # Trier les sessions par date (croissante, de la plus ancienne à la plus récente)
            group_sessions.sort(key=lambda x: x['date'])
            
            # Dictionnaire pour stocker le total précédent de chaque joueur
            previous_totals = {}
            
            # Parcourir les sessions dans l'ordre chronologique
            for session in group_sessions:
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

    def load_all(self) -> None:
        """Charge toutes les données : fetch, filter, correct, et tri."""
        self.fetch()
        self.filter_sessions()
        self.correct_sessions()
        # Trier par date (plus récent en premier)
        self.sessions.sort(key=lambda x: x['date'], reverse=True)

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Renvoie la liste finale des sessions prêtes pour stats/affichage."""
        return self.sessions

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
        # Si la session contient un joueur à ignorer, on écarte toute la session
        all_player_names = SessionDataManager.extract_player_names(session)
        if any(SessionDataManager.should_ignore_player(name) for name in all_player_names):
            return ''

        players = SessionDataManager.parse_session_data(session)
        if not players:
            return ''
        
        # Filtrer les joueurs à ignorer et récupérer leurs noms
        player_names = [name for name in players.keys() if not SessionDataManager.should_ignore_player(name)]
        
        # Trier par ordre alphabétique
        player_names.sort()
        
        # Concaténer avec des tirets
        return '-'.join(player_names)

    @staticmethod
    def extract_player_names(session) -> List[str]:
        """Retourne tous les noms de joueurs présents, sans filtrage."""
        data = session.get('data', {})
        if 'todayWin' in data:
            return list(data['todayWin'].keys())
        return []

    @staticmethod
    def should_ignore_player(player_name: str) -> bool:
        """Vérifie si un joueur doit être ignoré (AIJIMMY, P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, etc.)."""
        if not player_name:
            return True
        player_upper = player_name.upper().replace(' ', '')
        # Ignorer AIJIMMY, P1, P2, P3, P4, P5, P6, P7, P8, P9, P10
        return 'AIJIMMY' in player_upper or player_upper in ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10']

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
        
        if 'todayWin' in data:
            for player, today_wins in data['todayWin'].items():
                if not SessionDataManager.should_ignore_player(player):
                    player_data = {
                        'today': today_wins,
                        'total': data.get('totalWin', {}).get(player, 0)
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

