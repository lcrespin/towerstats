"""Load win/lose messages from the messages CSV sheet."""

import csv
import io
import urllib.request
from typing import Dict, List

from .config import MESSAGES_CSV_URL

# Optional: map CSV column names to app player names (e.g. ALEXANDRE -> ALEX)
PLAYER_NAME_ALIASES = {'ALEXANDRE': 'ALEX'}


def load_win_messages(csv_url: str = None) -> Dict[str, List[str]]:
    """
    Fetch the messages CSV and return win messages per player.
    Keys are player names (e.g. DAVID, ERIC); values are non-empty message strings.
    On error returns {}.
    """
    url = csv_url or MESSAGES_CSV_URL
    result = {}
    try:
        with urllib.request.urlopen(url) as response:
            csv_data = response.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_data))
        if not reader.fieldnames:
            return result
        win_cols = [c for c in reader.fieldnames if c.endswith('win') and len(c) > 3]
        for col in win_cols:
            player = col[:-3].strip()
            if not player:
                continue
            player = PLAYER_NAME_ALIASES.get(player, player)
            result[player] = []
        rows = list(reader)
        for col in win_cols:
            player = col[:-3].strip()
            if not player:
                continue
            player = PLAYER_NAME_ALIASES.get(player, player)
            for row in rows:
                val = (row.get(col) or '').strip()
                if val:
                    result[player].append(val)
    except Exception:
        return {}
    return result
