import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from kbmate_cli.main import app, _collect_files_from_dir, _collect_files_from_list, convert_single

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


def test_convert_assets_seqname_flag_in_help():
    result = runner.invoke(app, ["convert", "--help"])
    assert result.exit_code == 0
    assert "--assets-seqname" in result.stdout


def test_bulk_convert_assets_seqname_flag_in_help():
    result = runner.invoke(app, ["bulk-convert", "--help"])
    assert result.exit_code == 0
    assert "--assets-seqname" in result.stdout


@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(return_value="# mock")})
def test_bulk_convert_assets_seqname_flag():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf = root / "a.pdf"
        pdf.write_text("fake")
        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-r", str(root),
            "--output-dir", str(out),
            "--assets-seqname",
        ])
        assert result.exit_code == 0
        assets_dir = out / "assets" / "a"
        assert assets_dir.exists()


def test_convert_pdf_with_spaces_in_filename():
    src = FIXTURE_DIR / "eigent README CN.pdf"
    out = Path("/tmp/test_cli_spaces_output")
    result = runner.invoke(app, ["convert", str(src), "--output-dir", str(out)])
    assert result.exit_code == 0, f"Failed with output: {result.output}"
    assert (out / "assets").exists()
    hash_dirs = list((out / "assets").glob("*"))
    assert len(hash_dirs) > 0, f"No hash dirs found in {out / 'assets'}"


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


@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(return_value="# mock")})
def test_bulk_convert_recursive_dir_flat():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf1 = root / "a.pdf"
        pdf2 = root / "sub" / "b.pdf"
        pdf1.write_text("fake")
        (root / "sub").mkdir()
        pdf2.write_text("fake")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-r", str(root),
            "--output-dir", str(out),
        ])
        assert result.exit_code == 0
        assert (out / "converts" / "a.md").exists()
        assert (out / "converts" / "b.md").exists()


@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(return_value="# mock")})
def test_bulk_convert_recursive_dir_mirror():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf1 = root / "a.pdf"
        pdf2 = root / "sub" / "b.pdf"
        pdf1.write_text("fake")
        (root / "sub").mkdir()
        pdf2.write_text("fake")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-r", str(root),
            "--output-dir", str(out),
            "--output-layout", "mirror",
        ])
        assert result.exit_code == 0
        assert (out / "converts" / "a.md").exists()
        assert (out / "converts" / "sub" / "b.md").exists()


@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(return_value="# mock")})
def test_bulk_convert_file_list():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf1 = root / "a.pdf"
        pdf1.write_text("fake")
        flist = root / "sources.txt"
        flist.write_text(str(pdf1) + "\n")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-f", str(flist),
            "--output-dir", str(out),
        ])
        assert result.exit_code == 0
        assert (out / "converts" / "a.md").exists()


@patch("kbmate_cli.main._resolve_source")
@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(return_value="# mock")})
def test_bulk_convert_file_list_with_url(mock_resolve):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf_local = root / "downloaded.pdf"
        pdf_local.write_text("fake")
        mock_resolve.return_value = (str(pdf_local), None)

        flist = root / "sources.txt"
        flist.write_text("https://example.com/doc.pdf\n")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-f", str(flist),
            "--output-dir", str(out),
        ])
        assert result.exit_code == 0
        assert (out / "converts" / "downloaded.md").exists()


def test_bulk_convert_mutual_exclusive(tmp_path):
    result = runner.invoke(app, [
        "bulk-convert", "-r", str(tmp_path), "-f", str(tmp_path / "list.txt"),
    ])
    assert result.exit_code != 0


def test_bulk_convert_no_input():
    result = runner.invoke(app, ["bulk-convert"])
    assert result.exit_code != 0
    assert "specify either" in result.stderr.lower()


def test_bulk_convert_invalid_layout(tmp_path):
    result = runner.invoke(app, [
        "bulk-convert", "-r", str(tmp_path),
        "--output-layout", "invalid",
    ])
    assert result.exit_code != 0
    assert "must be 'flat' or 'mirror'" in result.stderr.lower()


