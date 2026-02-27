"""Application Flask principale pour TowerStats."""

import functions_framework  # type: ignore
from flask import Flask, send_from_directory, render_template, request  # type: ignore
import io
import os
import random

from .data_manager import SessionDataManager
from .stats_manager import SessionStatsManager
from .config import get_player_color
from .messages_loader import load_win_messages


def _filter_sessions_by_session_id(sessions, session_id):
    """Filter sessions by session_id using data_manager helper."""
    return SessionDataManager.filter_sessions_by_session_id(sessions, session_id)

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

    if session_id:
        sessions = _filter_sessions_by_session_id(sessions, session_id)
        date_start = None
        date_end = None
    stats_manager = SessionStatsManager(sessions, date_start=date_start, date_end=date_end)
    template_data = stats_manager.prepare_template_data()
    template_data['selected_date_start'] = date_start
    template_data['selected_date_end'] = date_end
    template_data['selected_session_id'] = session_id
    template_data['win_messages_by_player'] = load_win_messages()

    if session_id:
        full_stats = SessionStatsManager(data_manager.get_sessions(), date_start=None, date_end=None)
        full_data = full_stats.prepare_template_data()
        template_data['all_sessions_data'] = full_data['all_sessions_data']
    
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
