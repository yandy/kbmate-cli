# Cleanup & Hash Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `--output-layout` and `--assets-seqname` CLI options, add source-file hash-based markdown paths with skip-on-duplicate, fix asset hash filename redundancy, add SQLite record DB.

**Architecture:** Three layers: (1) `image_helper.py` — pure function for image extraction/relinking; (2) `main.py` — CLI orchestration with hash/skip/DB logic; (3) tests. Changes are isolated and independently testable.

**Tech Stack:** Python 3.12+, typer, sqlite3 (stdlib), hashlib (stdlib), tempfile (stdlib)

---

### Task 1: Fix asset hash filename + remove sequential from image_helper

**Files:**
- Modify: `src/kbmate_cli/image_helper.py:35-58`
- Test: `tests/test_image_helper.py`

- [ ] **Step 1: Update hash naming test to expect `hash[4:]` filenames**

```python
# In test_image_helper.py, update test_extract_and_relink_images_hash_naming:

def test_extract_and_relink_images_hash_naming():
    content1 = b"hello world image 1"
    content2 = b"hello world image 2"
    md_content = (
        "![](/tmp/src/doc-0001-01.png)\n"
        "![](/tmp/src/doc-0001-02.png)"
    )
    src_dir = Path("/tmp/test_hash_src")
    dst_dir = Path("/tmp/test_hash_dst")
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "doc-0001-01.png").write_bytes(content1)
    (src_dir / "doc-0001-02.png").write_bytes(content2)

    hash1 = hashlib.sha256(content1).hexdigest()
    hash2 = hashlib.sha256(content2).hexdigest()

    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir))

    assert (dst_dir / hash1[:2] / hash1[2:4] / f"{hash1[4:]}.png").exists()
    assert (dst_dir / hash2[:2] / hash2[2:4] / f"{hash2[4:]}.png").exists()
    assert f"assets/{hash1[:2]}/{hash1[2:4]}/{hash1[4:]}.png" in result
    assert f"assets/{hash2[:2]}/{hash2[2:4]}/{hash2[4:]}.png" in result
```

- [ ] **Step 2: Update dedup test to expect `hash[4:]` filenames**

```python
# test_extract_and_relink_images_dedup:
def test_extract_and_relink_images_dedup():
    content = b"duplicate content"
    md_content = (
        "![](/tmp/src_dedup/img-a.png)\n"
        "![](/tmp/src_dedup/img-b.png)"
    )
    src_dir = Path("/tmp/test_dedup_src")
    dst_dir = Path("/tmp/test_dedup_dst")
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "img-a.png").write_bytes(content)
    (src_dir / "img-b.png").write_bytes(content)

    hash_hex = hashlib.sha256(content).hexdigest()
    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir))

    hash_file = dst_dir / hash_hex[:2] / hash_hex[2:4] / f"{hash_hex[4:]}.png"
    assert hash_file.exists()
    expected_ref = f"assets/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex[4:]}.png"
    assert result.count(expected_ref) == 2
```

- [ ] **Step 3: Run updated hash tests — they should fail**

