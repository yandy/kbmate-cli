from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse

import typer
from pymupdf4llm.helpers.utils import md_path as _md_path
from kbmate_cli.url_downloader import download_to_temp, is_url, print_cleanup_hint, resolve_file_type

app = typer.Typer()


@app.callback()
def main():
    """Convert PDF/DOCX files to markdown."""


def _resolve_source(source_file: str) -> tuple[str, Path | None]:
    if not is_url(source_file):
        return source_file, None
    if source_file.startswith("file://"):
        return urlparse(source_file).path, None
    suffix = resolve_file_type(source_file)
    temp_path = download_to_temp(source_file, suffix)
    if temp_path.stat().st_size == 0:
        temp_path.unlink()
        raise ValueError("downloaded file is empty")
    return str(temp_path), temp_path


def _convert_pdf(src: Path, assets_dir: Path) -> str:
    from kbmate_cli.pdf_converter import convert_pdf
    from kbmate_cli.image_helper import extract_and_relink_images

    md = convert_pdf(str(src), str(assets_dir))
    return extract_and_relink_images(md, str(assets_dir), str(assets_dir))


def _convert_docx(src: Path, assets_dir: Path) -> str:
    from kbmate_cli.docx_converter import convert_docx
    from kbmate_cli.image_helper import normalize_image_refs, extract_and_relink_images

    pandoc_output = assets_dir / "pandoc_output"
    md = convert_docx(str(src), str(pandoc_output))
    md = normalize_image_refs(md)
    md = extract_and_relink_images(md, str(pandoc_output), str(assets_dir))
    if pandoc_output.exists():
        import shutil
        shutil.rmtree(pandoc_output)
    return md


_CONVERTERS = {
    ".pdf": _convert_pdf,
    ".docx": _convert_docx,
}


@app.command()
def convert(
    source_file: str = typer.Argument(..., help="Path or URL to the .docx or .pdf file"),
    output_dir: str = typer.Option("raw", help="Output directory"),
):
    try:
        source_file, temp_path = _resolve_source(source_file)
    except (ValueError, URLError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    src = Path(source_file)
    if not src.exists():
        typer.echo(f"Error: file not found: {source_file}", err=True)
        raise typer.Exit(code=1)

    ext = src.suffix.lower()
    converter = _CONVERTERS.get(ext)
    if converter is None:
        fmts = ", ".join(_CONVERTERS)
        typer.echo(f"Error: unsupported format: {ext} (supported: {fmts})", err=True)
        raise typer.Exit(code=1)

    out_dir = Path(output_dir)
    assets_parent = out_dir / "assets"

    sanitized_ref, _ = _md_path(str(assets_parent), f"{src.stem}.x")
    safe_stem = Path(sanitized_ref).stem

    assets_dir = assets_parent / safe_stem
    converts_dir = out_dir / "converts"
    converts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    try:
        markdown_content = converter(src, assets_dir)
        md_path = converts_dir / f"{safe_stem}.md"
        md_path.write_text(markdown_content, encoding="utf-8")
        typer.echo(f"Converted: {src} -> {md_path}")
    finally:
        if temp_path:
            print_cleanup_hint(temp_path)


if __name__ == "__main__":
    app()
