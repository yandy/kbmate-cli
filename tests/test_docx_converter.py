import pytest
from pathlib import Path
from mate_cli.docx_converter import convert_docx


def test_convert_docx_returns_markdown_content():
    docx_path = "evals/minimaxzh.docx"
    result = convert_docx(docx_path, "/tmp/test_docx_media")
    assert isinstance(result, str)
    assert len(result) > 100
    assert "MiniMax" in result


def test_convert_docx_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        convert_docx("nonexistent.docx", "/tmp/test_docx_media")


def test_convert_docx_extracts_images():
    docx_path = "evals/minimaxzh.docx"
    media_dir = Path("/tmp/test_docx_media")
    media_dir.mkdir(parents=True, exist_ok=True)
    result = convert_docx(docx_path, str(media_dir))
    images = list(media_dir.rglob("*.png"))
    assert len(images) > 0
    assert "![MiniMax Banner](" in result