Run: `uv run pytest tests/test_image_helper.py::test_extract_and_relink_images_hash_naming tests/test_image_helper.py::test_extract_and_relink_images_dedup -v`
Expected: FAIL (hash[4:] paths don't exist yet)

- [ ] **Step 4: Update `extract_and_relink_images` — remove `sequential` parameter, fix hash filename**

Change function signature and body:

```python
def extract_and_relink_images(markdown: str, src_dir: str, dst_dir: str) -> str:
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)
    dst_path.mkdir(parents=True, exist_ok=True)

    img_pattern = re.compile(r'!\[.*?\]\(([^)]+)\)')

    for match in img_pattern.finditer(markdown):
        img_path = match.group(1)
        filename = Path(img_path).name
        src_file = next(src_path.rglob(filename), None)
        if src_file is not None and src_file.is_file():
            content = src_file.read_bytes()
            hash_hex = hashlib.sha256(content).hexdigest()
            hash_prefix = hash_hex[:2]
            hash_sub = hash_hex[2:4]
            hash_dir = dst_path / hash_prefix / hash_sub
            hash_dir.mkdir(parents=True, exist_ok=True)
            dst_file = hash_dir / f"{hash_hex[4:]}{src_file.suffix}"
            if not dst_file.exists():
                shutil.move(str(src_file), str(dst_file))
            else:
                src_file.unlink()
            old_ref = match.group(0)
            ref_parts = ["assets", hash_prefix, hash_sub, f"{hash_hex[4:]}{src_file.suffix}"]
            new_ref = f"![]({'/'.join(ref_parts)})"
            result = result.replace(old_ref, new_ref, 1)

    return result
```

Note: the `result = markdown` and `result = re.sub(...)` lines should remain.

- [ ] **Step 5: Remove sequential test + ref_subdir test from test_image_helper.py**

Remove these two test functions:
- `test_extract_and_relink_images` (sequential)
- `test_extract_and_relink_images_hash_ref_subdir` (ref_subdir no longer used)

- [ ] **Step 6: Run all image_helper tests**

Run: `uv run pytest tests/test_image_helper.py -v`
Expected: All PASS (only hash-based tests remain)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(image_helper): drop sequential param, fix hash filename to use hash[4:]"
```

---

### Task 2a: Remove layout/seqname from main.py (deletion, no TDD)

**Files:**
- Modify: `src/kbmate_cli/main.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Update `_convert_pdf` and `_convert_docx` — remove `sequential` and `ref_subdir` params**

```python
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
```

- [ ] **Step 2: Simplify `convert_single` — drop `layout`, `relative_to`, `assets_seqname` params and related code**

Replace the `_md_path` call with inline sanitization (`re.sub(r'[^a-zA-Z0-9_\-.]', '_', source_path.stem)` or simply `source_path.stem` since it's only used for a temp dir name), drop the params, remove the seqname branch:

```python
import re

def _sanitize_stem(name: str) -> str:
    return re.sub(r'[^\w.\-]', '_', name)

def convert_single(source_path: Path, output_dir: Path) -> None:
    ext = source_path.suffix.lower()
    converter = _CONVERTERS.get(ext)
    if converter is None:
        fmts = ", ".join(_CONVERTERS)
        raise ValueError(f"unsupported format: {ext} (supported: {fmts})")

    assets_parent = output_dir / "assets"
    safe_stem = _sanitize_stem(source_path.stem)

    assets_dir = assets_parent / safe_stem
    converts_dir = output_dir / "converts"
    converts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    markdown_content = converter(source_path, assets_dir, assets_parent)

    md_path = converts_dir / f"{safe_stem}.md"
    md_path.write_text(markdown_content, encoding="utf-8")

    if assets_dir.exists() and not any(assets_dir.iterdir()):
        assets_dir.rmdir()

    typer.echo(f"Converted: {source_path} -> {md_path}")
```

Note: this is a transitional step — hash skip, tempfile, and DB will come in Task 2b.

- [ ] **Step 3: Remove unused imports in main.py**

Remove:
- `from typing import Literal`
- `from pymupdf4llm.helpers.utils import md_path as _md_path`

Add:
- `import re`

- [ ] **Step 4: Simplify `convert` command — remove `--assets-seqname`**

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
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        if temp_path:
            print_cleanup_hint(temp_path)
```

- [ ] **Step 5: Simplify `bulk_convert` — remove `--output-layout` and `--assets-seqname`**

```python
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
```

- [ ] **Step 6: Remove obsolete tests from test_cli.py**

Remove these test functions:
- `test_bulk_convert_assets_seqname_flag`
- `test_bulk_convert_recursive_dir_mirror`
- `test_bulk_convert_file_list_rejects_mirror`
- `test_bulk_convert_invalid_layout`
- `test_convert_single_mirror_relative_to_fails`

- [ ] **Step 7: Update tests that used removed options — remove flags from invoke calls**

The remaining bulk_convert tests (`test_bulk_convert_recursive_dir_flat`, `test_bulk_convert_file_list`, etc.) already don't use `--output-layout` or `--assets-seqname`, so no change needed for them.

Update `test_convert_pdf_with_spaces_in_filename`: the output path format will change (no more `assets/<safe_stem>/` — actually this is still transitional, the hash paths come in 2b). For now just remove the `--assets-seqname` from any test that uses it. (None of the remaining tests do.)

- [ ] **Step 8: Run tests to confirm deletion changes pass**

Run: `uv run pytest -v`
Expected: Some failures (hash path tests in image_helper + potentially the convert tests with hash paths)

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(main): drop output-layout and assets-seqname options"
```

---

### Task 2b: Add hash skip + tempfile + SQLite DB (TDD)

**Files:**
- Modify: `src/kbmate_cli/main.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write tests for new features**

Add these test functions to `test_cli.py`:

```python
def test_convert_skip_duplicate():
    pdf = FIXTURE_DIR / "eigent README CN.pdf"
    out = Path("/tmp/test_cli_skip_dup")
    result1 = runner.invoke(app, ["convert", str(pdf), "--output-dir", str(out)])
    assert result1.exit_code == 0
    result2 = runner.invoke(app, ["convert", str(pdf), "--output-dir", str(out)])
    assert result2.exit_code == 0
    assert "Skipped" in result2.stdout


def test_convert_skip_by_hash_content(tmp_path):
    src1 = tmp_path / "doc1.pdf"
    src2 = tmp_path / "doc2.pdf"
    content = b"same content"
    src1.write_bytes(content)
    src2.write_bytes(content)

    hash_hex = hashlib.sha256(content).hexdigest()
    out = tmp_path / "out"

    result1 = runner.invoke(app, ["convert", str(src1), "--output-dir", str(out)])
    assert result1.exit_code == 0

    result2 = runner.invoke(app, ["convert", str(src2), "--output-dir", str(out)])
    assert result2.exit_code == 0
    assert "Skipped" in result2.stdout

    md_path = out / "converts" / hash_hex[:2] / hash_hex[2:4] / f"{hash_hex[4:]}.md"
    assert md_path.exists()


def test_convert_records_db():
    pdf = FIXTURE_DIR / "eigent README CN.pdf"
    out = Path("/tmp/test_cli_db")
    runner.invoke(app, ["convert", str(pdf), "--output-dir", str(out)])
    db_path = out / "kbmate.db"
    assert db_path.exists()
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT source_hash, source_name FROM conversions"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[1] == "eigent README CN.pdf"


def test_convert_skip_does_not_record_db(tmp_path):
    src = tmp_path / "test.pdf"
    src.write_bytes(b"some content")
    out = tmp_path / "out"

    hash_hex = hashlib.sha256(b"some content").hexdigest()
    md_path = out / "converts" / hash_hex[:2] / hash_hex[2:4] / f"{hash_hex[4:]}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("pre-existing")

    result = runner.invoke(app, ["convert", str(src), "--output-dir", str(out)])
    assert "Skipped" in result.stdout
    db_path = out / "kbmate.db"
    assert not db_path.exists()
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `uv run pytest tests/test_cli.py::test_convert_skip_duplicate tests/test_cli.py::test_convert_skip_by_hash_content tests/test_cli.py::test_convert_records_db tests/test_cli.py::test_convert_skip_does_not_record_db -v`
Expected: FAIL (hash skip + DB not implemented yet)

- [ ] **Step 3: Add `_record_conversion` helper + imports to main.py**

Add to imports:
```python
import hashlib
import sqlite3
import tempfile
```

Add new function:
```python
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
```

- [ ] **Step 4: Update `convert_single` — add hash skip + tempfile + DB logging**

```python
def convert_single(source_path: Path, output_dir: Path) -> None:
    ext = source_path.suffix.lower()
    converter = _CONVERTERS.get(ext)
    if converter is None:
        fmts = ", ".join(_CONVERTERS)
        raise ValueError(f"unsupported format: {ext} (supported: {fmts})")

    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
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
```

- [ ] **Step 5: Run all tests to verify everything passes**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add source hash skip, tempfile extraction, and SQLite record DB"
```

---

### Task 3: Version bump

**Files:**
- Modify: `pyproject.toml:3`

- [ ] **Step 1: Bump version to 1.0.0**

Change `pyproject.toml` line 3:
```
version = "0.4.0"  →  version = "1.0.0"
```

- [ ] **Step 2: Run all tests one last time**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: bump version to 1.0.0"
```
