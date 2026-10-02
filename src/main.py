"""Application Flask principale pour TowerStats."""

import functions_framework  # type: ignore
from flask import Flask, send_from_directory, render_template, request  # type: ignore
import io
import os
import random

from .data_manager import SessionDataManager
from .stats_manager import SessionStatsManager, leaderboard_career_deltas
from .config import (
    get_player_color,
    DEFAULT_GAME_MODE,
    GAME_MODES,
    normalize_game_mode,
    is_valid_game_mode,
    game_mode_label,
)
from .seasons import (
    CAREER_SEASON_ID,
    get_current_season_id,
    resolve_season_id,
    get_season,
    season_date_bounds,
    is_season_live,
    season_period_label,
    season_spans_from_sessions,
    merge_date_bounds,
    build_stats_url,
    build_season_switcher,
)
from .messages_loader import load_win_messages
from .taglines import pick_taglines


def _filter_sessions_by_session_id(sessions, session_id):
    """Filter sessions by session_id using data_manager helper."""
    return SessionDataManager.filter_sessions_by_session_id(sessions, session_id)


def _filter_sessions_by_group_id(sessions, group_id):
    """Keep only sessions whose id equals group_id."""
    if not group_id or not group_id.strip():
        return sessions
    return [s for s in sessions if s.get('id') == group_id]

# Chemin vers la racine du projet (un niveau au-dessus de src/)
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Créer l'application Flask avec les chemins vers templates et static à la racine
app = Flask(__name__, 
            template_folder=os.path.join(BASE_PATH, 'templates'),
            static_folder=os.path.join(BASE_PATH, 'static'))

# Ajouter get_player_color comme fonction globale pour les templates
app.jinja_env.globals['get_player_color'] = get_player_color

# Ajouter un filtre enumerate pour Jinja2
@app.template_filter('enumerate')
def enumerate_filter(iterable, start=0):
    """Filtre Jinja2 pour enumerate."""
    return enumerate(iterable, start)


@app.template_filter('random_choice')
def random_choice_filter(seq):
    """Return a random item from the sequence, or '' if empty/missing."""
    if not seq:
        return ''
    return random.choice(seq)


@app.template_filter('capitalize_first')
def capitalize_first_filter(s):
    """Capitalize the first character of the string; leave the rest unchanged."""
    if not s:
        return ''
    return s[0].upper() + s[1:]


