from pathlib import Path

import typer

app = typer.Typer()


@app.callback()
def main():
    """Convert PDF/DOCX files to markdown."""


@app.command()
def convert(
    source_file: str = typer.Argument(..., help="Path to the .docx or .pdf file"),
    output_dir: str = typer.Option("raw", help="Output directory"),
):
    src = Path(source_file)
    if not src.exists():
        typer.echo(f"Error: file not found: {source_file}", err=True)
        raise typer.Exit(code=1)

    ext = src.suffix.lower()
    if ext not in (".pdf", ".docx"):
        typer.echo(f"Error: unsupported format: {ext} (supported: .pdf, .docx)", err=True)
        raise typer.Exit(code=1)

    stem = src.stem
    out_dir = Path(output_dir)
    assets_dir = out_dir / "assets" / stem
    converts_dir = out_dir / "converts"
    converts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    markdown_content: str = ""

    if ext == ".pdf":
        from mate_cli.pdf_converter import convert_pdf

        markdown_content = convert_pdf(str(src), str(assets_dir))

        from mate_cli.image_helper import extract_and_relink_images

        markdown_content = extract_and_relink_images(
            markdown_content, str(assets_dir), str(assets_dir)
        )

    elif ext == ".docx":
        from mate_cli.docx_converter import convert_docx

        pandoc_output = assets_dir / "pandoc_output"
        markdown_content = convert_docx(str(src), str(pandoc_output))

        from mate_cli.image_helper import normalize_image_refs, extract_and_relink_images

        markdown_content = normalize_image_refs(markdown_content)
        markdown_content = extract_and_relink_images(
            markdown_content, str(pandoc_output), str(assets_dir)
        )
        if pandoc_output.exists():
            import shutil

            shutil.rmtree(pandoc_output)

    md_path = converts_dir / f"{stem}.md"
    md_path.write_text(markdown_content, encoding="utf-8")
    typer.echo(f"Converted: {src} -> {md_path}")


if __name__ == "__main__":
    app()
