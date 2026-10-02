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


def pick_taglines(
    mashups: Optional[Sequence[str]] = None,
    slots: Sequence[str] = TAGLINE_SLOTS,
    rng: Optional[random.Random] = None,
) -> Dict[str, str]:
    """Pick a mashup per slot, without replacement when possible."""
    pool = list(mashups if mashups is not None else load_tagline_mashups())
    chooser = rng or random
    if not pool:
        return {slot: '' for slot in slots}
    if len(pool) >= len(slots):
        picked = chooser.sample(pool, k=len(slots))
    else:
        picked = [chooser.choice(pool) for _ in slots]
    return dict(zip(slots, picked))