@app.route('/images/<filename>')
def serve_image(filename):
    """Route pour servir les images statiques."""
    images_dir = os.path.join(BASE_PATH, 'images')
    return send_from_directory(images_dir, filename)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def flask_display_stats(path):
    """Route principale qui affiche les statistiques depuis Google Sheets."""
    # Récupère les données de la sheet
    try:
        data_manager = SessionDataManager()
        data_manager.load_all()
        sessions = data_manager.get_sessions()
    except Exception as e:
        # Erreur lors de la récupération
        return render_template('error.html', error_message=str(e)), 500
    
    date_start = request.args.get('dateStart') or None
    date_end = request.args.get('dateEnd') or None
    session_id = request.args.get('sessionId') or None
    group_id = request.args.get('groupId') or None
    raw_game_mode = request.args.get('gameMode') or DEFAULT_GAME_MODE
    game_mode = normalize_game_mode(raw_game_mode) if is_valid_game_mode(raw_game_mode) else DEFAULT_GAME_MODE
    current_season_id = get_current_season_id()
    selected_season = resolve_season_id(request.args.get('season'))
    season_meta = get_season(selected_season) or get_season(current_season_id)
    season_start, season_end = season_date_bounds(selected_season)
    effective_start, effective_end = merge_date_bounds(
        season_start, season_end, date_start, date_end
    )

    all_sessions = sessions
    sessions = SessionDataManager.filter_sessions_by_game_mode(all_sessions, game_mode)
    season_spans = season_spans_from_sessions(sessions)
    season_sessions = SessionDataManager.filter_sessions_by_date(
        sessions, season_start, season_end
    )
    all_groups_for_filter = SessionDataManager.sorted_group_ids_by_session_count(season_sessions)

    stats_date_start, stats_date_end = effective_start, effective_end
    if session_id:
        sessions = _filter_sessions_by_session_id(sessions, session_id)
        stats_date_start = None
        stats_date_end = None
    elif group_id:
        sessions = _filter_sessions_by_group_id(sessions, group_id)

    stats_manager = SessionStatsManager(
        sessions, date_start=stats_date_start, date_end=stats_date_end
    )
    template_data = stats_manager.prepare_template_data()
    template_data['selected_date_start'] = date_start
    template_data['selected_date_end'] = date_end
    template_data['selected_session_id'] = session_id
    template_data['selected_group_id'] = group_id
    template_data['selected_game_mode'] = game_mode
    template_data['game_modes'] = GAME_MODES
    template_data['default_game_mode'] = DEFAULT_GAME_MODE
    template_data['selected_game_mode_label'] = game_mode_label(game_mode)
    template_data['all_groups_for_filter'] = all_groups_for_filter
    template_data['win_messages_by_player'] = load_win_messages()
    template_data['taglines'] = pick_taglines()
    template_data['selected_season'] = selected_season
    template_data['current_season_id'] = current_season_id
    template_data['is_career_view'] = selected_season == CAREER_SEASON_ID
    template_data['season_switcher'] = build_season_switcher(
        selected_season, current_season_id, game_mode, group_id, spans=season_spans
    )
    first_session, last_session = season_spans.get(selected_season, (None, None))
    template_data['season_period_label'] = season_period_label(
        season_meta, first=first_session, last=last_session
    )
    template_data['season_picker_min'] = season_start
    template_data['season_picker_max'] = season_end
    template_data['reset_filters_url'] = build_stats_url(
        current_season_id, current_season_id
    )

    if selected_season == CAREER_SEASON_ID:
        template_data['season_banner'] = None
    elif is_season_live(season_meta):
        n = template_data.get('total_sessions') or 0
        session_word = 'session' if n == 1 else 'sessions'
        template_data['season_banner'] = (
            f"{season_meta['label']} · {template_data['season_period_label']} · "
            f"{n} {session_word} · compteurs à zéro"
        )
    else:
        champs = template_data.get('best_percentage_players') or []
        if champs:
            template_data['season_banner'] = (
                f"{season_meta['label']} · close · champion % victoires : {', '.join(champs)}"
            )
        else:
            template_data['season_banner'] = (
                f"{season_meta['label']} · close · {template_data['season_period_label']}"
            )

    season_dropdown_needed = bool(session_id or group_id or date_start or date_end)
    if season_dropdown_needed:
        season_dropdown_stats = SessionStatsManager(
            season_sessions, date_start=None, date_end=None
        )
        template_data['all_sessions_data'] = season_dropdown_stats.prepare_template_data()[
            'all_sessions_data'
        ]

    template_data['career_deltas'] = None
    if selected_season != CAREER_SEASON_ID:
        career_sessions = SessionDataManager.filter_sessions_by_game_mode(
            all_sessions, game_mode
        )
        if group_id and not session_id:
            career_sessions = _filter_sessions_by_group_id(career_sessions, group_id)
        career_stats = SessionStatsManager(career_sessions, date_start=None, date_end=None)
        template_data['career_deltas'] = leaderboard_career_deltas(
            template_data, career_stats.prepare_template_data()
        )
    
    # Charger les fichiers statiques
    def load_static_file(filename):
        """Charge un fichier statique et retourne son contenu."""
        filepath = os.path.join(BASE_PATH, 'static', filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return ''
    
    css_content = load_static_file('css/style.css')
    js_content = load_static_file('js/app.js')
    
    # Rendre le template avec les données
    return render_template('index.html', **template_data, stats_manager=stats_manager, 
                          css_content=css_content, js_content=js_content)


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
