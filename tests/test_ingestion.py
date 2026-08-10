"""Tests for ingestion script."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ingestion.download_ndbc import download_file, download_historical, download_realtime


def test_download_success(tmp_path):
    """Download should save file on success."""
    dest = tmp_path / "test.txt"
    with patch("src.ingestion.download_ndbc.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.content = b"hello"
        mock_get.return_value = mock_resp
        
        result = download_file("http://example.com/data.txt", dest)
    
    assert result is True
    assert dest.read_bytes() == b"hello"


def test_download_retry(tmp_path):
    """Should retry on failure."""
    from requests import RequestException

    dest = tmp_path / "test.txt"
    with patch("src.ingestion.download_ndbc.requests.get",
               side_effect=RequestException("fail")):
        result = download_file("http://example.com/data.txt", dest, retries=3)

    assert result is False


def test_download_historical_path(tmp_path):
    """Historical file should go to historical/ subfolder."""
    with patch("src.ingestion.download_ndbc.download_file", return_value=True) as mock:
        download_historical("41001", 2020, tmp_path)
    
    called_dest = mock.call_args[0][1]
    assert "historical" in str(called_dest)
    assert "41001h2020" in str(called_dest)


def test_download_realtime_path(tmp_path):
    """Realtime file should go to realtime/ subfolder."""
    with patch("src.ingestion.download_ndbc.download_file", return_value=True) as mock:
        download_realtime("41001", tmp_path)
    
    called_dest = mock.call_args[0][1]
    assert "realtime" in str(called_dest)
    assert called_dest.name == "41001.txt"
