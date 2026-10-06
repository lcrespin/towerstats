"""Assemble the stats page context from loaded sessions and query args."""

from .config import (
    DEFAULT_GAME_MODE,
    GAME_MODES,
    game_mode_label,
    is_valid_game_mode,
    normalize_game_mode,
)
from .data_manager import SessionDataManager
from .live_session import get_live_session_payload
from .messages import load_win_messages
from .seasons import (
    CAREER_SEASON_ID,
    build_season_switcher,
    build_stats_url,
    get_current_season_id,
    get_season,
    is_season_live,
    merge_date_bounds,
    resolve_season_id,
    season_date_bounds,
    season_period_label,
    season_spans_from_sessions,
)
from .stats_manager import SessionStatsManager, leaderboard_career_deltas
from .taglines import pick_header_subtitle, pick_taglines


def _season_banner(selected_season, season_meta, template_data):
    if selected_season == CAREER_SEASON_ID:
        return None
    period = template_data.get('season_period_label')
    if is_season_live(season_meta):
        n = template_data.get('total_sessions') or 0
        session_word = 'session' if n == 1 else 'sessions'
        return (
            f"{season_meta['label']} · {period} · "
            f"{n} {session_word} · compteurs à zéro"
        )
    champs = template_data.get('best_percentage_players') or []
    if champs:
        return (
            f"{season_meta['label']} · close · champion % victoires : {', '.join(champs)}"
        )
    return f"{season_meta['label']} · close · {period}"


def build_page_context(all_sessions, args) -> tuple:
    """Filter sessions and build the homepage template dict plus its stats manager."""
    date_start = args.get('dateStart') or None
    date_end = args.get('dateEnd') or None
    session_id = args.get('sessionId') or None
    group_id = args.get('groupId') or None
    raw_game_mode = args.get('gameMode') or DEFAULT_GAME_MODE
    game_mode = (
        normalize_game_mode(raw_game_mode)
        if is_valid_game_mode(raw_game_mode)
        else DEFAULT_GAME_MODE
    )
    current_season_id = get_current_season_id()
    selected_season = resolve_season_id(args.get('season'))
    season_meta = get_season(selected_season) or get_season(current_season_id)
    season_start, season_end = season_date_bounds(selected_season)
    effective_start, effective_end = merge_date_bounds(
        season_start, season_end, date_start, date_end
    )

    sessions = SessionDataManager.filter_sessions_by_game_mode(all_sessions, game_mode)
    season_spans = season_spans_from_sessions(sessions)
    season_sessions = SessionDataManager.filter_sessions_by_date(
        sessions, season_start, season_end
    )
    all_groups_for_filter = SessionDataManager.sorted_group_ids_by_session_count(
        season_sessions
    )

    stats_date_start, stats_date_end = effective_start, effective_end
    if session_id:
        sessions = SessionDataManager.filter_sessions_by_session_id(sessions, session_id)
        stats_date_start = None
        stats_date_end = None
    elif group_id:
        sessions = SessionDataManager.filter_sessions_by_group_id(sessions, group_id)

    stats_manager = SessionStatsManager(
        sessions, date_start=stats_date_start, date_end=stats_date_end
    )
    template_data = stats_manager.prepare_template_data()
    first_session, last_session = season_spans.get(selected_season, (None, None))
    template_data.update({
        'selected_date_start': date_start,
        'selected_date_end': date_end,
        'selected_session_id': session_id,
        'selected_group_id': group_id,
        'selected_game_mode': game_mode,
        'game_modes': GAME_MODES,
        'default_game_mode': DEFAULT_GAME_MODE,
        'selected_game_mode_label': game_mode_label(game_mode),
        'all_groups_for_filter': all_groups_for_filter,
        'win_messages_by_player': load_win_messages(),
        'taglines': pick_taglines(),
        'header_subtitle': pick_header_subtitle(),
        'selected_season': selected_season,
        'current_season_id': current_season_id,
        'is_career_view': selected_season == CAREER_SEASON_ID,
        'season_switcher': build_season_switcher(
            selected_season, current_season_id, game_mode, group_id, spans=season_spans
        ),
        'season_period_label': season_period_label(
            season_meta, first=first_session, last=last_session
        ),
        'season_picker_min': season_start,
        'season_picker_max': season_end,
        'reset_filters_url': build_stats_url(current_season_id, current_season_id),
        'live_session': get_live_session_payload(all_sessions),
    })
    template_data['season_banner'] = _season_banner(
        selected_season, season_meta, template_data
    )

    if session_id or group_id or date_start or date_end:
        # Archives dropdown lists every session in the season, not the filtered subset.
        dropdown_stats = SessionStatsManager(season_sessions, date_start=None, date_end=None)
        template_data['all_sessions_data'] = dropdown_stats.session_entries()

    template_data['career_deltas'] = None
    if selected_season != CAREER_SEASON_ID:
        career_sessions = SessionDataManager.filter_sessions_by_game_mode(
            all_sessions, game_mode
        )
        if group_id and not session_id:
            career_sessions = SessionDataManager.filter_sessions_by_group_id(
                career_sessions, group_id
            )
        career_stats = SessionStatsManager(career_sessions, date_start=None, date_end=None)
        template_data['career_deltas'] = leaderboard_career_deltas(
            template_data, career_stats.leaderboard_rankings()
        )

    return template_data, stats_manager
