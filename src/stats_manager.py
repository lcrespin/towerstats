"""Gestion des statistiques et calculs à partir des sessions filtrées."""

import os
import json
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

from .data_manager import SessionDataManager
from .config import PLAYER_TO_COLOR, get_player_color


class SessionStatsManager:
    """Effectue tous les calculs d'agrégat/statistiques à partir d'une liste de sessions filtrées."""
    
    def __init__(self, sessions: List[Dict[str, Any]]):
        self.sessions = sessions

    def get_unique_groups(self):
        """Récupère tous les groupes de joueurs uniques (basés sur l'ID de session).
        
        Les IDs sont déjà recalculés et ne contiennent que des joueurs valides,
        donc on peut simplement collecter tous les IDs uniques.
        """
        groups = set()
        for session in self.sessions:
            if session.get('id'):
                groups.add(session['id'])
        return sorted(list(groups))

    def get_global_ranking(self, group_id=None):
        """Calcule le classement global pour un groupe spécifique.
        
        Utilise stats['total'] (le maximum parmi toutes les sessions du groupe)
        pour obtenir le meilleur score dans ce groupe spécifique.
        """
        player_totals = defaultdict(int)
        
        for session in self.sessions:
            # Filtrer par groupe si spécifié
            if group_id and session['id'] != group_id:
                continue
            
            players = SessionDataManager.parse_session_data(session)
            for player, stats in players.items():
                # Prendre le total le plus élevé (stats['total']) pour chaque joueur
                if stats['total'] > player_totals[player]:
                    player_totals[player] = stats['total']
        
        # Trier par total décroissant
        ranking = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)
        return ranking

    def group_sessions_by_date(self):
        """Groupe les sessions par date (soirée)."""
        sessions_by_date = defaultdict(list)
        
        for session in self.sessions:
            # Extraire la date (sans l'heure)
            date_str = session['date'].split(' ')[0] if ' ' in session['date'] else session['date'][:10]
            sessions_by_date[date_str].append(session)
        
        # Trier les dates (plus récent en premier)
        sorted_dates = sorted(sessions_by_date.keys(), reverse=True)
        return {date: sessions_by_date[date] for date in sorted_dates}

    def format_date(self, date_str, format_short=False):
        """Formate une date pour l'affichage."""
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
        """Calcule le classement par pourcentage de victoires.
        
        Le nombre total de Victoires est le cumul de stats['today'] pour chaque session
        où le joueur a participé (depuis le début).
        
        Le nombre total de Parties est le cumul du total de parties (stats['today'] de tous
        les joueurs) pour chaque session de chaque groupe auquel le joueur a participé.
        
        Returns:
            list: Liste de tuples (joueur, victoires, parties_jouees, pourcentage) triée par pourcentage décroissant
        """
        player_victories = defaultdict(int)
        player_games_played = defaultdict(int)
        
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players:
                continue
            
            # Calculer le nombre total de parties dans cette session
            total_games_in_session = sum(stats['today'] for stats in players.values())
            
            # Pour chaque joueur de la session
            for player, stats in players.items():
                # Cumuler les victoires (stats['today']) pour chaque session
                player_victories[player] += stats['today']
                
                # Cumuler les parties jouées (total de la session pour chaque session où le joueur était présent)
                player_games_played[player] += total_games_in_session
        
        # Calculer les pourcentages
        player_stats = []
        for player in player_victories.keys():
            victories = player_victories[player]
            games_played = player_games_played[player]
            
            if games_played > 0:
                win_percentage = (victories / games_played) * 100
            else:
                win_percentage = 0.0
            
            player_stats.append((player, victories, games_played, win_percentage))
        
        # Trier par pourcentage décroissant
        return sorted(player_stats, key=lambda x: x[3], reverse=True)

    def get_medal(self, rank):
        """Retourne la médaille correspondant au rang."""
        if rank == 1:
            return '🥇'
        elif rank == 2:
            return '🥈'
        elif rank == 3:
            return '🥉'
        return ''

    def calculate_elo_ratings(self, initial_elo=1500, k_factor=32):
        """Calcule les ratings ELO pour chaque joueur basés sur toutes les sessions.
        
        Le système ELO calcule un score pour chaque joueur basé sur leurs performances
        dans les sessions. Chaque session est traitée comme une série de matchups entre
        tous les joueurs présents, où le classement est déterminé par le score 'today'.
        
        Args:
            initial_elo: Score ELO initial pour les nouveaux joueurs (défaut: 1500)
            k_factor: Facteur K qui détermine la vitesse de changement (défaut: 32)
                     Plus K est élevé, plus les changements sont rapides.
        
        Returns:
            dict: Dictionnaire {joueur: rating_elo} trié par rating décroissant
        """
        # Initialiser les ratings ELO pour tous les joueurs
        elo_ratings = defaultdict(lambda: initial_elo)
        
        # Trier les sessions par date (plus ancien en premier pour calculer chronologiquement)
        sorted_sessions = sorted(self.sessions, key=lambda x: x.get('date', ''))
        
        for session in sorted_sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players or len(players) < 2:
                continue
            
            # Filtrer les joueurs valides et obtenir leurs scores
            valid_players = {
                name: stats for name, stats in players.items()
                if not SessionDataManager.should_ignore_player(name)
            }
            
            if len(valid_players) < 2:
                continue
            
            # Trier les joueurs par score 'today' (décroissant)
            # Le meilleur score = gagnant de la session
            sorted_players = sorted(
                valid_players.items(),
                key=lambda x: x[1]['today'],
                reverse=True
            )
            
            # Créer un classement pour chaque joueur dans cette session
            # (1 = premier, 2 = deuxième, etc.)
            player_ranks = {}
            for rank, (player, stats) in enumerate(sorted_players, start=1):
                player_ranks[player] = rank
            
            # Calculer les matchups entre tous les joueurs de la session
            # Pour chaque paire de joueurs, calculer le résultat du matchup
            player_names = list(valid_players.keys())
            
            for i, player_a in enumerate(player_names):
                for player_b in player_names[i + 1:]:
                    rank_a = player_ranks[player_a]
                    rank_b = player_ranks[player_b]
                    
                    # Calculer le score attendu pour le joueur A
                    elo_a = elo_ratings[player_a]
                    elo_b = elo_ratings[player_b]
                    
                    # Score attendu (probabilité de gagner)
                    expected_score_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
                    
                    # Score réel basé sur le classement
                    # Si A est mieux classé que B, A gagne (score = 1)
                    # Si égalité, score = 0.5
                    # Sinon, A perd (score = 0)
                    if rank_a < rank_b:
                        actual_score_a = 1.0  # A gagne
                    elif rank_a == rank_b:
                        actual_score_a = 0.5  # Égalité
                    else:
                        actual_score_a = 0.0  # A perd
                    
                    # Mettre à jour les ratings ELO
                    elo_change = k_factor * (actual_score_a - expected_score_a)
                    elo_ratings[player_a] += elo_change
                    elo_ratings[player_b] -= elo_change  # Changement opposé pour B
        
        # Trier par rating décroissant
        sorted_elo = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_elo)

    def get_elo_ranking(self, initial_elo=1500, k_factor=32):
        """Retourne le classement ELO des joueurs.
        
        Args:
            initial_elo: Score ELO initial (défaut: 1500)
            k_factor: Facteur K (défaut: 32)
        
        Returns:
            list: Liste de tuples (joueur, rating_elo) triée par rating décroissant
        """
        elo_ratings = self.calculate_elo_ratings(initial_elo, k_factor)
        return list(elo_ratings.items())
    
    def has_detailed_stats(self) -> bool:
        """Vérifie si au moins une session contient des statistiques détaillées."""
        for session in self.sessions:
            if SessionDataManager.has_detailed_stats(session):
                return True
        return False
    
    def get_kill_death_stats(self):
        """Calcule les statistiques de kills et deaths par joueur.
        
        Returns:
            list: Liste de tuples (joueur, kills, deaths, self_kills, kd_ratio) triée par ratio K/D décroissant
        """
        player_kills = defaultdict(int)
        player_deaths = defaultdict(int)
        player_self_kills = defaultdict(int)
        
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            for player, stats in players.items():
                if 'detailed' in stats:
                    detailed = stats['detailed']
                    player_kills[player] = max(player_kills[player], detailed.get('kill', 0))
                    player_deaths[player] = max(player_deaths[player], detailed.get('death', 0))
                    player_self_kills[player] = max(player_self_kills[player], detailed.get('self', 0))
        
        # Calculer les ratios K/D
        player_stats = []
        for player in player_kills.keys():
            kills = player_kills[player]
            deaths = player_deaths[player]
            self_kills = player_self_kills[player]
            
            if deaths > 0:
                kd_ratio = kills / deaths
            else:
                kd_ratio = kills if kills > 0 else 0.0
            
            player_stats.append((player, kills, deaths, self_kills, kd_ratio))
        
        # Trier par ratio K/D décroissant
        return sorted(player_stats, key=lambda x: x[4], reverse=True)
    
    def get_kill_sources_stats(self):
        """Agrège les sources de kills (Arrow, Explosion, etc.) par joueur et globalement.
        
        Returns:
            dict: {
                'by_player': {player: {source: count}},
                'global': {source: total_count}
            }
        """
        by_player = defaultdict(lambda: defaultdict(int))
        global_sources = defaultdict(int)
        
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            for player, stats in players.items():
                if 'detailed' in stats:
                    kill_from = stats['detailed'].get('killFrom', {})
                    for source, count in kill_from.items():
                        by_player[player][source] = max(by_player[player][source], count)
                        global_sources[source] = max(global_sources[source], count)
        
        return {
            'by_player': dict(by_player),
            'global': dict(global_sources)
        }
    
    def get_kill_relationships(self):
        """Crée une matrice montrant qui tue qui (killBy agrégé).
        
        Returns:
            dict: {killer: {victim: count}} - Matrice des kills entre joueurs
        """
        relationships = defaultdict(lambda: defaultdict(int))
        
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            for player, stats in players.items():
                if 'detailed' in stats:
                    kill_by = stats['detailed'].get('killBy', {})
                    for killer, count in kill_by.items():
                        if not SessionDataManager.should_ignore_player(killer):
                            relationships[killer][player] = max(relationships[killer][player], count)
        
        return dict(relationships)
    
    def get_self_kill_stats(self):
        """Calcule les statistiques sur les auto-éliminations.
        
        Returns:
            list: Liste de tuples (joueur, self_kills) triée par nombre décroissant
        """
        player_self_kills = defaultdict(int)
        
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            for player, stats in players.items():
                if 'detailed' in stats:
                    self_kills = stats['detailed'].get('self', 0)
                    player_self_kills[player] = max(player_self_kills[player], self_kills)
        
        return sorted(player_self_kills.items(), key=lambda x: x[1], reverse=True)
    
    def get_detailed_player_stats(self, player_name: str):
        """Retourne les statistiques complètes pour un joueur spécifique.
        
        Args:
            player_name: Nom du joueur
        
        Returns:
            dict: Statistiques détaillées du joueur ou None si non trouvé
        """
        player_kills = 0
        player_deaths = 0
        player_self_kills = 0
        kill_from = defaultdict(int)
        kill_by = defaultdict(int)
        
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            if player_name in players:
                stats = players[player_name]
                if 'detailed' in stats:
                    detailed = stats['detailed']
                    player_kills = max(player_kills, detailed.get('kill', 0))
                    player_deaths = max(player_deaths, detailed.get('death', 0))
                    player_self_kills = max(player_self_kills, detailed.get('self', 0))
                    
                    for source, count in detailed.get('killFrom', {}).items():
                        kill_from[source] = max(kill_from[source], count)
                    
                    for killer, count in detailed.get('killBy', {}).items():
                        if not SessionDataManager.should_ignore_player(killer):
                            kill_by[killer] = max(kill_by[killer], count)
        
        if player_kills == 0 and player_deaths == 0:
            return None
        
        kd_ratio = player_kills / player_deaths if player_deaths > 0 else (player_kills if player_kills > 0 else 0.0)
        
        return {
            'player': player_name,
            'kills': player_kills,
            'deaths': player_deaths,
            'self_kills': player_self_kills,
            'kd_ratio': kd_ratio,
            'killFrom': dict(kill_from),
            'killBy': dict(kill_by)
        }

    def prepare_template_data(self):
        """Prépare toutes les données nécessaires pour le template HTML."""
        # Calculer les données
        unique_groups = self.get_unique_groups()
        sessions_by_date = self.group_sessions_by_date()
        latest_date = list(sessions_by_date.keys())[0] if sessions_by_date else None
        latest_sessions = sessions_by_date[latest_date] if latest_date else []
        
        # Calculer les classements pour chaque groupe
        rankings_by_group = {}
        for group_id in unique_groups:
            rankings_by_group[group_id] = self.get_global_ranking(group_id)
        
        # Trier les groupes par le meilleur score du groupe (décroissant)
        sorted_groups = sorted(
            unique_groups, 
            key=lambda g: rankings_by_group.get(g, [])[0][1] if rankings_by_group.get(g) else 0,
            reverse=True
        )
        
        # Classement par défaut (groupe avec le meilleur score)
        default_group = sorted_groups[0] if sorted_groups else None
        default_ranking = rankings_by_group.get(default_group, []) if default_group else []
        
        # Calculer les dates de début et de fin
        from .data_manager import SessionDataManager
        all_dates = [
            SessionDataManager.extract_date_str(session['date']) 
            for session in self.sessions 
            if session.get('date')
        ]
        date_debut = min(all_dates) if all_dates else None
        date_fin = max(all_dates) if all_dates else None
        date_debut_formatted = self.format_date(date_debut, format_short=True) if date_debut else "N/A"
        date_fin_formatted = self.format_date(date_fin, format_short=True) if date_fin else "N/A"
        
        # Statistiques supplémentaires
        total_sessions = len(self.sessions)
        unique_players = set()
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            filtered_players = {p: v for p, v in players.items() if not SessionDataManager.should_ignore_player(p)}
            unique_players.update(filtered_players.keys())
        
        # Meilleur joueur (parmi tous les groupes)
        all_player_totals = defaultdict(int)
        for ranking in rankings_by_group.values():
            for player, total in ranking:
                if total > all_player_totals[player]:
                    all_player_totals[player] = total
        
        best_players = []
        best_score = 0
        if all_player_totals:
            best_score = max(all_player_totals.values())
            best_players = [p for p, total in all_player_totals.items() if total == best_score]
        
        # Meilleur pourcentage de victoires
        win_percentage_ranking = self.get_win_percentage_ranking()
        best_percentage_players = []
        best_percentage = 0.0
        if win_percentage_ranking:
            _, _, _, top_percentage = win_percentage_ranking[0]
            best_percentage = top_percentage
            best_percentage_players = [
                player for player, _, _, pct in win_percentage_ranking if pct == top_percentage
            ]
        
        # Classement ELO
        try:
            elo_ranking = self.get_elo_ranking()
            # S'assurer que elo_ranking est une liste
            if not isinstance(elo_ranking, list):
                elo_ranking = list(elo_ranking) if elo_ranking else []
        except Exception as e:
            # En cas d'erreur, retourner une liste vide
            elo_ranking = []
        
        # Meilleur ELO
        best_elo_players = []
        best_elo = 0.0
        if elo_ranking:
            best_elo = elo_ranking[0][1]
            best_elo_players = [player for player, rating in elo_ranking if rating == best_elo]
        
        # Préparer les sessions latest avec leurs joueurs parsés
        latest_sessions_parsed = []
        for session in latest_sessions:
            players = SessionDataManager.parse_session_data(session)
            if players:
                sorted_players = sorted(players.items(), key=lambda x: x[1]['today'], reverse=True)
                latest_sessions_parsed.append({
                    'session': session,
                    'players': sorted_players
                })
        
        # Préparer toutes les sessions pour JavaScript
        all_sessions_data = []
        for date, date_sessions in sessions_by_date.items():
            for session in date_sessions:
                players = SessionDataManager.parse_session_data(session)
                if players:
                    sorted_players = sorted(players.items(), key=lambda x: x[1]['today'], reverse=True)
                    all_sessions_data.append({
                        'id': session['id'],
                        'group': session['id'],
                        'date': session['date'],
                        'formatted_date': self.format_date(date),
                        'players': [{'name': p, 'today': s['today'], 'total': s['total']} for p, s in sorted_players]
                    })
        
        # Statistiques détaillées (si disponibles)
        has_detailed = self.has_detailed_stats()
        kill_death_ranking = []
        kill_sources_aggregated = {'by_player': {}, 'global': {}}
        kill_relationships = {}
        all_players_for_matrix = []
        top_killers = []
        top_deaths = []
        top_self_kills = []
        best_kd_ratio = []
        best_kd_value = 0.0
        
        if has_detailed:
            kill_death_ranking = self.get_kill_death_stats()
            kill_sources_aggregated = self.get_kill_sources_stats()
            kill_relationships = self.get_kill_relationships()
            self_kill_stats = self.get_self_kill_stats()
            
            # Collecter tous les joueurs uniques pour la matrice (tueurs + victimes)
            all_players_set = set()
            for player, _, _, _, _ in kill_death_ranking:
                all_players_set.add(player)
            for killer in kill_relationships.keys():
                all_players_set.add(killer)
                for victim in kill_relationships[killer].keys():
                    all_players_set.add(victim)
            all_players_for_matrix = sorted(list(all_players_set))
            
            # Calculer le maximum de kills pour la normalisation de la matrice
            max_kills_in_matrix = 1  # Minimum 1 pour éviter division par zéro
            for killer, victims in kill_relationships.items():
                for victim, count in victims.items():
                    if count > max_kills_in_matrix:
                        max_kills_in_matrix = count
            
            # Top killers (par kills totaux)
            if kill_death_ranking:
                top_killers = sorted(kill_death_ranking, key=lambda x: x[1], reverse=True)[:5]
                top_deaths = sorted(kill_death_ranking, key=lambda x: x[2], reverse=True)[:5]
                top_self_kills = self_kill_stats[:5] if self_kill_stats else []
                
                # Meilleur ratio K/D
                if kill_death_ranking:
                    best_kd_value = kill_death_ranking[0][4]
                    best_kd_ratio = [
                        player for player, _, _, _, kd in kill_death_ranking 
                        if kd == best_kd_value
                    ]
        
        return {
            'unique_groups': unique_groups,
            'sorted_groups': sorted_groups,
            'default_group': default_group,
            'rankings_by_group': rankings_by_group,
            'default_ranking': default_ranking,
            'date_debut': date_debut_formatted,
            'date_fin': date_fin_formatted,
            'total_sessions': total_sessions,
            'unique_players_count': len(unique_players),
            'best_players': best_players,
            'best_score': best_score,
            'best_percentage_players': best_percentage_players,
            'best_percentage': best_percentage,
            'win_percentage_ranking': win_percentage_ranking,
            'elo_ranking': elo_ranking,
            'best_elo_players': best_elo_players,
            'best_elo': best_elo,
            'latest_date': latest_date,
            'latest_sessions_parsed': latest_sessions_parsed,
            'sessions_by_date': sessions_by_date,
            'all_sessions_data': all_sessions_data,
            'player_colors': PLAYER_TO_COLOR,
            'has_detailed_stats': has_detailed,
            'kill_death_ranking': kill_death_ranking,
            'kill_sources_aggregated': kill_sources_aggregated,
            'kill_relationships': kill_relationships,
            'all_players_for_matrix': all_players_for_matrix,
            'max_kills_in_matrix': max_kills_in_matrix,
            'top_killers': top_killers,
            'top_deaths': top_deaths,
            'top_self_kills': top_self_kills,
            'best_kd_ratio': best_kd_ratio,
            'best_kd_value': best_kd_value,
        }

