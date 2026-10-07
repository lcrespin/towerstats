import io
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import data_manager
from src.data_manager import SessionDataManager

CSV = 'id,date,value\nERIC-LOUIS,2026-09-01,"{""todayWin"": {""ERIC"": 2, ""LOUIS"": 1}, ""date"": ""2026-09-01-22""}"\n'


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _fake_urlopen(calls):
    def urlopen(_url):
        calls.append(1)
        return _Response(CSV.encode("utf-8"))
    return urlopen


def test_remote_csv_is_cached_between_fetches():
    calls = []
    data_manager._CSV_CACHE.clear()
    with patch("src.data_manager.urllib.request.urlopen", _fake_urlopen(calls)):
        SessionDataManager(csv_url="https://example.test/a.csv").fetch()
        manager = SessionDataManager(csv_url="https://example.test/a.csv")
        manager.fetch()
    assert len(calls) == 1
    assert [s["id"] for s in manager.sessions] == ["ERIC-LOUIS"]


def test_remote_csv_cache_expires():
    calls = []
    data_manager._CSV_CACHE.clear()
    with patch("src.data_manager.urllib.request.urlopen", _fake_urlopen(calls)), \
            patch("src.data_manager.time.monotonic", side_effect=[0.0, 1000.0, 1000.0]):
        SessionDataManager(csv_url="https://example.test/b.csv").fetch()
        SessionDataManager(csv_url="https://example.test/b.csv").fetch()
    assert len(calls) == 2
