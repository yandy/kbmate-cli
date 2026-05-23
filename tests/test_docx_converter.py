import pytest
from pathlib import Path
from kbmate_cli.docx_converter import convert_docx


FIXTURE_DIR = Path(__file__).parent / "evals"


def test_convert_docx_returns_markdown_content():
    docx_path = FIXTURE_DIR / "datamol-safe README.docx"
    result = convert_docx(str(docx_path), "/tmp/test_docx_media")
    assert isinstance(result, str)
    assert len(result) > 100
    assert "SAFE" in result


def test_convert_docx_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        convert_docx("nonexistent.docx", "/tmp/test_docx_media")


def test_convert_docx_extracts_images():
    docx_path = FIXTURE_DIR / "datamol-safe README.docx"
    media_dir = Path("/tmp/test_docx_media")
    media_dir.mkdir(parents=True, exist_ok=True)
    result = convert_docx(str(docx_path), str(media_dir))
    images = list(media_dir.rglob("*.*"))
    assert len(images) > 0
    assert "![IMG_256]" in result
