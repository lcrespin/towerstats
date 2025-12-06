"""Point d'entrée pour la compatibilité avec functions-framework et Gunicorn."""

# Réexport de l'app Flask depuis src/main
from src.main import app, display_stats

# Pour Gunicorn: main:app
# Pour functions-framework: main:display_stats

