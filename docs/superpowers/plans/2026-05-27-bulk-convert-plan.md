# bulk-convert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `kbmate bulk-convert` command to batch-convert PDF/DOCX files from a directory (`-r`) or a file list (`-f`), with flat/mirror output layout support.

**Architecture:** Extract a shared `convert_single()` function from the existing `convert` command. Add two file-collection helpers. Add the `bulk_convert` typer command that uses them both. `convert` becomes a thin wrapper around `convert_single`.

**Tech Stack:** Python 3.12+, typer, pymupdf4llm, pypandoc, pytest

---

### Task 1: Extract `convert_single()` and refactor `convert`

**Files:**
- Modify: `src/kbmate_cli/main.py:58-99`
- Modify: `src/kbmate_cli/main.py` (add `from typing import Literal` to imports)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add `convert_single()` function**

Add to `src/kbmate_cli/main.py` after line 55 (after `_CONVERTERS` dict):

```python
from typing import Literal


def convert_single(
    source_path: Path,
    output_dir: Path,
    *,
    layout: Literal["flat", "mirror"] = "flat",
    relative_to: Path | None = None,
) -> None:
    ext = source_path.suffix.lower()
    converter = _CONVERTERS.get(ext)
    if converter is None:
        fmts = ", ".join(_CONVERTERS)
        typer.echo(f"Error: unsupported format: {ext} (supported: {fmts})", err=True)
        raise typer.Exit(code=1)

    assets_parent = output_dir / "assets"

    if layout == "mirror" and relative_to is not None:
        try:
            rel = source_path.relative_to(relative_to).parent
        except ValueError:
            rel = Path(".")
    else:
        rel = Path(".")

    sanitized_ref, _ = _md_path(str(assets_parent / rel), f"{source_path.stem}.x")
    safe_stem = Path(sanitized_ref).stem

    assets_dir = assets_parent / rel / safe_stem
    converts_dir = output_dir / "converts" / rel
    converts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    markdown_content = converter(source_path, assets_dir)
    md_path = converts_dir / f"{safe_stem}.md"
    md_path.write_text(markdown_content, encoding="utf-8")
    typer.echo(f"Converted: {source_path} -> {md_path}")
```

- [ ] **Step 2: Refactor `convert` command to use `convert_single()`**

Replace the `convert` command body (lines 62-99) with:

```python
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
    finally:
        if temp_path:
            print_cleanup_hint(temp_path)
```

- [ ] **Step 3: Run existing tests to verify refactor didn't break anything**

Run: `uv run pytest tests/test_cli.py -v`
Expected: All 6 tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/kbmate_cli/main.py
git commit -m "refactor: extract convert_single() from convert command"
```

---

### Task 2: Add `_collect_files_from_dir()` and `_collect_files_from_list()`

**Files:**
- Modify: `src/kbmate_cli/main.py` (add helper functions)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:

```python
from kbmate_cli.main import _collect_files_from_dir, _collect_files_from_list
import tempfile


def test_collect_files_from_dir():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "sub").mkdir()
        pdf1 = root / "a.pdf"
        docx1 = root / "sub" / "b.docx"
        txt1 = root / "c.txt"
        pdf1.write_text("fake pdf")
        docx1.write_text("fake docx")
        txt1.write_text("fake txt")

        files = _collect_files_from_dir(root)
        assert len(files) == 2
        assert pdf1 in files
        assert docx1 in files
        assert txt1 not in files


def test_collect_files_from_dir_empty():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = _collect_files_from_dir(root)
        assert files == []


def test_collect_files_from_list_local(tmp_path):
    filelist = tmp_path / "sources.txt"
    filelist.write_text("/path/to/a.pdf\n/path/to/b.docx\n")
    result = _collect_files_from_list(filelist)
    assert result == ["/path/to/a.pdf", "/path/to/b.docx"]


def test_collect_files_from_list_urls(tmp_path):
    filelist = tmp_path / "sources.txt"
    filelist.write_text("https://example.com/doc.pdf\n/path/to/local.docx\n")
    result = _collect_files_from_list(filelist)
    assert result == ["https://example.com/doc.pdf", "/path/to/local.docx"]


