#!/usr/bin/env python3
"""
Sandbox pour débugger les données TowerStats en local.
Ce fichier n'est pas déployé et est ignoré par Git et Cloud Run.
"""

import urllib.request
import csv
import io
import json
from datetime import datetime
from collections import defaultdict

# URL publique de la Google Sheet en CSV
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQE3KfSAHXOp3hNFuR5oq_lgtEdEUzJ6YiRcov5gDSdgVSvuJDuy6sFslSC76qIa3CPjYSl9sTwQUrO/pub?output=csv'

# Mapping des couleurs vers les joueurs
COLOR_TO_PLAYER = {
    'pink': 'MEHDI',
    'green': 'JULIEN',
    'orange': 'LOUIS',
    'blue': None,
    'red': None,
    'yellow': 'ALEX',
    'purple': 'ERIC',
    'blue2': 'BENOIT',
    'white': 'DAVID'
}

# Mapping inverse : joueurs vers couleurs (pour l'affichage)
PLAYER_TO_COLOR = {
    'MEHDI': '#FFC0CB',      # pink
    'JULIEN': '#90EE90',     # green
    'LOUIS': '#FFA500',      # orange
    'BENOIT': '#4169E1',     # blue2 (royal blue)
    'DAVID': '#FFFFFF',      # white
    'ERIC': '#9370DB',       # purple (violet)
    'ALEX': '#FFFF00'        # yellow
}

def should_ignore_player(player_name):
    """Vérifie si un joueur doit être ignoré (AIJIMMY, P1, P2)."""
    if not player_name:
        return True
    player_upper = player_name.upper().replace(' ', '')
    return 'AIJIMMY' in player_upper or player_upper in ['P1', 'P2']

def get_sheet_data():
    """Récupère et parse les données depuis l'URL CSV publique."""
    try:
        print("📥 Téléchargement des données depuis Google Sheets...")
        with urllib.request.urlopen(CSV_URL) as response:
            csv_data = response.read().decode('utf-8')
        
        print("✅ Données téléchargées, parsing en cours...")
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        sessions = []
        
        for row in csv_reader:
            if not row.get('value'):
                continue
            
            session_id = row.get('id', '')
            if session_id:
                players_in_id = [p.strip() for p in session_id.split('-')]
                if all(should_ignore_player(p) for p in players_in_id):
                    continue
                
            try:
                data = json.loads(row['value'])
                session = {
                    'id': row['id'],
                    'date': row['date'],
                    'data': data
                }
                sessions.append(session)
            except json.JSONDecodeError:
                continue
        
        sessions.sort(key=lambda x: x['date'], reverse=True)
        print(f"✅ {len(sessions)} sessions chargées\n")
        return sessions
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des données: {e}")
        return None

def parse_session_data(session):
    """Parse les données d'une session selon le format (v1 ou v2)."""
    data = session['data']
    
    if 'version' in data and data['version'] == 'v1':
        players = {}
        for color in ['pink', 'green', 'orange', 'blue', 'red', 'yellow', 'purple', 'blue2', 'white']:
            today_key = f'{color}TodayWins'
            total_key = f'{color}TotalWins'
            if today_key in data and data[today_key] > 0:
                player_name = COLOR_TO_PLAYER.get(color, color.capitalize())
                if player_name and not should_ignore_player(player_name):
                    players[player_name] = {
                        'today': data[today_key],
                        'total': data.get(total_key, 0)
                    }
        print(f"DEBUG parse_session_data (v1): players = {players}")
        return players
    elif 'todayWin' in data:
        players = {}
        for player, today_wins in data['todayWin'].items():
            if not should_ignore_player(player):
                players[player] = {
                    'today': today_wins,
                    'total': data.get('totalWin', {}).get(player, 0)
                }
        print(f"DEBUG parse_session_data (v2): players = {players}")
        return players
    
    print(f"DEBUG parse_session_data: No players found, returning empty dict")
    return {}

