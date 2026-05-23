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
