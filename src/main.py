"""Flask app; display_stats is the Cloud Run / functions-framework entry."""

import functions_framework  # type: ignore
from flask import Flask, render_template, request, jsonify  # type: ignore
import io
import os
import random

from .data_manager import SessionDataManager
from .config import (
    get_player_color,
    get_player_portrait,
    PLAYER_TO_PORTRAIT,
)
from .page import build_page_context
from .live_session import get_live_session_payload

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_PATH, 'templates'),
            static_folder=os.path.join(BASE_PATH, 'static'))

app.jinja_env.globals['get_player_color'] = get_player_color
app.jinja_env.globals['get_player_portrait'] = get_player_portrait
app.jinja_env.globals['player_portraits'] = PLAYER_TO_PORTRAIT


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


def _load_sessions():
    """Fetch, correct and return the full session list."""
    data_manager = SessionDataManager()
    data_manager.load_all()
    return data_manager.get_sessions()


@app.route('/api/live')
def live_session_api():
    """JSON snapshot of the current live session, if any."""
    try:
        sessions = _load_sessions()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    entry = get_live_session_payload(sessions)
    return jsonify({'live': entry is not None, 'session': entry})


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def flask_display_stats(path):
    """Homepage: load sessions, assemble page context, render the template."""
    try:
        sessions = _load_sessions()
    except Exception as e:
        return render_template('error.html', error_message=str(e)), 500

    template_data, stats_manager = build_page_context(sessions, request.args)
    return render_template('index.html', **template_data, stats_manager=stats_manager)


# Cloud Run / functions-framework calls this with a Flask Request, not WSGI.
@functions_framework.http
def display_stats(request):
    """Adapt a functions-framework Request into Flask's WSGI dispatch."""
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
    for key, value in request.headers:
        environ[f'HTTP_{key.upper().replace("-", "_")}'] = value

    with app.request_context(environ):
        return app.full_dispatch_request()
