import hashlib
import sqlite3
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse

import typer
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


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def _collect_files_from_dir(root: Path) -> list[Path]:
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.suffix.lower() in SUPPORTED_EXTENSIONS and p.is_file():
            files.append(p)
    return files


def _collect_files_from_list(filelist: Path) -> list[str]:
    if not filelist.is_file():
        raise FileNotFoundError(f"file not found: {filelist}")
    lines = filelist.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _convert_pdf(src: Path, src_dir: Path, dst_dir: Path) -> str:
    from kbmate_cli.pdf_converter import convert_pdf
    from kbmate_cli.image_helper import extract_and_relink_images

    md = convert_pdf(str(src), str(src_dir))
    return extract_and_relink_images(md, str(src_dir), str(dst_dir))


def _convert_docx(src: Path, src_dir: Path, dst_dir: Path) -> str:
    from kbmate_cli.docx_converter import convert_docx
    from kbmate_cli.image_helper import normalize_image_refs, extract_and_relink_images

    pandoc_output = src_dir / "pandoc_output"
    md = convert_docx(str(src), str(pandoc_output))
    md = normalize_image_refs(md)
    md = extract_and_relink_images(md, str(pandoc_output), str(dst_dir))
    if pandoc_output.exists():
        import shutil
        shutil.rmtree(pandoc_output)
    return md


_CONVERTERS = {
    ".pdf": _convert_pdf,
    ".docx": _convert_docx,
}


def _record_conversion(output_dir: Path, source_hash: str, source_name: str) -> None:
    db_path = output_dir / "kbmate.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS conversions ("
            "  source_hash TEXT NOT NULL,"
            "  source_name TEXT NOT NULL,"
            "  converted_at TEXT NOT NULL DEFAULT (datetime('now')),"
            "  PRIMARY KEY (source_hash, source_name)"
            ")"
        )
        conn.execute(
            "INSERT OR IGNORE INTO conversions (source_hash, source_name) VALUES (?, ?)",
            (source_hash, source_name),
        )
        conn.commit()
    finally:
        conn.close()


def convert_single(source_path: Path, output_dir: Path) -> None:
    ext = source_path.suffix.lower()
    converter = _CONVERTERS.get(ext)
    if converter is None:
        fmts = ", ".join(_CONVERTERS)
        raise ValueError(f"unsupported format: {ext} (supported: {fmts})")

    source_hash = _hash_file(source_path)

    md_rel = Path(source_hash[:2]) / source_hash[2:4] / f"{source_hash[4:]}.md"
    md_path = output_dir / "converts" / md_rel
    if md_path.exists():
        typer.echo(f"Skipped (already converted): {source_path}")
        return

    assets_parent = output_dir / "assets"
    assets_parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=str(assets_parent)))

    markdown_content = converter(source_path, tmp_dir, assets_parent)

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_content, encoding="utf-8")

    _record_conversion(output_dir, source_hash, source_path.name)
    typer.echo(f"Converted: {source_path} -> {md_path}")


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

    try:
        convert_single(src, Path(output_dir))
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        if temp_path:
            print_cleanup_hint(temp_path)


@app.command()
def bulk_convert(
    recursive: str = typer.Option(None, "-r", "--recursive", help="Directory to scan recursively"),
    file_list: str = typer.Option(None, "-f", "--file-list", help="File containing one source per line"),
    output_dir: str = typer.Option("raw", help="Output directory"),
):
    if (recursive is not None) == (file_list is not None):
        typer.echo("Error: specify either -r (directory) or -f (file list), not both", err=True)
        raise typer.Exit(code=1)

    out = Path(output_dir)

    if recursive is not None:
        root = Path(recursive)
        if not root.is_dir():
            typer.echo(f"Error: not a directory: {root}", err=True)
            raise typer.Exit(code=1)
        for src_path in _collect_files_from_dir(root):
            try:
                convert_single(src_path, out)
            except Exception as e:
                typer.echo(f"Error converting {src_path}: {e}", err=True)
    else:
        assert file_list is not None
        flist = Path(file_list)
        try:
            lines = _collect_files_from_list(flist)
        except FileNotFoundError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)

        for line in lines:
            try:
                local_path, temp_path = _resolve_source(line)
            except (ValueError, URLError) as e:
                typer.echo(f"Error processing '{line}': {e}", err=True)
                continue
            src = Path(local_path)
            if not src.exists():
                typer.echo(f"Error: file not found: {local_path}", err=True)
                if temp_path:
                    print_cleanup_hint(temp_path)
                continue
            try:
                convert_single(src, out)
            except Exception as e:
                typer.echo(f"Error converting {src}: {e}", err=True)
            finally:
                if temp_path:
                    print_cleanup_hint(temp_path)


if __name__ == "__main__":
    app()
