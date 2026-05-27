from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from kbmate_cli.main import app, _collect_files_from_dir, _collect_files_from_list
import tempfile

runner = CliRunner()


def test_convert_help():
    result = runner.invoke(app, ["convert", "--help"])
    assert result.exit_code == 0
    assert "SOURCE_FILE" in result.stdout


def test_convert_missing_file():
    result = runner.invoke(app, ["convert", "nonexistent.pdf"])
    assert result.exit_code != 0


FIXTURE_DIR = Path(__file__).parent / "evals"


def test_convert_pdf():
    pdf = FIXTURE_DIR / "eigent README CN.pdf"
    result = runner.invoke(app, ["convert", str(pdf), "--output-dir", "/tmp/test_cli_output"])
    assert result.exit_code == 0


def test_convert_lunwen_pdf():
    pdf = FIXTURE_DIR / "论文.pdf"
    result = runner.invoke(app, ["convert", str(pdf), "--output-dir", "/tmp/test_cli_lunwen"])
    assert result.exit_code == 0


def test_convert_pdf_with_spaces_in_filename():
    src = FIXTURE_DIR / "eigent README CN.pdf"
    out = Path("/tmp/test_cli_spaces_output")
    result = runner.invoke(app, ["convert", str(src), "--output-dir", str(out)])
    assert result.exit_code == 0, f"Failed with output: {result.output}"
    assets_dir = out / "assets" / "eigent_README_CN"
    assert assets_dir.exists()
    images = list(assets_dir.glob("*"))
    assert len(images) > 0, f"No images found in {assets_dir}"


def test_convert_file_url():
    """file:// URL 应解析为本地路径并正常工作"""
    pdf = FIXTURE_DIR / "eigent README CN.pdf"
    file_url = f"file://{pdf.resolve()}"
    result = runner.invoke(app, ["convert", file_url, "--output-dir", "/tmp/test_cli_file_url"])
    assert result.exit_code == 0, f"Failed with output: {result.output}"


@patch("kbmate_cli.url_downloader.urlopen")
def test_convert_http_url(mock_urlopen):
    """http URL 应下载后转换"""
    # Mock HEAD probe
    head_resp = MagicMock()
    head_resp.headers = {"Content-Type": "application/pdf"}
    head_resp.__enter__.return_value = head_resp

    # Mock GET download
    pdf_path = FIXTURE_DIR / "eigent README CN.pdf"
    download_resp = MagicMock()
    download_resp.read.return_value = pdf_path.read_bytes()
    download_resp.__enter__.return_value = download_resp

    mock_urlopen.side_effect = [head_resp, download_resp]

    result = runner.invoke(
        app, ["convert", "https://example.com/doc.pdf", "--output-dir", "/tmp/test_cli_http_url"]
    )
    assert result.exit_code == 0, f"Failed with output: {result.output}"
    assert "临时文件已保存至" in result.stdout


def test_collect_files_from_dir():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "sub").mkdir()
        pdf1 = root / "a.pdf"
        docx1 = root / "sub" / "b.docx"
        txt1 = root / "c.txt"
        pdf1.write_text("fake pdf")
        docx1.write_text("fake docx")
        txt1.write_text("fake txt")

        files = _collect_files_from_dir(root)
        assert len(files) == 2
        assert pdf1 in files
        assert docx1 in files
        assert txt1 not in files


def test_collect_files_from_dir_empty():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = _collect_files_from_dir(root)
        assert files == []


def test_collect_files_from_list_local(tmp_path):
    filelist = tmp_path / "sources.txt"
    filelist.write_text("/path/to/a.pdf\n/path/to/b.docx\n")
    result = _collect_files_from_list(filelist)
    assert result == ["/path/to/a.pdf", "/path/to/b.docx"]


def test_collect_files_from_list_urls(tmp_path):
    filelist = tmp_path / "sources.txt"
    filelist.write_text("https://example.com/doc.pdf\n/path/to/local.docx\n")
    result = _collect_files_from_list(filelist)
    assert result == ["https://example.com/doc.pdf", "/path/to/local.docx"]


def test_collect_files_from_list_empty_lines(tmp_path):
    filelist = tmp_path / "sources.txt"
    filelist.write_text("/path/to/a.pdf\n\n/path/to/b.docx\n  \n")
    result = _collect_files_from_list(filelist)
    assert result == ["/path/to/a.pdf", "/path/to/b.docx"]
