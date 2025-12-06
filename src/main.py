"""Application Flask principale pour TowerStats."""

import functions_framework  # type: ignore
from flask import Flask, send_from_directory, render_template  # type: ignore
import io
import os

from .data_manager import SessionDataManager
from .stats_manager import SessionStatsManager
from .config import get_player_color

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
    
    # Préparer les données pour le template
    stats_manager = SessionStatsManager(sessions)
    template_data = stats_manager.prepare_template_data()
    
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
