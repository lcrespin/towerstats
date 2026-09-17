import os
import sys
from datetime import date
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.seasons import (
    CAREER_SEASON_ID,
    get_current_season_id,
    resolve_season_id,
    season_date_bounds,
    merge_date_bounds,
    is_season_live,
    get_season,
    season_period_label,
    season_spans_from_sessions,
    build_stats_url,
    build_season_switcher,
)
from src.data_manager import SessionDataManager
from src.stats_manager import SessionStatsManager, leaderboard_career_deltas


def _session(day: str, wins: dict, group: str = 'ALICE-BOB', mode: str = 'HeadHunters'):
    return {
        'id': group,
        'date': day,
        'mode': mode,
        'data': {
            'todayWin': dict(wins),
            'totalWin': dict(wins),
            'date': f'{day}-20',
        },
    }


def test_current_season_id_around_august_15_2026():
    assert get_current_season_id(date(2026, 8, 14)) == '1'
    assert get_current_season_id(date(2026, 8, 15)) == '2'
    assert get_current_season_id(date(2026, 9, 17)) == '2'


def test_resolve_season_defaults_and_all():
    today = date(2026, 9, 17)
    assert resolve_season_id(None, today=today) == '2'
    assert resolve_season_id('', today=today) == '2'
    assert resolve_season_id('nope', today=today) == '2'
    assert resolve_season_id('1', today=today) == '1'
    assert resolve_season_id('all', today=today) == CAREER_SEASON_ID


def test_season_date_bounds():
    assert season_date_bounds('1') == ('2025-06-01', '2026-08-14')
    assert season_date_bounds('2') == ('2026-08-15', None)
    assert season_date_bounds('all') == (None, None)


def test_merge_date_bounds_clamps_user_range_to_season():
    start, end = merge_date_bounds('2026-08-15', None, '2025-01-01', '2026-09-01')
    assert start == '2026-08-15'
    assert end == '2026-09-01'
    start, end = merge_date_bounds(None, None, '2025-01-01', '2026-09-01')
    assert start == '2025-01-01'
    assert end == '2026-09-01'


def test_season_boundary_sessions_split_on_august_15():
    sessions = [
        _session('2026-08-14', {'ALICE': 3, 'BOB': 1}),
        _session('2026-08-15', {'ALICE': 1, 'BOB': 5}),
    ]
    s1_start, s1_end = season_date_bounds('1')
    s2_start, s2_end = season_date_bounds('2')
    season1 = SessionDataManager.filter_sessions_by_date(sessions, s1_start, s1_end)
    season2 = SessionDataManager.filter_sessions_by_date(sessions, s2_start, s2_end)
    career = SessionDataManager.filter_sessions_by_date(sessions, None, None)
    assert [s['date'] for s in season1] == ['2026-08-14']
    assert [s['date'] for s in season2] == ['2026-08-15']
    assert len(career) == 2


def test_window_totals_reset_per_season():
    sessions = [
        _session('2026-08-14', {'ALICE': 3, 'BOB': 1}),
        _session('2026-08-15', {'ALICE': 1, 'BOB': 5}),
        _session('2026-08-16', {'ALICE': 2, 'BOB': 2}),
    ]
    s2_start, s2_end = season_date_bounds('2')
    stats = SessionStatsManager(sessions, date_start=s2_start, date_end=s2_end)
    ctx = stats.prepare_template_data()
    by_date = {row['date']: {p['name']: p['total'] for p in row['players']} for row in ctx['all_sessions_data']}
    assert by_date['2026-08-15'] == {'ALICE': 1, 'BOB': 5}
    assert by_date['2026-08-16'] == {'ALICE': 3, 'BOB': 7}
    assert '2026-08-14' not in by_date


def test_season_elo_starts_from_1500():
    sessions = [
        _session('2026-08-14', {'ALICE': 10, 'BOB': 1}),
        _session('2026-08-15', {'ALICE': 1, 'BOB': 10}),
    ]
    s2_start, s2_end = season_date_bounds('2')
    stats = SessionStatsManager(sessions, date_start=s2_start, date_end=s2_end)
    evo = stats.get_elo_evolution()
    assert evo
    assert all(v == 1500.0 for v in evo[0]['elo_by_player'].values())


def test_career_delta_labels():
    season_data = {
        'best_percentage_players': ['ALICE'],
        'best_elo_players': ['ALICE'],
        'best_elo_match_players': ['BOB'],
        'best_players': ['ALICE'],
    }
    career_data = {
        'win_percentage_ranking': [(1, 'BOB', 10, 20, 50.0), (2, 'ALICE', 8, 20, 40.0)],
        'elo_ranking': [(1, 'ALICE', 1600.0)],
        'elo_match_ranking': [(1, 'ALICE', 1600.0), (3, 'BOB', 1400.0)],
        'rankings_by_group': {
            'ALICE-BOB': [(1, 'ALICE', 10), (2, 'BOB', 4)],
        },
    }
    deltas = leaderboard_career_deltas(season_data, career_data)
    assert deltas['win_pct']['ALICE'] == 'carrière : 2e'
    assert deltas['elo']['ALICE'] == 'même rang'
    assert deltas['elo_match']['BOB'] == 'carrière : 3e'
    assert deltas['group_score']['ALICE'] == 'même rang'


