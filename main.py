import functions_framework
import urllib.request
import csv
import io
import json
from datetime import datetime
from collections import defaultdict, Counter

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

def get_player_color(player_name):
    """Retourne la couleur d'un joueur pour l'affichage."""
    return PLAYER_TO_COLOR.get(player_name.upper(), '#FFD700')  # Par défaut: or

def get_sheet_data():
    """Récupère et parse les données depuis l'URL CSV publique."""
    try:
        # Télécharge le CSV
        with urllib.request.urlopen(CSV_URL) as response:
            csv_data = response.read().decode('utf-8')
        
        # Parse le CSV
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        sessions = []
        
        for row in csv_reader:
            if not row.get('value'):
                continue
            
            # Ignorer les sessions avec uniquement des joueurs à ignorer (AIJIMMY, P1, P2) dans l'ID
            session_id = row.get('id', '')
            if session_id:
                players_in_id = [p.strip() for p in session_id.split('-')]
                # Ignorer si tous les joueurs dans l'ID sont à ignorer
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
        
        # Trier par date (plus récent en premier)
        sessions.sort(key=lambda x: x['date'], reverse=True)
        return sessions
    except Exception as e:
        return None, str(e)

def should_ignore_player(player_name):
    """Vérifie si un joueur doit être ignoré (AIJIMMY, P1, P2)."""
    if not player_name:
        return True
    player_upper = player_name.upper().replace(' ', '')
    # Ignorer AIJIMMY, P1, P2
    return 'AIJIMMY' in player_upper or player_upper in ['P1', 'P2']

def parse_session_data(session):
    """Parse les données d'une session selon le format (v1 ou v2)."""
    data = session['data']
    
    if 'version' in data and data['version'] == 'v1':
        # Format ancien avec couleurs
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
        return players
    elif 'todayWin' in data:
        # Format nouveau avec noms de joueurs
        players = {}
        for player, today_wins in data['todayWin'].items():
            if not should_ignore_player(player):
                players[player] = {
                    'today': today_wins,
                    'total': data.get('totalWin', {}).get(player, 0)
                }
        return players
    return {}

def get_unique_groups(sessions):
    """Récupère tous les groupes de joueurs uniques (basés sur l'ID de session)."""
    groups = set()
    for session in sessions:
        # Ignorer les sessions avec uniquement des joueurs à ignorer
        players_in_id = [p.strip() for p in session['id'].split('-')]
        if not all(should_ignore_player(p) for p in players_in_id):
            groups.add(session['id'])
    return sorted(list(groups))

def get_global_ranking(sessions, group_id=None):
    """Calcule le classement global pour un groupe spécifique."""
    player_totals = defaultdict(int)
    
    for session in sessions:
        # Filtrer par groupe si spécifié
        if group_id and session['id'] != group_id:
            continue
        
        players = parse_session_data(session)
        for player, stats in players.items():
            # Prendre le total le plus récent pour chaque joueur
            if stats['total'] > player_totals[player]:
                player_totals[player] = stats['total']
    
    # Trier par total décroissant
    ranking = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)
    return ranking

# def get_absolute_global_ranking(sessions):
#     """Calcule le classement global absolu : somme de toutes les victoires de session (today) 
#     de chaque joueur depuis le début, toutes sessions et tous groupes confondus."""
#     player_total_wins = defaultdict(int)
#     
#     for session in sessions:
#         players = parse_session_data(session)
#         for player, stats in players.items():
#             # Additionner toutes les "Victoires Session" (today) pour chaque joueur
#             # depuis le début, toutes sessions et tous groupes confondus
#             player_total_wins[player] += stats['today']
#     
#     # Trier par total décroissant
#     ranking = sorted(player_total_wins.items(), key=lambda x: x[1], reverse=True)
#     return ranking

def group_sessions_by_date(sessions):
    """Groupe les sessions par date (soirée)."""
    sessions_by_date = defaultdict(list)
    
    for session in sessions:
        # Extraire la date (sans l'heure)
        date_str = session['date'].split(' ')[0] if ' ' in session['date'] else session['date'][:10]
        sessions_by_date[date_str].append(session)
    
    # Trier les dates (plus récent en premier)
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

