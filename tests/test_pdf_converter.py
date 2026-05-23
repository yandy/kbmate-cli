import pytest
from pathlib import Path
from kbmate_cli.pdf_converter import convert_pdf


def test_convert_pdf_returns_markdown_content():
    pdf_path = "evals/minimax.pdf"
    result = convert_pdf(pdf_path, "/tmp/test_pdf_assets")
    assert isinstance(result, str)
    assert len(result) > 100
    assert "MiniMax" in result


def test_convert_pdf_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        convert_pdf("nonexistent.pdf", "/tmp/test_pdf_assets")


def test_convert_pdf_extracts_images():
    pdf_path = "evals/minimax.pdf"
    img_dir = Path("/tmp/test_pdf_images")
    img_dir.mkdir(parents=True, exist_ok=True)
    result = convert_pdf(pdf_path, str(img_dir))
    images = list(img_dir.glob("*.png"))
    assert len(images) > 0
    assert "![](/" in result