def get_unique_groups(sessions):
    """Récupère tous les groupes de joueurs uniques (basés sur l'ID de session)."""
    groups = set()
    for session in sessions:
        players_in_id = [p.strip() for p in session['id'].split('-')]
        if not all(should_ignore_player(p) for p in players_in_id):
            groups.add(session['id'])
    return sorted(list(groups))

def get_global_ranking(sessions, group_id=None):
    """Calcule le classement global pour un groupe spécifique."""
    player_totals = defaultdict(int)
    
    for session in sessions:
        if group_id and session['id'] != group_id:
            continue
        
        players = parse_session_data(session)
        for player, stats in players.items():
            if stats['total'] > player_totals[player]:
                player_totals[player] = stats['total']
    
    ranking = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)
    return ranking

def group_sessions_by_date(sessions):
    """Groupe les sessions par date (soirée)."""
    sessions_by_date = defaultdict(list)
    
    for session in sessions:
        date_str = session['date'].split(' ')[0] if ' ' in session['date'] else session['date'][:10]
        sessions_by_date[date_str].append(session)
    
    sorted_dates = sorted(sessions_by_date.keys(), reverse=True)
    return {date: sessions_by_date[date] for date in sorted_dates}

def format_date(date_str, format_short=False):
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

def print_separator():
    """Affiche un séparateur visuel."""
    print("=" * 80)

def print_section(title):
    """Affiche un titre de section."""
    print_separator()
    print(f"  {title}")
    print_separator()

def display_statistics(sessions):
    """Affiche les statistiques générales."""
    print_section("📊 STATISTIQUES GÉNÉRALES")
    
    unique_groups = get_unique_groups(sessions)
    sessions_by_date = group_sessions_by_date(sessions)
    
    all_player_totals = defaultdict(int)
    rankings_by_group = {}
    for group_id in unique_groups:
        rankings_by_group[group_id] = get_global_ranking(sessions, group_id)
        for player, total in rankings_by_group[group_id]:
            if total > all_player_totals[player]:
                all_player_totals[player] = total
    
    unique_players = set()
    for session in sessions:
        players = parse_session_data(session)
        filtered_players = {p: v for p, v in players.items() if not should_ignore_player(p)}
        unique_players.update(filtered_players.keys())
    
    all_dates = []
    for session in sessions:
        try:
            date_str = session['date'][:10] if len(session['date']) >= 10 else session['date']
            all_dates.append(date_str)
        except:
            continue
    
    date_debut = min(all_dates) if all_dates else None
    date_fin = max(all_dates) if all_dates else None
    
    print(f"Total sessions: {len(sessions)}")
    print(f"Joueurs uniques: {len(unique_players)}")
    print(f"Groupes uniques: {len(unique_groups)}")
    print(f"Date début: {format_date(date_debut) if date_debut else 'N/A'}")
    print(f"Date fin: {format_date(date_fin) if date_fin else 'N/A'}")
    
    if all_player_totals:
        best_player = max(all_player_totals.items(), key=lambda x: x[1])
        print(f"\n🏆 Meilleur score global: {best_player[1]} ({best_player[0]})")
    
    print()

