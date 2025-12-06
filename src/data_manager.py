"""Gestion des données de sessions : récupération, parsing, filtrage et correction."""

import urllib.request
import csv
import io
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any

from .config import CSV_URL, COLOR_TO_PLAYER, PLAYER_TO_COLOR_KEY, V1_DATES_TO_IGNORE, COLOR_CONFIG


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
        """Filtre les sessions (minuit, v1, etc)."""
        if not self.sessions:
            return
        
        # Trier par date décroissante (plus récent en premier)
        sessions_sorted = sorted(self.sessions, key=lambda x: x['date'], reverse=True)
        
        sessions_to_keep = []
        
        # Parcourir les sessions et détecter les paires qui passent minuit
        for i, session in enumerate(sessions_sorted):
            # Vérifier si c'est une session v1
            is_v1 = session.get('data', {}).get('version') == 'v1'
            
            # Pour les sessions v1, ignorer uniquement les dates spécifiques
            if is_v1:
                date_str = SessionDataManager.extract_date_str(session['date'])
                if date_str in V1_DATES_TO_IGNORE:
                    continue
                sessions_to_keep.append(session)
                continue
            
            # Vérifier s'il y a une session le jour suivant avec le même ID
            date_obj, hour = SessionDataManager.parse_date_with_hour(session['date'])
            
            if date_obj is not None and hour is not None:
                # Format avec heure : chercher session entre 00h-05h le jour suivant
                next_day = date_obj + timedelta(days=1)
                found_next = False
                for j, other_session in enumerate(sessions_sorted):
                    if j >= i or other_session['id'] != session['id']:
                        continue
                    other_date_obj, other_hour = SessionDataManager.parse_date_with_hour(other_session['date'])
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
                            if 'version' in data and data['version'] == 'v1':
                                # Format v1 : trouver la couleur du joueur
                                color = PLAYER_TO_COLOR_KEY.get(player)
                                if color:
                                    today_key = f'{color}TodayWins'
                                    if today_key in data:
                                        data[today_key] = expected_today
                            elif 'todayWin' in data:
                                # Format v2 : corriger directement
                                if player in data['todayWin']:
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
    def should_ignore_player(player_name: str) -> bool:
        """Vérifie si un joueur doit être ignoré (AIJIMMY, P1, P2)."""
        if not player_name:
            return True
        player_upper = player_name.upper().replace(' ', '')
        # Ignorer AIJIMMY, P1, P2
        return 'AIJIMMY' in player_upper or player_upper in ['P1', 'P2']

    @staticmethod
    def parse_session_data(session: Dict[str, Any]) -> Dict[str, Any]:
        """Parse les données d'une session selon le format (v1 ou v2)."""
        data = session['data']
        
        if 'version' in data and data['version'] == 'v1':
            # Format ancien avec couleurs
            players = {}
            for color in COLOR_CONFIG.keys():
                today_key = f'{color}TodayWins'
                total_key = f'{color}TotalWins'
                if today_key in data and data[today_key] > 0:
                    player_name = COLOR_TO_PLAYER.get(color, color.capitalize())
                    if player_name and not SessionDataManager.should_ignore_player(player_name):
                        players[player_name] = {
                            'today': data[today_key],
                            'total': data.get(total_key, 0)
                        }
            return players
        elif 'todayWin' in data:
            # Format nouveau avec noms de joueurs
            players = {}
            for player, today_wins in data['todayWin'].items():
                if not SessionDataManager.should_ignore_player(player):
                    players[player] = {
                        'today': today_wins,
                        'total': data.get('totalWin', {}).get(player, 0)
                    }
            return players
        return {}

