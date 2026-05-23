# Convert DOCX/PDF to Markdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `kbmate convert` command that converts `.docx` and `.pdf` files to markdown with extracted images.

**Architecture:** One typer CLI entry (`kbmate`), two conversion backends (`pymupdf4llm` for PDF, `pypandoc` for DOCX), and a shared image post-processing step that normalizes image paths.

**Tech Stack:** Python 3.12+, typer, pymupdf4llm, pypandoc, pandoc (system)

---

### Task 1: Set up project structure and dependencies

**Files:**
- Create: `src/mate_cli/__init__.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create package structure**

Create `src/mate_cli/__init__.py`:
```python

```

- [ ] **Step 2: Update pyproject.toml with dependencies and entry point**

```toml
[project]
name = "mate-cli"
version = "0.1.0"
description = "CLI tools for knowledge base management"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "pymupdf4llm",
    "pypandoc",
    "typer>=0.15.0",
]

[project.scripts]
kbmate = "mate_cli.main:app"
```

- [ ] **Step 3: Install dependencies**

Run: `uv sync`

Expected: All dependencies installed without errors.

- [ ] **Step 4: Verify typer app loads**

Run: `uv run python -c "from mate_cli.main import app; print(app)"`

Expected: Prints `<typer.models.TyperInfo object>` or similar (should not error).

---

### Task 2: Implement PDF converter module

**Files:**
- Create: `src/mate_cli/pdf_converter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pdf_converter.py`:
```python
import pytest
from pathlib import Path
from mate_cli.pdf_converter import convert_pdf


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
```

Run: `uv run pytest tests/test_pdf_converter.py -v`

Expected: FAIL — module not found.

- [ ] **Step 2: Write minimal implementation**

Create `src/mate_cli/pdf_converter.py`:
```python
from pathlib import Path

import pymupdf4llm


def convert_pdf(pdf_path: str, image_dir: str) -> str:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    img_path = Path(image_dir)
    img_path.mkdir(parents=True, exist_ok=True)

    md_text = pymupdf4llm.to_markdown(
        pdf_path,
        write_images=True,
        image_path=str(img_path),
        image_format="png",
        dpi=150,
        page_chunks=False,
    )
    return md_text
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/test_pdf_converter.py -v`

Expected: All 3 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/mate_cli/__init__.py src/mate_cli/pdf_converter.py tests/test_pdf_converter.py pyproject.toml
git commit -m "feat: add pdf converter module"
```

---

### Task 3: Implement DOCX converter module

**Files:**
- Create: `src/mate_cli/docx_converter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_docx_converter.py`:
```python
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
    images = list(media_dir.glob("*.png"))
    assert len(images) > 0
    assert "![](/" in result
```

Run: `uv run pytest tests/test_docx_converter.py -v`

Expected: FAIL — module not found.

- [ ] **Step 2: Write minimal implementation**

Create `src/mate_cli/docx_converter.py`:
```python
from pathlib import Path

import pypandoc


def convert_docx(docx_path: str, media_dir: str) -> str:
    path = Path(docx_path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")

    md_text = pypandoc.convert_file(
        docx_path,
        "markdown",
        extra_args=["--wrap=none", f"--extract-media={media_dir}"],
    )
    return md_text
```

Run: `uv run pytest tests/test_docx_converter.py -v`

Expected: All 3 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/mate_cli/docx_converter.py tests/test_docx_converter.py
git commit -m "feat: add docx converter module"
```

---

### Task 4: Implement image path post-processor

**Files:**
- Create: `src/mate_cli/image_helper.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_image_helper.py`:
```python
import pytest
from pathlib import Path
from mate_cli.image_helper import normalize_image_refs, extract_and_relink_images


def test_normalize_image_refs_strips_pandoc_attrs():
    md = "![alt](media/image1.png \"title\"){width=\"5in\" height=\"3in\"}"
    result = normalize_image_refs(md)
    assert "{width=" not in result
    assert "{height=" not in result
    assert "\"title\"" not in result


def test_normalize_image_refs_does_not_alter_plain_refs():
    md = "![](/assets/foo/image-001.png)"
    result = normalize_image_refs(md)
    assert result == md


def test_extract_and_relink_images():
    md_content = (
        "![](/tmp/src/doc-0001-01.png)\n"
        "![](/tmp/src/doc-0001-02.png)"
    )
    src_dir = Path("/tmp/test_relink_src")
    dst_dir = Path("/tmp/test_relink_dst")
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "doc-0001-01.png").touch()
    (src_dir / "doc-0001-02.png").touch()

    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir))

    assert (dst_dir / "image-001.png").exists()
    assert (dst_dir / "image-002.png").exists()
    assert "/image-001.png" in result
    assert "/image-002.png" in result
    assert "doc-0001-01" not in result
