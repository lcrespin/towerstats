"""Season windows: bounds, current season, and HUD links."""

from datetime import date, datetime
from urllib.parse import urlencode

from .config import DEFAULT_GAME_MODE

CAREER_SEASON_ID = 'all'

SEASONS = [
    {
        'id': '1',
        'short': 'S1',
        'label': 'Saison 1',
        'start': '2025-06-01',
        'end': '2026-08-14',
    },
    {
        'id': '2',
        'short': 'S2',
        'label': 'Saison 2',
        'start': '2026-08-15',
        'end': None,
    },
]

CAREER_SEASON = {
    'id': CAREER_SEASON_ID,
    'short': '∞',
    'label': 'Carrière',
    'start': None,
    'end': None,
}

_BY_ID = {season['id']: season for season in SEASONS}
_BY_ID[CAREER_SEASON_ID] = CAREER_SEASON

_MONTHS_FR = {
    1: ('janv.', 'janvier'), 2: ('févr.', 'février'), 3: ('mars', 'mars'),
    4: ('avr.', 'avril'), 5: ('mai', 'mai'), 6: ('juin', 'juin'),
    7: ('juil.', 'juillet'), 8: ('août', 'août'), 9: ('sept.', 'septembre'),
    10: ('oct.', 'octobre'), 11: ('nov.', 'novembre'), 12: ('déc.', 'décembre'),
}


def get_season(season_id: str | None) -> dict | None:
    """Return a numbered season or the career entry."""
    return _BY_ID.get(season_id) if season_id else None


def season_date_bounds(season_id: str) -> tuple[str | None, str | None]:
    """Inclusive YYYY-MM-DD window; (None, None) for career."""
    season = get_season(season_id)
    if not season or season_id == CAREER_SEASON_ID:
        return None, None
    return season.get('start'), season.get('end')


def get_current_season_id(today: date | None = None) -> str:
    """Numbered season that contains today, else the latest one that has started."""
    today_str = (today or date.today()).isoformat()
    current = None
    last_started = None
    for season in SEASONS:
        start = season.get('start')
        end = season.get('end')
        if start and start <= today_str:
            last_started = season
            if not end or today_str <= end:
                current = season
    if current:
        return current['id']
    if last_started:
        return last_started['id']
    return SEASONS[0]['id']


def resolve_season_id(raw: str | None, today: date | None = None) -> str:
    """Query param to season id; missing/unknown values use the current season."""
    if raw in _BY_ID:
        return raw
    return get_current_season_id(today)


def is_season_live(season: dict, today: date | None = None) -> bool:
    """True for an open-ended numbered season that has already started."""
    if not season or season.get('id') == CAREER_SEASON_ID or season.get('end'):
        return False
    today_str = (today or date.today()).isoformat()
    start = season.get('start')
    return not start or start <= today_str


def season_spans_from_sessions(sessions: list) -> dict:
    """Actual first/last session dates per season id, from loaded sessions."""
    spans = {}
    for season in (*SEASONS, CAREER_SEASON):
        start, end = season_date_bounds(season['id'])
        dates = []
        for session in sessions:
            day = str(session.get('date') or '')[:10]
            if len(day) < 10:
                continue
            if start and day < start:
                continue
            if end and day > end:
                continue
            dates.append(day)
        spans[season['id']] = (min(dates), max(dates)) if dates else (None, None)
    return spans


def season_period_label(
    season: dict,
    first: str | None = None,
    last: str | None = None,
) -> str:
    """Caption under the active season pill, using real session dates when known."""
    if not season or season.get('id') == CAREER_SEASON_ID:
        return 'toutes les sessions'
    start = first or season.get('start')
    end = last or season.get('end')
    if season.get('end') and start and end:
        return (
            f"{_format_fr(start, month_year=True, long_month=True)} → "
            f"{_format_fr(end, month_year=True, long_month=True)}"
        )
    if start:
        return f"depuis le {_format_fr(start, long_month=True)}"
    return season.get('label', '')


def merge_date_bounds(
    season_start: str | None,
    season_end: str | None,
    user_start: str | None,
    user_end: str | None,
) -> tuple[str | None, str | None]:
    """Intersect the season window with optional user dates."""
    starts = [d for d in (season_start, user_start) if d]
    ends = [d for d in (season_end, user_end) if d]
    return (max(starts) if starts else None, min(ends) if ends else None)


def build_stats_url(
    season_id: str,
    current_season_id: str,
    game_mode: str | None = None,
    group_id: str | None = None,
) -> str:
    """GET url; omit season when it is the implicit current default."""
    query = {}
    if season_id != current_season_id:
        query['season'] = season_id
    if game_mode and game_mode != DEFAULT_GAME_MODE:
        query['gameMode'] = game_mode
    if group_id:
        query['groupId'] = group_id
    if not query:
        return '/'
    return '/?' + urlencode(query)


def build_season_switcher(
    selected_id: str,
    current_season_id: str,
    game_mode: str | None = None,
    group_id: str | None = None,
    today: date | None = None,
    spans: dict | None = None,
) -> list:
    """HUD pills for numbered seasons plus career."""
    spans = spans or {}
    items = []
    for season in (*SEASONS, CAREER_SEASON):
        first, last = spans.get(season['id'], (None, None))
        items.append({
            **season,
            'href': build_stats_url(season['id'], current_season_id, game_mode, group_id),
            'active': season['id'] == selected_id,
            'live': is_season_live(season, today),
            'period_label': season_period_label(season, first=first, last=last),
        })
    return items


def _format_fr(value: str, *, month_year: bool = False, long_month: bool = False) -> str:
    try:
        parsed = datetime.strptime(value[:10], '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return value
    short, long = _MONTHS_FR[parsed.month]
    month = long if long_month else short
    if month_year:
        return f"{month} {parsed.year}"
    return f"{parsed.day} {month} {parsed.year}"
