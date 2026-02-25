"""Gestion des statistiques et calculs à partir des sessions filtrées."""

from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

from .data_manager import SessionDataManager
from .config import PLAYER_TO_COLOR

MEDAL_BY_RANK = {1: '🥇', 2: '🥈', 3: '🥉'}


class SessionStatsManager:
    """Effectue tous les calculs d'agrégat/statistiques à partir d'une liste de sessions filtrées."""
    
    def __init__(
        self,
        sessions: List[Dict[str, Any]],
        date_start: str | None = None,
        date_end: str | None = None,
    ):
        """Initialise le manager avec une éventuelle fenêtre de dates.

        Args:
            sessions: Liste de sessions déjà corrigées/triées.
            date_start: Date de début au format YYYY-MM-DD (inclusif).
            date_end: Date de fin au format YYYY-MM-DD (inclusif).
        """
        self.sessions = self._filter_sessions_by_date(sessions, date_start, date_end)

    def _session_date_str(self, session: Dict[str, Any]) -> str:
        """Normalised YYYY-MM-DD date string for a session."""
        return SessionDataManager.extract_date_str(str(session.get('date', '')))

    def _filter_sessions_by_date(
        self,
        sessions: List[Dict[str, Any]],
        date_start: str | None,
        date_end: str | None,
    ) -> List[Dict[str, Any]]:
        """Filtre les sessions selon une fenêtre de dates (inclusives).

        Les dates sont comparées au format YYYY-MM-DD.
        Si aucune date n'est fournie, toutes les sessions sont conservées.
        """
        if not date_start and not date_end:
            return sessions

        filtered: List[Dict[str, Any]] = []
        for session in sessions:
            date_str = self._session_date_str(session)
            if not date_str:
                continue
            if date_start and date_str < date_start:
                continue
            if date_end and date_str > date_end:
                continue
            filtered.append(session)
        return filtered

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
            date_str = self._session_date_str(session)
            sessions_by_date[date_str].append(session)
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
        return MEDAL_BY_RANK.get(rank, '')

    def calculate_elo_legacy_ratings(self, initial_elo=1500, k_factor=32):
        """Calcule les ratings ELO legacy basés sur toutes les sessions.

        Cette version conserve exactement la logique historique
        (mise à jour séquentielle paire par paire dans une session).
        """
        elo_ratings = defaultdict(lambda: initial_elo)
        sorted_sessions = sorted(self.sessions, key=lambda x: x.get('date', ''))

        for session in sorted_sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players or len(players) < 2:
                continue

            sorted_players = sorted(
                players.items(),
                key=lambda x: x[1]['today'],
                reverse=True
            )
            player_ranks = {player: rank for rank, (player, _) in enumerate(sorted_players, start=1)}
            player_names = list(players.keys())

            for i, player_a in enumerate(player_names):
                for player_b in player_names[i + 1:]:
                    rank_a = player_ranks[player_a]
                    rank_b = player_ranks[player_b]
                    elo_a = elo_ratings[player_a]
                    elo_b = elo_ratings[player_b]
                    expected_score_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

                    if rank_a < rank_b:
                        actual_score_a = 1.0
                    elif rank_a == rank_b:
                        actual_score_a = 0.5
                    else:
                        actual_score_a = 0.0

                    elo_change = k_factor * (actual_score_a - expected_score_a)
                    elo_ratings[player_a] += elo_change
                    elo_ratings[player_b] -= elo_change

        sorted_elo = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_elo)

    def calculate_elo_ratings(self, initial_elo=1500, k_factor=32):
        """Calcule les ratings ELO batch (nouvelle version par session).

        Pour chaque session, les deltas ELO de toutes les paires sont calculés
        avec les ratings au début de la session puis appliqués en batch.
        """
        elo_ratings = defaultdict(lambda: initial_elo)
        sorted_sessions = sorted(self.sessions, key=lambda x: x.get('date', ''))

        for session in sorted_sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players or len(players) < 2:
                continue

            sorted_players = sorted(
                players.items(),
                key=lambda x: x[1]['today'],
                reverse=True
            )
            player_ranks = {player: rank for rank, (player, _) in enumerate(sorted_players, start=1)}
            player_names = sorted(players.keys())
            session_deltas = defaultdict(float)

            for i, player_a in enumerate(player_names):
                for player_b in player_names[i + 1:]:
                    rank_a = player_ranks[player_a]
                    rank_b = player_ranks[player_b]
                    elo_a = elo_ratings[player_a]
                    elo_b = elo_ratings[player_b]
                    expected_score_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

                    if rank_a < rank_b:
                        actual_score_a = 1.0
                    elif rank_a == rank_b:
                        actual_score_a = 0.5
                    else:
                        actual_score_a = 0.0

                    elo_change = k_factor * (actual_score_a - expected_score_a)
                    session_deltas[player_a] += elo_change
                    session_deltas[player_b] -= elo_change

            for player, delta in session_deltas.items():
                elo_ratings[player] += delta

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

    def get_elo_legacy_ranking(self, initial_elo=1500, k_factor=32):
        """Retourne le classement ELO legacy des joueurs."""
        elo_ratings = self.calculate_elo_legacy_ratings(initial_elo, k_factor)
        return list(elo_ratings.items())
    
    def has_detailed_stats(self) -> bool:
        """Vérifie si au moins une session contient des statistiques détaillées."""
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
        """Kills/deaths/self_kills only from sessions that have detailed stats.

        Uses cumulative deltas: sessions are processed in chronological order;
        for each session with detailed stats, we add (current_cumulative - previous_cumulative)
        per player so numerator and denominator (Parties) refer to the same period.
        """
        sessions_chrono = sorted(self.sessions, key=lambda s: s.get('date', ''))
        player_kills = defaultdict(int)
        player_deaths = defaultdict(int)
        player_self_kills = defaultdict(int)
        prev_kill = defaultdict(int)
        prev_death = defaultdict(int)
        prev_self = defaultdict(int)
        for session in sessions_chrono:
            if not SessionDataManager.has_detailed_stats(session):
                continue
            players = SessionDataManager.parse_session_data(session)
            for player, stats in players.items():
                if 'detailed' not in stats:
                    continue
                d = stats['detailed']
                cur_k = d.get('kill', 0)
                cur_d = d.get('death', 0)
                cur_s = d.get('self', 0)
                player_kills[player] += max(0, cur_k - prev_kill[player])
                player_deaths[player] += max(0, cur_d - prev_death[player])
                player_self_kills[player] += max(0, cur_s - prev_self[player])
                prev_kill[player] = cur_k
                prev_death[player] = cur_d
                prev_self[player] = cur_s
        return player_kills, player_deaths, player_self_kills

    def get_kill_death_stats(self):
        """Calcule les statistiques de kills et deaths par joueur.

        Kills/Deaths/Self = totaux uniquement sur les sessions où les stats détaillées
        existent (même période que "Parties"). Parties = somme des parties jouées
        dans ces mêmes sessions (total_games_in_session = somme des victoires du jour
        de tous les joueurs de la session). Les moyennes = totaux / Parties.

        Returns:
            list: Liste de tuples (joueur, kills, deaths, self_kills, kd_ratio,
                  games_played, kills_per_game, deaths_per_game, self_per_game)
                  triée par ratio K/D décroissant
        """
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
        """Crée une matrice montrant qui tue qui avec la moyenne de kills par partie.
        
        Pour chaque paire (killer, victim), calcule la moyenne de kills par partie
        en divisant le total de kills par le nombre total de parties dans les sessions
        où les deux joueurs ont joué ensemble.
        
        Returns:
            dict: {killer: {victim: average_kills_per_game}} - Matrice des moyennes de kills entre joueurs
        """
        # Dictionnaires pour stocker les totaux de kills et le nombre de parties
        total_kills = defaultdict(lambda: defaultdict(int))
        total_games = defaultdict(lambda: defaultdict(int))
        
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            if not players:
                continue
            
            # Calculer le nombre total de parties dans cette session
            total_games_in_session = sum(stats['today'] for stats in players.values())
            
            # Pour chaque joueur (victime)
            for player, stats in players.items():
                if 'detailed' in stats:
                    kill_by = stats['detailed'].get('killBy', {})
                    # Pour chaque tueur qui a tué ce joueur
                    for killer, count in kill_by.items():
                        # Ajouter les kills au total
                        total_kills[killer][player] += count
                        # Ajouter le nombre de parties de cette session
                        total_games[killer][player] += total_games_in_session
        
        # Calculer les moyennes
        relationships = defaultdict(dict)
        for killer in total_kills:
            for victim in total_kills[killer]:
                kills = total_kills[killer][victim]
                games = total_games[killer][victim]
                if games > 0:
                    average = kills / games
                    relationships[killer][victim] = average
                else:
                    relationships[killer][victim] = 0.0
        
        return dict(relationships)
    
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
        
        date_debut = min(sessions_by_date.keys()) if sessions_by_date else None
        date_fin = max(sessions_by_date.keys()) if sessions_by_date else None
        date_debut_formatted = self.format_date(date_debut, format_short=True) if date_debut else "N/A"
        date_fin_formatted = self.format_date(date_fin, format_short=True) if date_fin else "N/A"
        
        # Statistiques supplémentaires
        total_sessions = len(self.sessions)
        unique_players = set()
        for session in self.sessions:
            players = SessionDataManager.parse_session_data(session)
            unique_players.update(players.keys())
        
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
        
        # Classement ELO (nouvelle version batch)
        try:
            elo_ranking = self.get_elo_ranking()
            # S'assurer que elo_ranking est une liste
            if not isinstance(elo_ranking, list):
                elo_ranking = list(elo_ranking) if elo_ranking else []
        except Exception:
            # En cas d'erreur, retourner une liste vide
            elo_ranking = []

        # Classement ELO legacy
        try:
            elo_legacy_ranking = self.get_elo_legacy_ranking()
            if not isinstance(elo_legacy_ranking, list):
                elo_legacy_ranking = list(elo_legacy_ranking) if elo_legacy_ranking else []
        except Exception:
            elo_legacy_ranking = []

        # Meilleur ELO (nouveau)
        best_elo_players = []
        best_elo = 0.0
        if elo_ranking:
            best_elo = elo_ranking[0][1]
            best_elo_players = [player for player, rating in elo_ranking if rating == best_elo]

        # Meilleur ELO legacy
        best_elo_legacy_players = []
        best_elo_legacy = 0.0
        if elo_legacy_ranking:
            best_elo_legacy = elo_legacy_ranking[0][1]
            best_elo_legacy_players = [
                player for player, rating in elo_legacy_ranking if rating == best_elo_legacy
            ]
        
        def sorted_players_by_today(session):
            players = SessionDataManager.parse_session_data(session)
            if not players:
                return None
            return sorted(players.items(), key=lambda x: x[1]['today'], reverse=True)

        latest_sessions_parsed = []
        for session in latest_sessions:
            sorted_players = sorted_players_by_today(session)
            if sorted_players:
                latest_sessions_parsed.append({'session': session, 'players': sorted_players})

        all_sessions_data = []
        for date, date_sessions in sessions_by_date.items():
            for session in date_sessions:
                sorted_players = sorted_players_by_today(session)
                if sorted_players:
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
        least_deaths_row = None
        least_self_kills_row = None
        best_kd_ratio = []
        best_kd_value = 0.0
        
        if has_detailed:
            kill_death_ranking = self.get_kill_death_stats()
            kill_sources_aggregated = self.get_kill_sources_stats()
            kill_relationships = self.get_kill_relationships()

            # Collecter tous les joueurs uniques pour la matrice (tueurs + victimes)
            all_players_set = set()
            for player, *_ in kill_death_ranking:
                all_players_set.add(player)
            for killer in kill_relationships.keys():
                all_players_set.add(killer)
                for victim in kill_relationships[killer].keys():
                    all_players_set.add(victim)
            all_players_for_matrix = sorted(list(all_players_set))

            # Maximum de kills pour la normalisation de la matrice
            max_kills_in_matrix = 1
            for killer, victims in kill_relationships.items():
                for victim, count in victims.items():
                    if count > max_kills_in_matrix:
                        max_kills_in_matrix = count

            # Top / least depuis kill_death_ranking (une seule source pour cartes et tableau)
            if kill_death_ranking:
                top_killers = sorted(kill_death_ranking, key=lambda x: x[6], reverse=True)[:5]
                by_deaths = sorted(kill_death_ranking, key=lambda x: x[7], reverse=True)
                top_deaths = by_deaths[:5]
                least_deaths_row = by_deaths[-1]
                by_self = sorted(kill_death_ranking, key=lambda x: x[8], reverse=True)
                top_self_kills = [(r[0], r[3], r[8]) for r in by_self[:5]]
                least_self_kills_row = by_self[-1]
                best_kd_value = kill_death_ranking[0][4]
                best_kd_ratio = [row[0] for row in kill_death_ranking if row[4] == best_kd_value]
        
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
            'elo_legacy_ranking': elo_legacy_ranking,
            'best_elo_legacy_players': best_elo_legacy_players,
            'best_elo_legacy': best_elo_legacy,
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
            'least_deaths_row': least_deaths_row,
            'least_self_kills_row': least_self_kills_row,
            'best_kd_ratio': best_kd_ratio,
            'best_kd_value': best_kd_value,
        }

