import pytest
from pathlib import Path

from kbmate_cli.url_downloader import is_url, guess_ext_from_url


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
