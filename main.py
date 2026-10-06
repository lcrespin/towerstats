"""Root WSGI entry: Gunicorn uses main:app, functions-framework uses main:display_stats."""

from src.main import app, display_stats

