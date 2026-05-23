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
