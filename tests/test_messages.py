import os
import sys
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.messages import load_win_messages


def _messages_csv(csv_content: str):
    return patch("src.messages._download_csv", return_value=csv_content)


def test_load_win_messages_parses_columns_and_rows():
    csv_content = "DAVIDwin,ERICwin\nGagne.,Top.\nAgain,Winner\n"
    with _messages_csv(csv_content):
        result = load_win_messages(csv_url="http://example.com/messages.csv")
    assert "DAVID" in result
    assert "ERIC" in result
    assert result["DAVID"] == ["Gagne.", "Again"]
    assert result["ERIC"] == ["Top.", "Winner"]


def test_load_win_messages_skips_empty_cells():
    csv_content = "DAVIDwin,ERICwin\nmsg1,\n,msg2\n"
    with _messages_csv(csv_content):
        result = load_win_messages(csv_url="http://example.com/messages.csv")
    assert result["DAVID"] == ["msg1"]
    assert result["ERIC"] == ["msg2"]


def test_load_win_messages_returns_empty_dict_on_error():
    with patch("src.messages._download_csv", side_effect=Exception("network error")):
        result = load_win_messages(csv_url="http://example.com/messages.csv")
    assert result == {}


def test_load_win_messages_maps_alexandre_to_alex():
    csv_content = "ALEXANDREwin\nYellow wins.\n"
    with _messages_csv(csv_content):
        result = load_win_messages(csv_url="http://example.com/messages.csv")
    assert "ALEX" in result
    assert "ALEXANDRE" not in result
    assert result["ALEX"] == ["Yellow wins."]
