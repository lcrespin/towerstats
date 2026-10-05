"""Load and pick random section tagline mashups."""

import os
import random
from typing import Dict, List, Optional, Sequence

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MASHUPS_PATH = os.path.join(BASE_PATH, 'data', 'tagline_mashups.txt')

TAGLINE_SLOTS = (
    'records',
    'podium',
    'archives',
    'fleches',
    'kills',
    'parcours',
)

FAVORITE_COUNT = 40
FAVORITE_WEIGHT = 0.9


def load_tagline_mashups(path: Optional[str] = None) -> List[str]:
    """Return non-empty mashup lines from the taglines file."""
    filepath = path or DEFAULT_MASHUPS_PATH
    try:
        with open(filepath, encoding='utf-8') as handle:
            return [
                line.strip()
                for line in handle
                if line.strip() and not line.lstrip().startswith('#')
            ]
    except OSError:
        return []


def _pick_one(favorites: List[str], others: List[str], chooser) -> List[str]:
    """Return the group to draw from, favoring the first lines of the file."""
    if favorites and (not others or chooser.random() < FAVORITE_WEIGHT):
        return favorites
    return others


def pick_taglines(
    mashups: Optional[Sequence[str]] = None,
    slots: Sequence[str] = TAGLINE_SLOTS,
    rng: Optional[random.Random] = None,
    favorite_count: int = FAVORITE_COUNT,
) -> Dict[str, str]:
    """Pick a mashup per slot, without replacement when possible.

    The first `favorite_count` mashups are picked FAVORITE_WEIGHT of the time.
    """
    pool = list(mashups if mashups is not None else load_tagline_mashups())
    chooser = rng or random
    if not pool:
        return {slot: '' for slot in slots}
    favorites = pool[:favorite_count]
    others = pool[favorite_count:]
    unique = len(pool) >= len(slots)
    picked = []
    for _ in slots:
        group = _pick_one(favorites, others, chooser)
        index = chooser.randrange(len(group))
        picked.append(group.pop(index) if unique else group[index])
    return dict(zip(slots, picked))