def test_switcher_omits_season_param_for_current():
    items = build_season_switcher('2', '2')
    by_id = {item['id']: item for item in items}
    assert by_id['2']['href'] == '/'
    assert by_id['2']['active'] is True
    assert by_id['2']['live'] is True
    assert by_id['1']['href'] == '/?season=1'
    assert by_id['all']['href'] == '/?season=all'
    assert 'LIVE' not in by_id['1'].get('short', '')
    assert is_season_live(get_season('1'), date(2026, 9, 17)) is False
    assert season_period_label(get_season('1')) == 'juin 2025 → août 2026'
    assert season_period_label(get_season('2')).startswith('depuis le 15 août')
    assert build_stats_url('2', '2') == '/'


def test_period_label_uses_actual_session_dates():
    s1 = get_season('1')
    s2 = get_season('2')
    assert season_period_label(s1, first='2025-06-03', last='2026-07-18') == (
        'juin 2025 → juillet 2026'
    )
    assert season_period_label(s2, first='2026-08-26', last='2026-09-17') == (
        'depuis le 26 août 2026'
    )
    sessions = [
        _session('2025-05-31', {'ALICE': 1, 'BOB': 1}),
        _session('2025-06-03', {'ALICE': 1, 'BOB': 1}),
        _session('2026-07-18', {'ALICE': 1, 'BOB': 1}),
        _session('2026-08-26', {'ALICE': 1, 'BOB': 1}),
    ]
    spans = season_spans_from_sessions(sessions)
    assert spans['1'] == ('2025-06-03', '2026-07-18')
    assert spans['2'] == ('2026-08-26', '2026-08-26')
    items = build_season_switcher('2', '2', spans=spans)
    by_id = {item['id']: item for item in items}
    assert by_id['1']['period_label'] == 'juin 2025 → juillet 2026'
    assert by_id['2']['period_label'] == 'depuis le 26 août 2026'


SYNTHETIC_SESSIONS = [
    _session('2025-05-31', {'ALICE': 2, 'BOB': 2}),
    _session('2025-06-03', {'ALICE': 4, 'BOB': 1}),
    _session('2026-08-14', {'ALICE': 3, 'BOB': 1}),
    _session('2026-08-26', {'ALICE': 1, 'BOB': 5}),
]


def _fake_load_all(self):
    self.sessions = list(SYNTHETIC_SESSIONS)


def _get_client():
    from src.main import app
    app.config['TESTING'] = True
    return app.test_client()


@patch('src.main.load_win_messages', return_value={})
@patch('src.main.SessionDataManager.load_all', _fake_load_all)
def test_default_route_uses_current_season(_messages):
    client = _get_client()
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'season-pill is-active' in html
    assert 'href="/?season=1"' in html
    assert 'href="/?season=all"' in html
    assert 'Saison 2' in html
    assert 'compteurs à zéro' in html
    assert 'Filtres appliqués' not in html
    assert 'name="season"' not in html
    assert 'Session: ALICE-BOB - 2026-08-14' not in html
    assert 'Session: ALICE-BOB - 2026-08-26' in html
    assert 'depuis le 26 août 2026' in html


@patch('src.main.load_win_messages', return_value={})
@patch('src.main.SessionDataManager.load_all', _fake_load_all)
def test_season_all_route_is_career(_messages):
    client = _get_client()
    response = client.get('/?season=all')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'name="season" value="all"' in html
    assert 'compteurs à zéro' not in html
    assert '2025-05-31' in html
    assert '2025-06-03' in html
    assert '2026-08-14' in html
    assert '2026-08-26' in html


@patch('src.main.load_win_messages', return_value={})
@patch('src.main.SessionDataManager.load_all', _fake_load_all)
def test_season_1_route_stops_before_august_15(_messages):
    client = _get_client()
    response = client.get('/?season=1')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'name="season" value="1"' in html
    assert 'min="2025-06-01"' in html
    assert 'max="2026-08-14"' in html
    assert 'close' in html
    assert 'Session: ALICE-BOB - 2026-08-14' in html
    assert 'Session: ALICE-BOB - 2026-08-26' not in html
    assert 'Session: ALICE-BOB - 2025-05-31' not in html
    assert '2025-06-03' in html
    assert 'Depuis le 03/06/25' in html
    assert 'juin 2025 → août 2026' in html
    assert 'carrière :' in html or 'même rang' in html
