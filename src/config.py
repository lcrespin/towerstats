"""Configuration et constantes pour TowerStats."""

# URL publique de la Google Sheet en CSV
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQE3KfSAHXOp3hNFuR5oq_lgtEdEUzJ6YiRcov5gDSdgVSvuJDuy6sFslSC76qIa3CPjYSl9sTwQUrO/pub?output=csv'

# Source de vérité : configuration des couleurs
# Format: couleur (nom) -> (joueur, code_hex)
COLOR_CONFIG = {
    'pink': ('MEHDI', '#FFC0CB'),
    'green': ('JULIEN', '#90EE90'),
    'orange': ('LOUIS', '#FFA500'),
    'yellow': ('ALEX', '#FFFF00'),
    'purple': ('ERIC', '#9370DB'),
    'blue2': ('BENOIT', '#4169E1'),
    'white': ('DAVID', '#FFFFFF'),
    'blue': (None, None),
    'red': (None, None),
}

# Génération des mappings à partir de la source de vérité
COLOR_TO_PLAYER = {color: player for color, (player, _) in COLOR_CONFIG.items()}
PLAYER_TO_COLOR = {player: hex_color for color, (player, hex_color) in COLOR_CONFIG.items() if player}
PLAYER_TO_COLOR_KEY = {player: color for color, (player, _) in COLOR_CONFIG.items() if player}

# Dates à ignorer pour les sessions v1 (avant minuit)
# Ces dates correspondent aux sessions qui ont été fusionnées avec la session du jour suivant
V1_DATES_TO_IGNORE = {
    '2025-06-02',
    '2025-06-04',
    '2025-09-11',
    '2025-09-16',
    '2025-10-01',
    '2025-10-15',
}

def get_player_color(player_name):
    """Retourne la couleur d'un joueur pour l'affichage."""
    return PLAYER_TO_COLOR.get(player_name.upper(), '#FFD700')  # Par défaut: or

