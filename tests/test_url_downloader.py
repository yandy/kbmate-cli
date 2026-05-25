import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import URLError

from kbmate_cli.url_downloader import (
    is_url, guess_ext_from_url,
    probe_content_type, resolve_file_type,
    download_to_temp, print_cleanup_hint,
)


class TestIsUrl:
    def test_http(self):
        assert is_url("http://example.com/doc.pdf") is True

    def test_https(self):
        assert is_url("https://example.com/doc.pdf") is True

    def test_file_protocol(self):
        assert is_url("file:///home/user/doc.pdf") is True

    def test_local_path(self):
        assert is_url("/home/user/doc.pdf") is False

    def test_relative_path(self):
        assert is_url("doc.pdf") is False


class TestGuessExtFromUrl:
    def test_pdf(self):
        assert guess_ext_from_url("https://example.com/doc.pdf") == ".pdf"

    def test_docx(self):
        assert guess_ext_from_url("https://example.com/report.docx") == ".docx"

    def test_no_ext(self):
        assert guess_ext_from_url("https://example.com/download") is None

    def test_query_string(self):
        assert guess_ext_from_url("https://example.com/file.pdf?token=abc") == ".pdf"


class TestProbeContentType:
    @patch("kbmate_cli.url_downloader.urlopen")
    def test_pdf_content_type(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        assert probe_content_type("https://example.com/doc") == ".pdf"

    @patch("kbmate_cli.url_downloader.urlopen")
    def test_docx_content_type(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        assert probe_content_type("https://example.com/doc") == ".docx"

    @patch("kbmate_cli.url_downloader.urlopen")
    def test_unknown_content_type(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "application/octet-stream"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        assert probe_content_type("https://example.com/doc") is None

    @patch("kbmate_cli.url_downloader.urlopen")
    def test_network_error_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("connection failed")
        assert probe_content_type("https://example.com/doc") is None


class TestResolveFileType:
    @patch("kbmate_cli.url_downloader.probe_content_type")
    def test_probe_success(self, mock_probe):
        mock_probe.return_value = ".pdf"
        assert resolve_file_type("https://example.com/doc") == ".pdf"
        mock_probe.assert_called_once()

    @patch("kbmate_cli.url_downloader.probe_content_type")
    def test_probe_fallback_to_url(self, mock_probe):
        mock_probe.return_value = None
        assert resolve_file_type("https://example.com/doc.pdf") == ".pdf"

    @patch("kbmate_cli.url_downloader.probe_content_type")
    def test_no_match_raises(self, mock_probe):
        mock_probe.return_value = None
        with pytest.raises(ValueError, match="cannot determine file type"):
            resolve_file_type("https://example.com/doc")


class TestDownloadToTemp:
    @patch("kbmate_cli.url_downloader.urlopen")
    def test_download_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"%PDF-1.4 fake content"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = download_to_temp("https://example.com/doc.pdf", ".pdf")
        assert isinstance(result, Path)
        assert result.suffix == ".pdf"
        assert result.exists()
        assert result.read_bytes() == b"%PDF-1.4 fake content"
        result.unlink()

    @patch("kbmate_cli.url_downloader.urlopen")
    def test_network_error_raises(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("connection refused")
        with pytest.raises(URLError):
            download_to_temp("https://example.com/doc.pdf", ".pdf")


class TestPrintCleanupHint:
    def test_prints_message(self, capsys):
        p = Path("/tmp/test_file.pdf")
        print_cleanup_hint(p)
        captured = capsys.readouterr()
        assert "/tmp/test_file.pdf" in captured.out
        assert "手动删除" in captured.out