def generate_html(sessions):
    """Génère la page HTML complète avec style pixelart."""
    
    # Calculer les données
    unique_groups = get_unique_groups(sessions)
    sessions_by_date = group_sessions_by_date(sessions)
    latest_date = list(sessions_by_date.keys())[0] if sessions_by_date else None
    latest_sessions = sessions_by_date[latest_date] if latest_date else []
    
    # Calculer les classements pour chaque groupe
    rankings_by_group = {}
    for group_id in unique_groups:
        rankings_by_group[group_id] = get_global_ranking(sessions, group_id)
    
    # Trier les groupes par le meilleur score du groupe (décroissant)
    def get_best_score(group_id):
        ranking = rankings_by_group.get(group_id, [])
        if ranking:
            return ranking[0][1]  # Score du premier joueur (meilleur)
        return 0
    
    sorted_groups = sorted(unique_groups, key=get_best_score, reverse=True)
    
    # Classement par défaut (groupe avec le meilleur score)
    default_group = sorted_groups[0] if sorted_groups else None
    default_ranking = rankings_by_group.get(default_group, []) if default_group else []
    
    # Calculer le classement global absolu (somme de toutes les victoires)
    # absolute_global_ranking = get_absolute_global_ranking(sessions)
    
    # Calculer les dates de début et de fin
    all_dates = []
    for session in sessions:
        try:
            date_str = session['date'][:10] if len(session['date']) >= 10 else session['date']
            all_dates.append(date_str)
        except:
            continue
    
    date_debut = min(all_dates) if all_dates else None
    date_fin = max(all_dates) if all_dates else None
    date_debut_formatted = format_date(date_debut, format_short=True) if date_debut else "N/A"
    date_fin_formatted = format_date(date_fin, format_short=True) if date_fin else "N/A"
    
    # Statistiques supplémentaires
    total_sessions = len(sessions)
    unique_players = set()
    for session in sessions:
        players = parse_session_data(session)
        # Filtrer les joueurs AIJIMMY
        filtered_players = {p: v for p, v in players.items() if not should_ignore_player(p)}
        unique_players.update(filtered_players.keys())
    
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TowerStats - Statistiques TowerFall Ascension</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Press Start 2P', cursive;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #e8e8e8;
            line-height: 1.6;
            font-size: 10px;
            min-height: 100vh;
            background-image: 
                repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.1) 2px, rgba(0,0,0,0.1) 4px),
                repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(0,0,0,0.1) 2px, rgba(0,0,0,0.1) 4px);
        }
        
        /* Header */
        header {
            background: linear-gradient(135deg, #2d1b3d 0%, #1a0d2e 100%);
            border-bottom: 4px solid #8b4513;
            padding: 25px 20px;
            text-align: center;
            box-shadow: 0 4px 8px rgba(0,0,0,0.5);
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 80px;
        }
        
        header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: repeating-linear-gradient(
                45deg,
                transparent,
                transparent 10px,
                rgba(139, 69, 19, 0.1) 10px,
                rgba(139, 69, 19, 0.1) 20px
            );
            pointer-events: none;
        }
        
        h1 {
            font-size: 24px;
            color: #ffd700;
            text-shadow: 
                3px 3px 0px #8b4513,
                0 0 10px rgba(255, 215, 0, 0.5);
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }
        
        .header-image-placeholder {
            width: 200px;
            height: 100px;
            margin: 10px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            z-index: 1;
        }
        
        .header-image-placeholder img {
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
        }
        
        /* Sticky Menu */
        nav {
            background: linear-gradient(135deg, #3d2817 0%, #2d1b0d 100%);
            border-bottom: 3px solid #8b4513;
            padding: 15px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 4px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        nav ul {
            list-style: none;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            margin: 0;
            padding: 0;
        }
        
        .stats-dates {
            color: #ffd700;
            font-size: 8px;
            text-shadow: 1px 1px 0px #8b4513;
            display: flex;
            flex-direction: column;
            line-height: 1.4;
            margin-top: 20px;
            text-align: center;
        }
        
        nav a {
            color: #ffd700;
            text-decoration: none;
            padding: 8px 16px;
            border: 2px solid #8b4513;
            background: rgba(139, 69, 19, 0.3);
            transition: all 0.3s;
            display: inline-block;
        }
        
        nav a:hover {
            background: rgba(139, 69, 19, 0.6);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.5);
        }
        
        /* Main Content */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        section {
            background: rgba(45, 27, 61, 0.8);
            border: 3px solid #8b4513;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 
                inset 0 0 20px rgba(0,0,0,0.5),
                0 4px 8px rgba(0,0,0,0.5);
            position: relative;
        }
        
        section::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: repeating-linear-gradient(
                0deg,
                transparent,
                transparent 20px,
                rgba(139, 69, 19, 0.05) 20px,
                rgba(139, 69, 19, 0.05) 22px
            );
            pointer-events: none;
        }
        
        section h2 {
            color: #ffd700;
            font-size: 16px;
            margin-bottom: 15px;
            text-shadow: 2px 2px 0px #8b4513;
            position: relative;
            z-index: 1;
        }
        
        .ranking-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            position: relative;
            z-index: 1;
        }
        
        .ranking-table th {
            background: linear-gradient(135deg, #8b4513 0%, #654321 100%);
            color: #ffd700;
            padding: 12px;
            text-align: left;
            border: 2px solid #654321;
            font-size: 10px;
        }
        
        .ranking-table td {
            padding: 10px 12px;
            border: 2px solid #654321;
            background: rgba(26, 26, 46, 0.5);
            font-size: 9px;
        }
        
        .ranking-table tr:nth-child(even) td {
            background: rgba(26, 26, 46, 0.7);
        }
        
        .ranking-table tr:hover td {
            background: rgba(139, 69, 19, 0.3);
        }
        
        .rank-1 { color: #ffd700; font-weight: bold; }
        .rank-2 { color: #c0c0c0; }
        .rank-3 { color: #cd7f32; }
        
        .session-card {
            background: rgba(26, 26, 46, 0.6);
            border: 2px solid #8b4513;
            padding: 15px;
            margin-bottom: 15px;
            position: relative;
            z-index: 1;
        }
        
        .session-date {
            color: #ffd700;
            font-size: 12px;
            margin-bottom: 10px;
        }
        
        .session-players {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        
        .player-stat {
            background: rgba(139, 69, 19, 0.2);
            padding: 8px;
            border: 1px solid #8b4513;
            font-size: 8px;
        }
        
        .player-name {
            font-weight: bold;
            /* La couleur sera définie inline pour chaque joueur */
        }
        
        .group-select {
            background: linear-gradient(135deg, #8b4513 0%, #654321 100%);
            color: #ffd700;
            border: 2px solid #654321;
            padding: 10px 15px;
            font-family: 'Press Start 2P', cursive;
            font-size: 8px;
            cursor: pointer;
            width: 100%;
            max-width: 500px;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23ffd700' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 10px center;
            padding-right: 35px;
        }
        
        .group-select:hover {
            background: linear-gradient(135deg, #654321 0%, #8b4513 100%);
        }
        
        .group-select:focus {
            outline: none;
            border-color: #ffd700;
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-card {
            background: rgba(26, 26, 46, 0.6);
            border: 2px solid #8b4513;
            padding: 15px;
            text-align: center;
            position: relative;
            z-index: 1;
        }
        
        .stat-value {
            font-size: 20px;
            color: #ffd700;
            margin: 10px 0;
        }
        
        .stat-label {
            font-size: 8px;
            color: #c0c0c0;
        }
        
        .toggle-button {
            background: linear-gradient(135deg, #8b4513 0%, #654321 100%);
            color: #ffd700;
            border: 2px solid #654321;
            padding: 12px 20px;
            font-family: 'Press Start 2P', cursive;
            font-size: 9px;
            cursor: pointer;
            margin: 20px 0;
            transition: all 0.3s;
            position: relative;
            z-index: 1;
        }
        
        .toggle-button:hover {
            background: linear-gradient(135deg, #654321 0%, #8b4513 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.5);
        }
        
        .pagination-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin: 20px 0;
            position: relative;
            z-index: 1;
        }
        
        .pagination-button {
            background: linear-gradient(135deg, #8b4513 0%, #654321 100%);
            color: #ffd700;
            border: 2px solid #654321;
            padding: 8px 16px;
            font-family: 'Press Start 2P', cursive;
            font-size: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .pagination-button:hover:not(:disabled) {
            background: linear-gradient(135deg, #654321 0%, #8b4513 100%);
            transform: translateY(-2px);
        }
        
        .pagination-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .page-info {
            color: #ffd700;
            font-size: 9px;
        }
        
        @media (max-width: 768px) {
            body { font-size: 8px; }
            h1 { font-size: 18px; }
            section h2 { font-size: 12px; }
            nav ul { flex-direction: column; gap: 10px; }
        }
    </style>
</head>
<body>
    <header>
        <h1>🏹 TOWERSTATS 🏹</h1>
    </header>
    
    <nav>
        <ul>
            <li><a href="#statistiques">Statistiques</a></li>
            <!-- <li><a href="#classement-global">Classement Général</a></li> -->
            <li><a href="#classement">Classement par Groupe</a></li>
            <li><a href="#derniere-soiree">Dernière Soirée</a></li>
        </ul>
    </nav>
    
    <div class="container">
        <section id="statistiques">
            <h2>📊 Statistiques Générales</h2>
            <div class="stats-grid">'''
    
    # Meilleur joueur (parmi tous les groupes) - en premier
    all_player_totals = defaultdict(int)
    for ranking in rankings_by_group.values():
        for player, total in ranking:
            if total > all_player_totals[player]:
                all_player_totals[player] = total
    
    if all_player_totals:
        best_player = max(all_player_totals.items(), key=lambda x: x[1])
        best_player_name, best_score = best_player
        html += f'''
                <div class="stat-card">
                    <div class="stat-label">Meilleur Score Global</div>
                    <div class="stat-value">{best_score}</div>
                    <div class="stat-label">{best_player_name}</div>
                </div>'''
    
    # Joueurs Uniques - en deuxième
    html += f'''
                <div class="stat-card">
                    <div class="stat-label">Joueurs Uniques</div>
                    <div class="stat-value">{len(unique_players)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Sessions</div>
                    <div class="stat-value">{total_sessions}</div>
                </div>'''
    
    html += f'''
            </div>
            <div class="stats-dates">
                <div>Depuis le {date_debut_formatted}</div>
                <div>Dernière soirée jouée le {date_fin_formatted}</div>
            </div>
        </section>
        
        <!-- Section Classement Général Actuel commentée
        <section id="classement-global">
            <h2>🏆 Classement Général Actuel</h2>
            <table class="ranking-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Joueur</th>
                        <th>Victoires</th>
                    </tr>
                </thead>
                <tbody>
                </tbody>
            </table>
        </section>
        -->
        
        <section id="classement">
            <h2>🏆 Classement par Groupe</h2>
            <div style="margin-bottom: 20px; position: relative; z-index: 1;">
                <label for="group-select" style="color: #ffd700; font-size: 10px; display: block; margin-bottom: 10px;">
                    Sélectionner un groupe de joueurs:
                </label>
                <select id="group-select" class="group-select">
'''
    
    # Générer les options du menu déroulant (triées par meilleur score)
    for group_id in sorted_groups:
        selected = 'selected' if group_id == default_group else ''
        best_score = get_best_score(group_id)
        html += f'                    <option value="{group_id}" {selected}>{group_id} (Meilleur: {best_score})</option>\n'
    
    html += '''                </select>
            </div>
            <table class="ranking-table" id="ranking-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Joueur</th>
                        <th>Victoires</th>
                    </tr>
                </thead>
                <tbody id="ranking-tbody">'''
    
    # Classement par défaut
    for rank, (player, total) in enumerate(default_ranking, 1):
        rank_class = f'rank-{rank}' if rank <= 3 else ''
        player_color = get_player_color(player)
        html += f'''
                    <tr>
                        <td class="{rank_class}">#{rank}</td>
                        <td class="{rank_class}" style="color: {player_color}; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">{player}</td>
                        <td class="{rank_class}">{total}</td>
                    </tr>'''
    
    # Convertir les classements en JSON pour JavaScript
    rankings_json = json.dumps(rankings_by_group).replace('</', '<\\/')
    player_colors_json = json.dumps(PLAYER_TO_COLOR).replace('</', '<\\/')
    
    html += f'''
                </tbody>
            </table>
            <script>
                const rankingsByGroup = {rankings_json};
                if (typeof playerColors === 'undefined') {{
                    var playerColors = {player_colors_json};
                }}
                
                function getPlayerColor(playerName) {{
                    return playerColors[playerName.toUpperCase()] || '#FFD700';
                }}
                
                function updateRanking(groupId) {{
                    const ranking = rankingsByGroup[groupId] || [];
                    const tbody = document.getElementById('ranking-tbody');
                    tbody.innerHTML = '';
                    
                    ranking.forEach((playerData, index) => {{
                        const rank = index + 1;
                        const rankClass = rank <= 3 ? `rank-${{rank}}` : '';
                        const playerName = playerData[0];
                        const playerColor = getPlayerColor(playerName);
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="${{rankClass}}">#${{rank}}</td>
                            <td class="${{rankClass}}" style="color: ${{playerColor}}; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">${{playerName}}</td>
                            <td class="${{rankClass}}">${{playerData[1]}}</td>
                        `;
                        tbody.appendChild(row);
                    }});
                }}
                
                document.getElementById('group-select').addEventListener('change', function() {{
                    updateRanking(this.value);
                }});
            </script>
        </section>
        
        <section id="derniere-soiree">
            <h2>📅 Dernière Soirée de Jeu</h2>'''
    
    # Dernière soirée
    if latest_date and latest_sessions:
        html += f'<div class="session-date">Date: {format_date(latest_date)}</div>'
        
        for session in latest_sessions:
            players = parse_session_data(session)
            if players:
                html += f'''
            <div class="session-card">
                <div style="color: #ffd700; margin-bottom: 15px; font-size: 10px;">
                    Session: {session["id"]} - {session["date"]}
                </div>
                <table class="ranking-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Joueur</th>
                            <th>Session</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>'''
                
                # Trier les joueurs par victoires du jour
                sorted_players = sorted(players.items(), key=lambda x: x[1]['today'], reverse=True)
                for rank, (player, stats) in enumerate(sorted_players, 1):
                    player_color = get_player_color(player)
                    rank_class = f'rank-{rank}' if rank <= 3 else ''
                    html += f'''
                        <tr>
                            <td class="{rank_class}">#{rank}</td>
                            <td class="{rank_class}" style="color: {player_color}; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">{player}</td>
                            <td class="{rank_class}">{stats["today"]}</td>
                            <td class="{rank_class}">{stats["total"]}</td>
                        </tr>'''
                
                html += '''
                    </tbody>
                </table>
            </div>'''
    
    # Préparer toutes les sessions pour JavaScript
    all_sessions_data = []
    for date, date_sessions in sessions_by_date.items():
        for session in date_sessions:
            players = parse_session_data(session)
            if players:
                sorted_players = sorted(players.items(), key=lambda x: x[1]['today'], reverse=True)
                all_sessions_data.append({
                    'id': session['id'],
                    'date': session['date'],
                    'formatted_date': format_date(date),
                    'players': [{'name': p, 'today': s['today'], 'total': s['total']} for p, s in sorted_players]
                })
    
    # Convertir en JSON pour JavaScript
    sessions_json = json.dumps(all_sessions_data).replace('</', '<\\/')
    
    # Convertir les couleurs en JSON pour JavaScript
    player_colors_json = json.dumps(PLAYER_TO_COLOR).replace('</', '<\\/')
    
    # Bouton pour afficher toutes les sessions
    html += f'''
            <button id="toggle-all-sessions" class="toggle-button">
                ▼ Voir toutes les sessions
            </button>
            <div id="all-sessions-container" style="display: none;">
                <div id="all-sessions-list"></div>
                <div class="pagination-controls">
                    <button id="prev-page" class="pagination-button">◄ Précédent</button>
                    <span id="page-info" class="page-info">1</span>
                    <button id="next-page" class="pagination-button">Suivant ►</button>
                </div>
            </div>
            <script>
                const allSessions = {sessions_json};
                if (typeof playerColors === 'undefined') {{
                    var playerColors = {player_colors_json};
                }}
                let currentPage = 1;
                const sessionsPerPage = 10;
                const totalPages = Math.ceil(allSessions.length / sessionsPerPage);
                
                function getPlayerColor(playerName) {{
                    return playerColors[playerName.toUpperCase()] || '#FFD700';
                }}
                
                function renderSessions() {{
                    const container = document.getElementById('all-sessions-list');
                    container.innerHTML = '';
                    
                    const start = (currentPage - 1) * sessionsPerPage;
                    const end = start + sessionsPerPage;
                    const pageSessions = allSessions.slice(start, end);
                    
                    pageSessions.forEach(function(session) {{
                        const sessionCard = document.createElement('div');
                        sessionCard.className = 'session-card';
                        var tableRows = '';
                        session.players.forEach(function(p, index) {{
                            var rank = index + 1;
                            var rankClass = rank <= 3 ? 'rank-' + rank : '';
                            var color = getPlayerColor(p.name);
                            tableRows += '<tr><td class="' + rankClass + '">#' + rank + '</td><td class="' + rankClass + '" style="color: ' + color + '; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">' + p.name + '</td><td class="' + rankClass + '">' + p.today + '</td><td class="' + rankClass + '">' + p.total + '</td></tr>';
                        }});
                        sessionCard.innerHTML = '<div style="color: #ffd700; margin-bottom: 15px; font-size: 10px;">Session: ' + session.id + ' - ' + session.date + '</div><table class="ranking-table"><thead><tr><th>#</th><th>Joueur</th><th>Session</th><th>Total</th></tr></thead><tbody>' + tableRows + '</tbody></table>';
                        container.appendChild(sessionCard);
                    }});
                    
                    document.getElementById('page-info').textContent = `${{currentPage}} / ${{totalPages}}`;
                    document.getElementById('prev-page').disabled = currentPage === 1;
                    document.getElementById('next-page').disabled = currentPage === totalPages;
                }}
                
                // Attacher l'événement au bouton
                var toggleBtn = document.getElementById('toggle-all-sessions');
                if (toggleBtn) {{
                    toggleBtn.addEventListener('click', function() {{
                        var container = document.getElementById('all-sessions-container');
                        var isVisible = container.style.display !== 'none';
                        container.style.display = isVisible ? 'none' : 'block';
                        this.textContent = isVisible ? '▼ Voir toutes les sessions' : '▲ Masquer toutes les sessions';
                        
                        if (!isVisible && currentPage === 1) {{
                            renderSessions();
                        }}
                    }});
                }}
                
                document.getElementById('prev-page').addEventListener('click', function() {{
                    if (currentPage > 1) {{
                        currentPage--;
                        renderSessions();
                    }}
                }});
                
                document.getElementById('next-page').addEventListener('click', function() {{
                    if (currentPage < totalPages) {{
                        currentPage++;
                        renderSessions();
                    }}
                }});
            </script>
        </section>
    </div>
    
    <script>
        // Smooth scroll pour le menu
        document.querySelectorAll('nav a').forEach(function(anchor) {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                var target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }});
        }});
    </script>
</body>
</html>'''
    
    return html

@functions_framework.http
def display_stats(request):
    """HTTP Cloud Function qui affiche les statistiques depuis Google Sheets."""
    # Récupère les données de la sheet
    sheet_data = get_sheet_data()
    
    if isinstance(sheet_data, tuple) and sheet_data[0] is None:
        # Erreur lors de la récupération
        error_msg = sheet_data[1]
        error_html = '<html><head><meta charset="UTF-8"><title>Erreur</title>'
        error_html += '<style>body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #e8e8e8; }'
        error_html += 'pre { background-color: #2d1b3d; padding: 15px; border-radius: 5px; border: 2px solid #8b4513; }</style>'
        error_html += '</head><body><h1>Erreur</h1><p>Impossible de récupérer les données:</p><pre>' + error_msg + '</pre></body></html>'
        return error_html, 500
    
    # Génère la page HTML
    html_response = generate_html(sheet_data)
    return html_response
