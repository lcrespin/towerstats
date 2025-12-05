import functions_framework  # type: ignore
from flask import Flask, send_from_directory, request as flask_request  # type: ignore
import urllib.request
import csv
import io
import json
import os
from datetime import datetime
from collections import defaultdict

# Créer l'application Flask
app = Flask(__name__)

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

def get_win_percentage_ranking(sessions):
    """Calcule le classement par pourcentage de victoires.
    
    Returns:
        list: Liste de tuples (joueur, victoires, parties_jouees, pourcentage) triée par pourcentage décroissant
    """
    player_victories = defaultdict(int)
    player_games_played = defaultdict(int)
    
    for session in sessions:
        players = parse_session_data(session)
        if not players:
            continue
        
        # Calculer le nombre total de parties dans cette session
        total_games_in_session = sum(stats['today'] for stats in players.values())
        
        # Pour chaque joueur de la session
        for player, stats in players.items():
            # Ajouter les victoires
            player_victories[player] += stats['today']
            # Ajouter le nombre de parties jouées (total de la session)
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

def get_medal(rank):
    """Retourne la médaille correspondant au rang."""
    if rank == 1:
        return '🥇'
    elif rank == 2:
        return '🥈'
    elif rank == 3:
        return '🥉'
    return ''

def load_static_file(filepath, required=False):
    """Charge un fichier statique (CSS, JS ou HTML) et retourne son contenu.
    
    Args:
        filepath: Chemin vers le fichier à charger
        required: Si True, lève une exception si le fichier ne peut pas être chargé.
                 Si False, retourne une chaîne vide en cas d'erreur.
    
    Returns:
        Contenu du fichier ou chaîne vide si non requis et erreur.
    
    Raises:
        FileNotFoundError: Si required=True et le fichier n'existe pas.
        IOError: Si required=True et une erreur de lecture survient.
    """
    try:
        # Essayer d'abord depuis le répertoire courant
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, filepath)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        # Si pas trouvé, essayer directement
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        # Fichier non trouvé
        if required:
            raise FileNotFoundError(f"Required file not found: {filepath}")
        print(f"Warning: Could not load {filepath}: File not found")
        return ''
    except (FileNotFoundError, IOError) as e:
        if required:
            raise
        print(f"Warning: Could not load {filepath}: {e}")
        return ''
    except Exception as e:
        if required:
            raise IOError(f"Error loading {filepath}: {e}") from e
        print(f"Warning: Could not load {filepath}: {e}")
        return ''

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
    
    # Charger le template HTML (requis - lève une exception si échec)
    try:
        html_template = load_static_file('templates/index.html', required=True)
    except (FileNotFoundError, IOError) as e:
        # Retourner une page d'erreur HTML si le template ne peut pas être chargé
        error_html = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erreur - TowerStats</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: #e8e8e8;
            padding: 40px;
            text-align: center;
        }
        h1 { color: #ff4444; }
        pre {
            background: #2d1b3d;
            padding: 20px;
            border-radius: 5px;
            border: 2px solid #8b4513;
            text-align: left;
            max-width: 800px;
            margin: 20px auto;
        }
    </style>
</head>
<body>
    <h1>❌ Erreur de Configuration</h1>
    <p>Le template HTML n'a pas pu être chargé.</p>
    <pre>''' + str(e) + '''</pre>
    <p>Vérifiez que le fichier <code>templates/index.html</code> existe et est accessible.</p>
</body>
</html>'''
        return error_html
    
    # Charger les fichiers statiques (optionnels - chaîne vide si échec)
    css_content = load_static_file('static/css/style.css', required=False)
    js_content = load_static_file('static/js/app.js', required=False)
    
    # Générer les cartes de statistiques
    stats_cards = []
    
    # Meilleur joueur (parmi tous les groupes) - en premier
    all_player_totals = defaultdict(int)
    for ranking in rankings_by_group.values():
        for player, total in ranking:
            if total > all_player_totals[player]:
                all_player_totals[player] = total
    
    if all_player_totals:
        best_player = max(all_player_totals.items(), key=lambda x: x[1])
        best_player_name, best_score = best_player
        stats_cards.append(f'''
                <div class="stat-card">
                    <div class="stat-label">Meilleur Score Global</div>
                    <div class="stat-value">{best_score}</div>
                    <div class="stat-label">{best_player_name}</div>
                </div>''')
    
    # Meilleur pourcentage de victoires - en deuxième position
    win_percentage_ranking = get_win_percentage_ranking(sessions)
    if win_percentage_ranking:
        best_percentage_player, victories, games_played, win_percentage = win_percentage_ranking[0]
        stats_cards.append(f'''
                <div class="stat-card">
                    <div class="stat-label">Meilleur % Victoires</div>
                    <div class="stat-value">{win_percentage:.1f}%</div>
                    <div class="stat-label">{best_percentage_player}</div>
                </div>''')
    
    # Joueurs Uniques et Total Sessions
    stats_cards.append(f'''
                <div class="stat-card">
                    <div class="stat-label">Joueurs Uniques</div>
                    <div class="stat-value">{len(unique_players)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Sessions</div>
                    <div class="stat-value">{total_sessions}</div>
                </div>''')
    
    stats_cards_html = ''.join(stats_cards)
    
    # Générer les options du menu déroulant
    group_options = []
    for group_id in sorted_groups:
        selected = 'selected' if group_id == default_group else ''
        best_score = get_best_score(group_id)
        group_options.append(f'                    <option value="{group_id}" {selected}>{group_id} (Meilleur: {best_score})</option>')
    group_options_html = '\n'.join(group_options)
    
    # Calculer le classement par pourcentage de victoires
    win_percentage_ranking = get_win_percentage_ranking(sessions)
    
    # Générer les lignes du tableau de pourcentage de victoires
    win_percentage_rows = []
    for rank, (player, victories, games_played, win_percentage) in enumerate(win_percentage_ranking, 1):
        medal = get_medal(rank)
        rank_class = f'rank-{rank}' if rank <= 3 else ''
        player_color = get_player_color(player)
        win_percentage_rows.append(f'''
                    <tr>
                        <td class="{rank_class}" style="color: {player_color}; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">{medal} {player}</td>
                        <td class="{rank_class}">{victories}/{games_played}</td>
                        <td class="{rank_class}">{win_percentage:.2f}%</td>
                    </tr>''')
    win_percentage_rows_html = ''.join(win_percentage_rows)
    
    # Générer les lignes du classement
    ranking_rows = []
    for rank, (player, total) in enumerate(default_ranking, 1):
        medal = get_medal(rank)
        rank_class = f'rank-{rank}' if rank <= 3 else ''
        player_color = get_player_color(player)
        ranking_rows.append(f'''
                    <tr>
                        <td class="{rank_class}" style="color: {player_color}; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">{medal} {player}</td>
                        <td class="{rank_class}">{total}</td>
                    </tr>''')
    ranking_rows_html = ''.join(ranking_rows)
    
    # Générer les sessions de la dernière session
    latest_sessions_html = ''
    if latest_date and latest_sessions:
        latest_sessions_html += f'<div class="session-date">Date: {format_date(latest_date)}</div>'
        
        for session in latest_sessions:
            players = parse_session_data(session)
            if players:
                session_rows = []
                sorted_players = sorted(players.items(), key=lambda x: x[1]['today'], reverse=True)
                for rank, (player, stats) in enumerate(sorted_players, 1):
                    medal = get_medal(rank)
                    player_color = get_player_color(player)
                    rank_class = f'rank-{rank}' if rank <= 3 else ''
                    session_rows.append(f'''
                        <tr>
                            <td class="{rank_class}" style="color: {player_color}; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">{medal} {player}</td>
                            <td class="{rank_class}">{stats["today"]}</td>
                            <td class="{rank_class}">{stats["total"]}</td>
                        </tr>''')
                
                latest_sessions_html += f'''
            <div class="session-card">
                <div style="color: #ffd700; margin-bottom: 15px; font-size: 10px;">
                    Session: {session["id"]} - {session["date"]}
                </div>
                <table class="ranking-table">
                    <thead>
                        <tr>
                            <th>Joueur</th>
                            <th>Session</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
{''.join(session_rows)}
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
    rankings_json = json.dumps(rankings_by_group).replace('</', '<\\/')
    player_colors_json = json.dumps(PLAYER_TO_COLOR).replace('</', '<\\/')
    sessions_json = json.dumps(all_sessions_data).replace('</', '<\\/')
    
    # Remplacer les placeholders dans le template
    html = html_template.replace('{CSS_CONTENT}', css_content)
    html = html.replace('{JS_CONTENT}', js_content)
    html = html.replace('{STATS_CARDS}', stats_cards_html)
    html = html.replace('{DATE_DEBUT}', date_debut_formatted)
    html = html.replace('{DATE_FIN}', date_fin_formatted)
    html = html.replace('{GROUP_OPTIONS}', group_options_html)
    html = html.replace('{RANKING_ROWS}', ranking_rows_html)
    html = html.replace('{WIN_PERCENTAGE_ROWS}', win_percentage_rows_html)
    html = html.replace('{LATEST_SESSIONS}', latest_sessions_html)
    html = html.replace('{RANKINGS_JSON}', rankings_json)
    html = html.replace('{PLAYER_COLORS_JSON}', player_colors_json)
    html = html.replace('{SESSIONS_JSON}', sessions_json)
    
    return html

@app.route('/images/<filename>')
def serve_image(filename):
    """Route pour servir les images statiques."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(base_path, 'images')
    return send_from_directory(images_dir, filename)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def flask_display_stats(path):
    """Route principale qui affiche les statistiques depuis Google Sheets."""
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

# Wrapper pour functions-framework
@functions_framework.http
def display_stats(request):
    """Handler pour functions-framework qui délègue à Flask."""
    # functions-framework passe un objet Flask Request
    # On utilise directement Flask en créant un contexte WSGI
    # Construire l'environ WSGI depuis l'objet request Flask
    environ = {
        'REQUEST_METHOD': request.method,
        'PATH_INFO': request.path,
        'QUERY_STRING': request.query_string.decode() if request.query_string else '',
        'wsgi.input': io.BytesIO(request.get_data()),
        'CONTENT_LENGTH': str(len(request.get_data())),
        'CONTENT_TYPE': request.content_type or '',
        'SERVER_NAME': request.host.split(':')[0] if request.host else 'localhost',
        'SERVER_PORT': request.host.split(':')[1] if ':' in request.host else '80',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': request.scheme,
        'wsgi.errors': None,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }
    # Ajouter les headers HTTP
    for key, value in request.headers:
        environ[f'HTTP_{key.upper().replace("-", "_")}'] = value
    
    # Utiliser Flask avec le contexte WSGI
    with app.request_context(environ):
        return app.full_dispatch_request()

# L'objet app Flask est déjà WSGI-compatible
# Gunicorn peut l'utiliser directement via main:app