@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(side_effect=[RuntimeError("unexpected crash"), "# mock"])})
def test_bulk_convert_runtime_error_continues_r():
    """RuntimeError from converter should not crash the entire -r batch"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf1 = root / "a.pdf"
        pdf2 = root / "b.pdf"
        pdf1.write_text("fake")
        pdf2.write_text("fake")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-r", str(root),
            "--output-dir", str(out),
        ])
        assert result.exit_code == 0
        assert "Error converting" in result.stderr
        converted = list(out.rglob("*.md"))
        assert len(converted) == 1


@patch("kbmate_cli.main._resolve_source")
@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(side_effect=[RuntimeError("unexpected crash"), "# mock"])})
def test_bulk_convert_runtime_error_continues_f(mock_resolve, tmp_path):
    """RuntimeError from converter should not crash the entire -f batch"""
    root = tmp_path
    pdf1 = root / "a.pdf"
    pdf2 = root / "b.pdf"
    pdf1.write_text("fake")
    pdf2.write_text("fake")
    mock_resolve.side_effect = [
        (str(pdf1), None),
        (str(pdf2), None),
    ]

    flist = root / "sources.txt"
    flist.write_text("/path/to/a.pdf\n/path/to/b.pdf\n")

    out = root / "out"
    result = runner.invoke(app, [
        "bulk-convert", "-f", str(flist),
        "--output-dir", str(out),
    ])
    assert result.exit_code == 0
    assert "Error converting" in result.stderr
    converted = list(out.rglob("*.md"))
    assert len(converted) == 1


@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(side_effect=[ValueError("mock fail"), "# mock"])})
def test_bulk_convert_continue_on_error():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf1 = root / "a.pdf"
        pdf2 = root / "b.pdf"
        pdf1.write_text("fake")
        pdf2.write_text("fake")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-r", str(root),
            "--output-dir", str(out),
        ])
        # Batch continues despite one failure
        assert result.exit_code == 0
        assert "Error converting" in result.stderr
        # Exactly one file should have been converted (one fails, one succeeds)
        converted = list(out.rglob("*.md"))
        assert len(converted) == 1


def test_bulk_convert_file_list_rejects_mirror(tmp_path):
    flist = tmp_path / "sources.txt"
    flist.write_text("/path/to/a.pdf\n")
    result = runner.invoke(app, [
        "bulk-convert", "-f", str(flist),
        "--output-layout", "mirror",
    ])
    assert result.exit_code != 0
    assert "mirror is only supported with -r" in result.stderr.lower()


def test_bulk_convert_help():
    result = runner.invoke(app, ["bulk-convert", "--help"])
    assert result.exit_code == 0
    assert "bulk" in result.stdout.lower() or "-r" in result.stdout


# ── Error-handling coverage tests ─────────────────────────────────────────────


def test_collect_files_from_dir_not_a_directory(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("not a dir")
    with pytest.raises(NotADirectoryError):
        _collect_files_from_dir(f)


def test_collect_files_from_list_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        _collect_files_from_list(tmp_path / "nonexistent.txt")


def test_convert_single_unsupported_format(tmp_path):
    txt = tmp_path / "test.txt"
    txt.write_text("hello")
    with pytest.raises(ValueError, match="unsupported format"):
        convert_single(txt, tmp_path)


def test_convert_unsupported_format(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    result = runner.invoke(app, ["convert", str(f)])
    assert result.exit_code != 0
    assert "unsupported format" in result.stderr.lower()


@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(return_value="# mock")})
def test_convert_single_mirror_relative_to_fails(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    pdf = tmp_path / "a.pdf"
    pdf.write_text("fake")
    convert_single(pdf, tmp_path, layout="mirror", relative_to=sub)
    assert (tmp_path / "converts" / "a.md").exists()


def test_convert_empty_download(tmp_path):
    import tempfile as _tf

    tf = _tf.NamedTemporaryFile(delete=False, suffix=".pdf")
    tf.write(b"")
    tf.close()
    p = Path(tf.name)
    with patch("kbmate_cli.main.download_to_temp", return_value=p):
        result = runner.invoke(app, [
            "convert", "https://example.com/empty.pdf",
        ])
    assert result.exit_code != 0
    p.unlink(missing_ok=True)


def test_bulk_convert_recursive_not_a_directory(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("not a dir")
    result = runner.invoke(app, ["bulk-convert", "-r", str(f)])
    assert result.exit_code != 0
    assert "not a directory" in result.stderr.lower()


def test_bulk_convert_file_list_not_found(tmp_path):
    result = runner.invoke(app, [
        "bulk-convert", "-f", str(tmp_path / "nonexistent.txt"),
    ])
    assert result.exit_code != 0
    assert "file not found" in result.stderr.lower()


@patch("kbmate_cli.main._resolve_source")
def test_bulk_convert_file_list_url_error(mock_resolve, tmp_path):
    mock_resolve.side_effect = ValueError("download failed")
    flist = tmp_path / "sources.txt"
    flist.write_text("https://example.com/fail.pdf\n")
    result = runner.invoke(app, ["bulk-convert", "-f", str(flist)])
    assert result.exit_code == 0
    assert "Error processing" in result.stderr


@patch("kbmate_cli.main.print_cleanup_hint")
@patch("kbmate_cli.main._resolve_source")
def test_bulk_convert_file_list_file_not_found_with_temp(mock_resolve, mock_hint, tmp_path):
    mock_resolve.return_value = ("/nonexistent/path.pdf", Path("/tmp/cleanup_me.pdf"))
    flist = tmp_path / "sources.txt"
    flist.write_text("https://example.com/gone.pdf\n")
    result = runner.invoke(app, ["bulk-convert", "-f", str(flist)])
    assert result.exit_code == 0
    mock_hint.assert_called_once()


@patch("kbmate_cli.main.print_cleanup_hint")
@patch("kbmate_cli.main._resolve_source")
@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(side_effect=ValueError("convert failed"))})
def test_bulk_convert_file_list_convert_error_with_temp(mock_resolve, mock_hint, tmp_path):
    local_pdf = tmp_path / "a.pdf"
    local_pdf.write_text("fake")
    mock_resolve.return_value = (str(local_pdf), Path("/tmp/cleanup_me.pdf"))
    flist = tmp_path / "sources.txt"
    flist.write_text("https://example.com/a.pdf\n")
    result = runner.invoke(app, ["bulk-convert", "-f", str(flist)])
    assert result.exit_code == 0
    mock_hint.assert_called_once()