def display_rankings(sessions):
    """Affiche les classements par groupe."""
    print_section("🏆 CLASSEMENTS PAR GROUPE")
    
    unique_groups = get_unique_groups(sessions)
    
    def get_best_score(group_id):
        ranking = get_global_ranking(sessions, group_id)
        if ranking:
            return ranking[0][1]
        return 0
    
    sorted_groups = sorted(unique_groups, key=get_best_score, reverse=True)
    
    for group_id in sorted_groups:
        ranking = get_global_ranking(sessions, group_id)
        if not ranking:
            continue
        
        best_score = get_best_score(group_id)
        print(f"\n📋 Groupe: {group_id} (Meilleur: {best_score})")
        print("-" * 60)
        for rank, (player, total) in enumerate(ranking, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
            print(f"{medal} #{rank:2d} {player:15s} {total:4d} victoires")
    
    print()

def display_latest_sessions(sessions, limit=5):
    """Affiche les dernières sessions."""
    print_section(f"📅 DERNIÈRES {limit} SESSIONS")
    
    sessions_by_date = group_sessions_by_date(sessions)
    latest_date = list(sessions_by_date.keys())[0] if sessions_by_date else None
    
    if not latest_date:
        print("Aucune session trouvée.")
        return
    
    latest_sessions = sessions_by_date[latest_date]
    print(f"Date: {format_date(latest_date)} ({len(latest_sessions)} session(s))\n")
    
    for i, session in enumerate(latest_sessions[:limit], 1):
        players = parse_session_data(session)
        if not players:
            continue
        
        print(f"Session {i}: {session['id']}")
        print(f"  Date: {session['date']}")
        print("  Résultats:")
        sorted_players = sorted(players.items(), key=lambda x: x[1]['today'], reverse=True)
        for rank, (player, stats) in enumerate(sorted_players, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
            print(f"    {medal} #{rank} {player:15s} Session: {stats['today']:2d} | Total: {stats['total']:4d}")
        print()
    
    print()

def cumulate_today_points(sessions):
    """Cumule les points du jour (today) de chaque joueur et le nombre de parties jouées.
    
    Returns:
        tuple: (dict_victoires, dict_parties_jouees)
            - dict_victoires: {joueur: total_victoires}
            - dict_parties_jouees: {joueur: total_parties_jouees}
    """
    player_victories = defaultdict(int)
    player_games_played = defaultdict(int)
    
    print("\n🔢 DÉBUT DU CALCUL DES POINTS DU JOUR CUMULÉS")
    print("=" * 80)
    
    for session_idx, session in enumerate(sessions, 1):
        print(f"\n📅 Session {session_idx}: {session['id']} ({session['date'][:10]})")
        players = parse_session_data(session)
        
        if not players:
            print("  ⚠️  Aucun joueur trouvé dans cette session")
            continue
        
        # Calculer le nombre total de parties dans cette session
        total_games_in_session = sum(stats['today'] for stats in players.values())
        print(f"  🎮 Total de parties dans cette session: {total_games_in_session}")
        
        print(f"  👥 {len(players)} joueur(s) dans cette session:")
        for player, stats in players.items():
            today_victories = stats['today']
            
            # Ajouter les victoires
            previous_victories = player_victories[player]
            player_victories[player] += today_victories
            new_victories = player_victories[player]
            
            # Ajouter le nombre de parties jouées (total de la session)
            previous_games = player_games_played[player]
            player_games_played[player] += total_games_in_session
            new_games = player_games_played[player]
            
            print(f"    ➕ {player:15s}: +{today_victories:2d} victoires (total: {previous_victories:4d} → {new_victories:4d})")
            print(f"       📊 +{total_games_in_session:2d} parties jouées (total: {previous_games:4d} → {new_games:4d})")
    
    print("\n" + "=" * 80)
    print("✅ CALCUL TERMINÉ\n")
    
    return dict(player_victories), dict(player_games_played)

def display_cumulated_today_points(sessions):
    """Affiche le classement par pourcentage de victoires basé sur les parties jouées."""
    print_section("📊 CLASSEMENT PAR POURCENTAGE DE VICTOIRES")
    
    player_victories, player_games_played = cumulate_today_points(sessions)
    
    if not player_victories:
        print("❌ Aucune donnée trouvée.")
        return
    
    # Calculer les pourcentages pour chaque joueur
    player_stats = []
    for player in player_victories.keys():
        victories = player_victories[player]
        games_played = player_games_played[player]
        
        if games_played > 0:
            win_percentage = (victories / games_played) * 100
        else:
            win_percentage = 0.0
        
        player_stats.append({
            'player': player,
            'victories': victories,
            'games_played': games_played,
            'win_percentage': win_percentage
        })
    
    # Trier par pourcentage décroissant
    sorted_players = sorted(player_stats, key=lambda x: x['win_percentage'], reverse=True)
    
    print("🏆 CLASSEMENT PAR POURCENTAGE DE VICTOIRES:")
    print("-" * 80)
    print(f"{'Rang':<6} {'Joueur':<15} {'Victoires':<12} {'Parties':<12} {'% Victoires':<15}")
    print("-" * 80)
    
    for rank, stats in enumerate(sorted_players, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
        player = stats['player']
        victories = stats['victories']
        games_played = stats['games_played']
        win_percentage = stats['win_percentage']
        
        print(f"{medal} #{rank:2d}  {player:15s} {victories:4d}/{games_played:4d}      {win_percentage:6.2f}%")
    
    print()

def display_raw_session(sessions, session_id=None, index=None):
    """Affiche les données brutes d'une session."""
    print_section("🔍 DONNÉES BRUTES D'UNE SESSION")
    
    if session_id:
        session = next((s for s in sessions if s['id'] == session_id), None)
        if not session:
            print(f"❌ Session '{session_id}' non trouvée.")
            return
    elif index is not None:
        if 0 <= index < len(sessions):
            session = sessions[index]
        else:
            print(f"❌ Index {index} invalide (0-{len(sessions)-1}).")
            return
    else:
        print("❌ Spécifiez soit session_id soit index.")
        return
    
    print(f"ID: {session['id']}")
    print(f"Date: {session['date']}")
    print("Données JSON:")
    print(json.dumps(session['data'], indent=2, ensure_ascii=False))
    print()
    
    players = parse_session_data(session)
    if players:
        print("Joueurs parsés:")
        for player, stats in players.items():
            print(f"  - {player}: {stats['today']} victoires (session), {stats['total']} (total)")
    print()

def main():
    """Fonction principale du sandbox."""
    print("\n" + "=" * 80)
    print("  🏹 TOWERSTATS SANDBOX - Mode Debug 🏹")
    print("=" * 80 + "\n")
    
    sessions = get_sheet_data()
    if not sessions:
        print("❌ Impossible de charger les données. Vérifiez votre connexion internet.")
        return
    
    while True:
        print("\nOptions disponibles:")
        print("  1. Afficher les statistiques générales")
        print("  2. Afficher les classements par groupe")
        print("  3. Afficher les dernières sessions")
        print("  4. Afficher les données brutes d'une session (par index)")
        print("  5. Afficher les données brutes d'une session (par ID)")
        print("  6. Lister tous les groupes")
        print("  7. Lister toutes les sessions (résumé)")
        print("  8. Cumuler les points du jour de chaque joueur (débogage)")
        print("  0. Quitter")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == '0':
            print("\n👋 Au revoir!")
            break
        elif choice == '1':
            display_statistics(sessions)
        elif choice == '2':
            display_rankings(sessions)
        elif choice == '3':
            limit = input("Nombre de sessions à afficher (défaut: 5): ").strip()
            limit = int(limit) if limit.isdigit() else 5
            display_latest_sessions(sessions, limit)
        elif choice == '4':
            index = input("Index de la session (0-{}): ".format(len(sessions)-1)).strip()
            if index.isdigit():
                display_raw_session(sessions, index=int(index))
            else:
                print("❌ Index invalide.")
        elif choice == '5':
            session_id = input("ID de la session: ").strip()
            if session_id:
                display_raw_session(sessions, session_id=session_id)
            else:
                print("❌ ID vide.")
        elif choice == '6':
            print_section("📋 LISTE DES GROUPES")
            unique_groups = get_unique_groups(sessions)
            for i, group_id in enumerate(unique_groups, 1):
                ranking = get_global_ranking(sessions, group_id)
                best_score = ranking[0][1] if ranking else 0
                print(f"{i:2d}. {group_id} (Meilleur: {best_score})")
            print()
        elif choice == '7':
            print_section("📋 LISTE DES SESSIONS (RÉSUMÉ)")
            for i, session in enumerate(sessions, 1):
                players = parse_session_data(session)
                player_count = len(players)
                print(f"{i:3d}. [{session['date'][:10]}] {session['id']:30s} ({player_count} joueur(s))")
            print()
        elif choice == '8':
            display_cumulated_today_points(sessions)
        else:
            print("❌ Choix invalide.")

if __name__ == '__main__':
    main()

