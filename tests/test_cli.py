from pathlib import Path

import pytest
from typer.testing import CliRunner
from kbmate_cli.main import app

runner = CliRunner()


def test_convert_help():
    result = runner.invoke(app, ["convert", "--help"])
    assert result.exit_code == 0
    assert "SOURCE_FILE" in result.stdout


def test_convert_missing_file():
    result = runner.invoke(app, ["convert", "nonexistent.pdf"])
    assert result.exit_code != 0


def test_convert_pdf():
    result = runner.invoke(app, ["convert", "evals/minimax.pdf", "--output-dir", "/tmp/test_cli_output"])
    assert result.exit_code == 0


def test_convert_pdf_with_spaces_in_filename():
    src = Path("/tmp/test with spaces.pdf")
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(Path("evals/minimax.pdf").read_bytes())
    out = Path("/tmp/test_cli_spaces_output")
    result = runner.invoke(app, ["convert", str(src), "--output-dir", str(out)])
    assert result.exit_code == 0, f"Failed with output: {result.output}"
    assets_dir = out / "assets" / "test_with_spaces"
    assert assets_dir.exists()
    images = list(assets_dir.glob("*"))
    assert len(images) > 0, f"No images found in {assets_dir}"