```

Run: `uv run pytest tests/test_image_helper.py -v`

Expected: FAIL — module not found.

- [ ] **Step 2: Write minimal implementation**

Create `src/mate_cli/image_helper.py`:
```python
import re
import shutil
from pathlib import Path


def normalize_image_refs(markdown: str) -> str:
    result = markdown
    result = re.sub(r'\s*\{[^}]*\}', '', result)
    return result


def extract_and_relink_images(markdown: str, src_dir: str, dst_dir: str) -> str:
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)
    dst_path.mkdir(parents=True, exist_ok=True)

    img_pattern = re.compile(r'!\[.*?\]\(([^)]+)\)')
    counter = 1
    result = markdown

    for match in img_pattern.finditer(markdown):
        img_path = match.group(1)
        src_file = src_path / Path(img_path).name
        if src_file.exists():
            new_name = f"image-{counter:03d}{src_file.suffix}"
            dst_file = dst_path / new_name
            shutil.copy2(str(src_file), str(dst_file))
            old_ref = match.group(0)
            new_ref = f"![](/assets/{dst_path.name}/{new_name})"
            result = result.replace(old_ref, new_ref, 1)
            counter += 1

    return result
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/test_image_helper.py -v`

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/mate_cli/image_helper.py tests/test_image_helper.py
git commit -m "feat: add image post-processing module"
```

---

### Task 5: Wire up the CLI command (typer app)

**Files:**
- Create: `src/mate_cli/main.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:
```python
import pytest
from typer.testing import CliRunner
from mate_cli.main import app

runner = CliRunner()


def test_convert_help():
    result = runner.invoke(app, ["convert", "--help"])
    assert result.exit_code == 0
    assert "SOURCE_FILE" in result.stdout


def test_convert_missing_file():
    result = runner.invoke(app, ["convert", "nonexistent.pdf"])
    assert result.exit_code != 0


def test_convert_invalid_extension():
    result = runner.invoke(app, ["convert", "evals/2412.20138v7.pdf"])
    assert result.exit_code == 0
```

Run: `uv run pytest tests/test_cli.py -v`

Expected: FAIL — module not found.

- [ ] **Step 2: Write minimal implementation**

Create `src/mate_cli/main.py`:
```python
from pathlib import Path

import typer

app = typer.Typer()


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

        media_dir = assets_dir / "media"
        markdown_content = convert_docx(str(src), str(media_dir))

        from mate_cli.image_helper import normalize_image_refs, extract_and_relink_images

        markdown_content = normalize_image_refs(markdown_content)
        markdown_content = extract_and_relink_images(
            markdown_content, str(media_dir), str(assets_dir)
        )
        if media_dir.exists():
            import shutil
            shutil.rmtree(media_dir)

    md_path = converts_dir / f"{stem}.md"
    md_path.write_text(markdown_content, encoding="utf-8")
    typer.echo(f"Converted: {src} -> {md_path}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`

Expected: All 3 tests PASS.

- [ ] **Step 4: Run manual integration tests against all eval files**

```bash
uv run python -m src.mate_cli.main convert evals/minimaxzh.docx
uv run python -m src.mate_cli.main convert evals/minimax.pdf
uv run python -m src.mate_cli.main convert evals/2412.20138v7.pdf
```

Expected: Each command completes without error.

- [ ] **Step 5: Verify output structure**

```bash
ls -la raw/converts/
ls -la raw/assets/
```

Expected: Markdown files exist in `raw/converts/`, image directories exist in `raw/assets/`.

- [ ] **Step 6: Commit**

```bash
git add src/mate_cli/main.py tests/test_cli.py
git commit -m "feat: wire up kbmate convert CLI command"
```

---

### Task 6: Update root main.py for backward compatibility

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update root main.py**

Replace contents with:
```python
from mate_cli.main import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Verify it still works**

Run: `uv run python main.py convert --help`

Expected: Shows help text for convert command.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "chore: update root main.py to delegate to package"
```

---

### Task 7: Verify everything end-to-end

- [ ] **Step 1: Run all tests**

Run: `uv run pytest tests/ -v`

Expected: All tests PASS.

- [ ] **Step 2: Verify global install**

Run: `uv tool install . && kbmate convert evals/minimaxzh.docx`

Expected: Command works. Then: `uv tool uninstall mate-cli`

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: finalize convert command implementation"
```
