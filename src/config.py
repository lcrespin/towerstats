"""Configuration et constantes pour TowerStats."""

# URL publique de la Google Sheet en CSV
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTTikaqWVWPY9RNMASh76zdipiwF5XwwAq-TNgUDSVs6uU10BRvaATt8GidTikAvL6E1Jh6drNG04wd/pub?gid=0&single=true&output=csv'

# Game modes (v4+); missing mode in source data defaults to HeadHunters
DEFAULT_GAME_MODE = 'HeadHunters'

GAME_MODES = {
    'HeadHunters': {'label': 'Head Hunters'},
    '13': {'label': 'Respawn 3'},
}


def normalize_game_mode(raw: str | None) -> str:
    """Return a known game mode id; default to HeadHunters for missing/unknown values."""
    if raw and raw in GAME_MODES:
        return raw
    return DEFAULT_GAME_MODE


def is_valid_game_mode(mode: str) -> bool:
    """True if mode is a configured game mode id."""
    return mode in GAME_MODES


def game_mode_label(mode: str) -> str:
    """Display label for a game mode id."""
    return GAME_MODES.get(mode, GAME_MODES[DEFAULT_GAME_MODE])['label']

# Win/lose messages sheet (columns: NOMwin, NOMlose per player)
MESSAGES_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTyNKz-IP1qJHMNpW8SFpvYOy_IXA9uDbN8FxZEOZRAR1kbP1ABb35ZKnhvB-0MJ_-d96ddIqER38fR/pub?gid=0&single=true&output=csv'

# Mapping des couleurs pour l'affichage
PLAYER_TO_COLOR = {
    'MEHDI': '#FFC0CB',
    'JULIEN': '#90EE90',
    'LOUIS': '#FFA500',
    'ALEX': '#FFFF00',
    'ERIC': '#9370DB',
    'BENOIT': '#4169E1',
    'DAVID': '#FFFFFF',
    'ZAYA': '#FF3333',
}

def get_player_color(player_name):
    """Retourne la couleur d'un joueur pour l'affichage."""
    return PLAYER_TO_COLOR.get(player_name.upper(), '#FFD700')  # Par défaut: or