def test_collect_files_from_list_empty_lines(tmp_path):
    filelist = tmp_path / "sources.txt"
    filelist.write_text("/path/to/a.pdf\n\n/path/to/b.docx\n  \n")
    result = _collect_files_from_list(filelist)
    assert result == ["/path/to/a.pdf", "/path/to/b.docx"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py::test_collect_files_from_dir tests/test_cli.py::test_collect_files_from_dir_empty tests/test_cli.py::test_collect_files_from_list_local tests/test_cli.py::test_collect_files_from_list_urls tests/test_cli.py::test_collect_files_from_list_empty_lines -v`
Expected: FAIL with ImportError (function not defined)

- [ ] **Step 3: Implement helper functions**

Add after `_resolve_source` in `src/kbmate_cli/main.py` (after line 27):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py::test_collect_files_from_dir tests/test_cli.py::test_collect_files_from_dir_empty tests/test_cli.py::test_collect_files_from_list_local tests/test_cli.py::test_collect_files_from_list_urls tests/test_cli.py::test_collect_files_from_list_empty_lines -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/kbmate_cli/main.py tests/test_cli.py
git commit -m "feat: add file collection helpers for bulk-convert"
```

---

### Task 3: Add `bulk_convert` command

**Files:**
- Modify: `src/kbmate_cli/main.py` (add command)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for bulk_convert**

Add to `tests/test_cli.py`:

```python
@patch("kbmate_cli.main._convert_pdf", return_value="# mock")
def test_bulk_convert_recursive_dir_flat(mock_convert):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf1 = root / "a.pdf"
        pdf2 = root / "sub" / "b.pdf"
        pdf1.write_text("fake")
        (root / "sub").mkdir()
        pdf2.write_text("fake")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-r", str(root),
            "--output-dir", str(out),
        ])
        assert result.exit_code == 0
        assert (out / "converts" / "a.md").exists()
        assert (out / "converts" / "b.md").exists()


@patch("kbmate_cli.main._convert_pdf", return_value="# mock")
def test_bulk_convert_recursive_dir_mirror(mock_convert):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf1 = root / "a.pdf"
        pdf2 = root / "sub" / "b.pdf"
        pdf1.write_text("fake")
        (root / "sub").mkdir()
        pdf2.write_text("fake")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-r", str(root),
            "--output-dir", str(out),
            "--output-layout", "mirror",
        ])
        assert result.exit_code == 0
        assert (out / "converts" / "a.md").exists()
        assert (out / "converts" / "sub" / "b.md").exists()


@patch("kbmate_cli.main._convert_pdf", return_value="# mock")
def test_bulk_convert_file_list(mock_convert):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf1 = root / "a.pdf"
        pdf1.write_text("fake")
        flist = root / "sources.txt"
        flist.write_text(str(pdf1) + "\n")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-f", str(flist),
            "--output-dir", str(out),
        ])
        assert result.exit_code == 0
        assert (out / "converts" / "a.md").exists()


@patch("kbmate_cli.main._resolve_source")
@patch("kbmate_cli.main._convert_pdf", return_value="# mock")
def test_bulk_convert_file_list_with_url(mock_convert, mock_resolve):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf_local = root / "downloaded.pdf"
        pdf_local.write_text("fake")
        mock_resolve.return_value = (str(pdf_local), None)

        flist = root / "sources.txt"
        flist.write_text("https://example.com/doc.pdf\n")

        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-f", str(flist),
            "--output-dir", str(out),
        ])
        assert result.exit_code == 0
        assert (out / "converts" / "downloaded.md").exists()


def test_bulk_convert_mutual_exclusive(tmp_path):
    result = runner.invoke(app, [
        "bulk-convert", "-r", str(tmp_path), "-f", str(tmp_path / "list.txt"),
    ])
    assert result.exit_code != 0


def test_bulk_convert_no_input():
    result = runner.invoke(app, ["bulk-convert"])
    assert result.exit_code != 0
    assert "either" in result.stdout.lower() or "required" in result.stdout.lower()


def test_bulk_convert_help():
    result = runner.invoke(app, ["bulk-convert", "--help"])
    assert result.exit_code == 0
    assert "Bulk" in result.stdout or "bulk" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py::test_bulk_convert_recursive_dir_flat tests/test_cli.py::test_bulk_convert_recursive_dir_mirror tests/test_cli.py::test_bulk_convert_file_list tests/test_cli.py::test_bulk_convert_file_list_with_url tests/test_cli.py::test_bulk_convert_mutual_exclusive tests/test_cli.py::test_bulk_convert_no_input tests/test_cli.py::test_bulk_convert_help -v`
Expected: FAIL with "No such command 'bulk-convert'"

- [ ] **Step 3: Implement `bulk_convert` command**

Add to `src/kbmate_cli/main.py`, after the `convert` command:

```python
@app.command()
def bulk_convert(
    recursive: str = typer.Option(None, "-r", "--recursive", help="Directory to scan recursively"),
    file_list: str = typer.Option(None, "-f", "--file-list", help="File containing one source per line"),
    output_dir: str = typer.Option("raw", help="Output directory"),
    output_layout: str = typer.Option("flat", "--output-layout", help="Output layout: flat or mirror"),
):
    if (recursive is not None) == (file_list is not None):
        typer.echo("Error: specify either -r (directory) or -f (file list), not both", err=True)
        raise typer.Exit(code=1)

    if output_layout not in ("flat", "mirror"):
        typer.echo("Error: --output-layout must be 'flat' or 'mirror'", err=True)
        raise typer.Exit(code=1)

    out = Path(output_dir)
    sources: list[tuple[Path, Path | None]] = []

    if recursive is not None:
        root = Path(recursive)
        if not root.is_dir():
            typer.echo(f"Error: not a directory: {root}", err=True)
            raise typer.Exit(code=1)
        files = _collect_files_from_dir(root)
        for f in files:
            sources.append((f, None))

        for src_path, temp_path in sources:
            try:
                convert_single(src_path, out, layout=output_layout, relative_to=root)  # type: ignore
            finally:
                if temp_path:
                    print_cleanup_hint(temp_path)
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
                convert_single(src, out, layout=output_layout)
            finally:
                if temp_path:
                    print_cleanup_hint(temp_path)
```

> **Note:** In the `-r` branch, the loop needs to be inside the `if` block. The code above shows the `-r` loop inside the block. The `-f` loop is in the `else` block.

Wait, I need to restructure this. Let me rewrite the command properly:

```python
@app.command()
def bulk_convert(
    recursive: str = typer.Option(None, "-r", "--recursive", help="Directory to scan recursively"),
    file_list: str = typer.Option(None, "-f", "--file-list", help="File containing one source per line"),
    output_dir: str = typer.Option("raw", help="Output directory"),
    output_layout: str = typer.Option("flat", "--output-layout", help="Output layout: flat or mirror"),
):
    if (recursive is not None) == (file_list is not None):
        typer.echo("Error: specify either -r (directory) or -f (file list), not both", err=True)
        raise typer.Exit(code=1)

    if output_layout not in ("flat", "mirror"):
        typer.echo("Error: --output-layout must be 'flat' or 'mirror'", err=True)
        raise typer.Exit(code=1)

    out = Path(output_dir)

    if recursive is not None:
        root = Path(recursive)
        if not root.is_dir():
            typer.echo(f"Error: not a directory: {root}", err=True)
            raise typer.Exit(code=1)
        for src_path in _collect_files_from_dir(root):
            convert_single(src_path, out, layout=output_layout, relative_to=root)
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
                convert_single(src, out, layout=output_layout)
            finally:
                if temp_path:
                    print_cleanup_hint(temp_path)
```

This is cleaner. The `-r` branch doesn't need temp_path handling since all files are local.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py::test_bulk_convert_recursive_dir_flat tests/test_cli.py::test_bulk_convert_recursive_dir_mirror tests/test_cli.py::test_bulk_convert_file_list tests/test_cli.py::test_bulk_convert_file_list_with_url tests/test_cli.py::test_bulk_convert_mutual_exclusive tests/test_cli.py::test_bulk_convert_no_input tests/test_cli.py::test_bulk_convert_help -v`
Expected: All 7 PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests PASS (coverage >= 85%)

- [ ] **Step 6: Commit**

```bash
git add src/kbmate_cli/main.py tests/test_cli.py
git commit -m "feat: add bulk-convert command with -r and -f"
```

---

### Spec Self-Review

- All spec requirements covered: `-r` (recursive dir), `-f` (file list), `--output-layout {flat,mirror}` (default flat), extracted `convert_single()`, `convert` still works.
- No placeholders, TBDs, or vague requirements.
- Signatures consistent across tasks.

---

### Execution

After approval, use subagent-driven-development to execute per-task.
