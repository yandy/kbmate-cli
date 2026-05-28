# Assets Hash Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--assets-seqname` flag to `convert`/`bulk-convert`; default image naming uses SHA256 content hash with git-style two-level directory.

**Architecture:** `extract_and_relink_images()` in `image_helper.py` receives `sequential` and `ref_subdir` parameters. Hash mode computes SHA256, stores under `dst_dir/{hash[:2]}/{hash[2:4]}/{hash64}.ext`, deduplicates. Call chain: CLI → `convert_single` → `_convert_pdf`/`_convert_docx` → `extract_and_relink_images`.

**Tech Stack:** Python 3.12+, `hashlib` (stdlib), `shutil` (stdlib), `typer`

---

## File Structure

| File | Responsibility | Change |
|------|---------------|--------|
| `src/kbmate_cli/image_helper.py` | Hash computation, file move, ref rewrite | Add `sequential`/`ref_subdir` params, hash naming path |
| `src/kbmate_cli/main.py` | CLI commands, orchestration | Add `--assets-seqname` option, propagate through call chain |
| `tests/test_image_helper.py` | Test hash naming logic | Add hash naming + dedup + ref_subdir tests |
| `tests/test_cli.py` | CLI integration tests | Add `--assets-seqname` integration test |

---

### Task 1: Update `extract_and_relink_images` with hash naming

**Files:**
- Modify: `src/kbmate_cli/image_helper.py`
- Test: `tests/test_image_helper.py`

- [ ] **Step 1: Write failing test for hash naming**

```python
import hashlib
from kbmate_cli.image_helper import extract_and_relink_images

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

    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir), sequential=False)

    assert (dst_dir / hash1[:2] / hash1[2:4] / f"{hash1}.png").exists()
    assert (dst_dir / hash2[:2] / hash2[2:4] / f"{hash2}.png").exists()
    assert f"assets/{hash1[:2]}/{hash1[2:4]}/{hash1}.png" in result
    assert f"assets/{hash2[:2]}/{hash2[2:4]}/{hash2}.png" in result
    assert "image-001" not in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_image_helper.py::test_extract_and_relink_images_hash_naming -v`
Expected: FAIL — `extract_and_relink_images` doesn't accept `sequential` keyword

- [ ] **Step 3: Add `sequential` and `ref_subdir` params to `extract_and_relink_images`**

```python
import hashlib

def extract_and_relink_images(
    markdown: str,
    src_dir: str,
    dst_dir: str,
    *,
    sequential: bool = False,
    ref_subdir: str = "",
) -> str:
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)
    dst_path.mkdir(parents=True, exist_ok=True)

    img_pattern = re.compile(r'!\[.*?\]\(([^)]+)\)')
    counter = 1
    result = markdown

    for match in img_pattern.finditer(markdown):
        img_path = match.group(1)
        filename = Path(img_path).name
        src_file = next(src_path.rglob(filename), None)
        if src_file is not None and src_file.is_file():
            if sequential:
                new_name = f"image-{counter:03d}{src_file.suffix}"
                dst_file = dst_path / new_name
                shutil.move(str(src_file), str(dst_file))
                old_ref = match.group(0)
                new_ref = f"![](assets/{dst_path.name}/{new_name})"
                result = result.replace(old_ref, new_ref, 1)
                counter += 1
            else:
                content = src_file.read_bytes()
                hash_hex = hashlib.sha256(content).hexdigest()
                hash_prefix = hash_hex[:2]
                hash_sub = hash_hex[2:4]
                hash_dir = dst_path / hash_prefix / hash_sub
                hash_dir.mkdir(parents=True, exist_ok=True)
                dst_file = hash_dir / f"{hash_hex}{src_file.suffix}"
                if not dst_file.exists():
                    shutil.move(str(src_file), str(dst_file))
                else:
                    src_file.unlink()
                old_ref = match.group(0)
                ref_parts = [p for p in ("assets", ref_subdir, hash_prefix, hash_sub, f"{hash_hex}{src_file.suffix}") if p]
                new_ref = f"![]({'/'.join(ref_parts)})"
                result = result.replace(old_ref, new_ref, 1)

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_image_helper.py::test_extract_and_relink_images_hash_naming -v`
Expected: PASS

- [ ] **Step 5: Write test for deduplication**

```python
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

    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir), sequential=False)

    # Only one file on disk
    hash_file = dst_dir / hash_hex[:2] / hash_hex[2:4] / f"{hash_hex}.png"
    assert hash_file.exists()
    # Both refs point to the same hash path
    expected_ref = f"assets/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex}.png"
    assert result.count(expected_ref) == 2
```

- [ ] **Step 6: Run dedup test**

Run: `uv run pytest tests/test_image_helper.py::test_extract_and_relink_images_dedup -v`
Expected: PASS

- [ ] **Step 7: Write test for `ref_subdir` in hash mode**

```python
def test_extract_and_relink_images_hash_ref_subdir():
    content = b"some content"
    md_content = "![](/tmp/src_ref/img.png)"
    src_dir = Path("/tmp/test_ref_src")
    dst_dir = Path("/tmp/test_ref_dst")
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "img.png").write_bytes(content)

    hash_hex = hashlib.sha256(content).hexdigest()
    result = extract_and_relink_images(
        md_content, str(src_dir), str(dst_dir),
        sequential=False, ref_subdir="subdir",
    )

    expected = f"assets/subdir/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex}.png"
    assert expected in result
```

- [ ] **Step 8: Run ref_subdir test**

Run: `uv run pytest tests/test_image_helper.py::test_extract_and_relink_images_hash_ref_subdir -v`
Expected: PASS

- [ ] **Step 9: Run all image helper tests**

Run: `uv run pytest tests/test_image_helper.py -v`
Expected: All 5 tests pass (3 new + 2 existing)

- [ ] **Step 10: Commit**

```bash
git add src/kbmate_cli/image_helper.py tests/test_image_helper.py
git commit -m "feat: add hash-based image naming with git-style directory structure"
```

---

### Task 2: Wire `--assets-seqname` through CLI chain

**Files:**
- Modify: `src/kbmate_cli/main.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI test for `--assets-seqname`**

```python
def test_convert_assets_seqname_flag_in_help():
    result = runner.invoke(app, ["convert", "--help"])
    assert result.exit_code == 0
    assert "--assets-seqname" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_convert_assets_seqname_flag_in_help -v`
Expected: FAIL — `--assets-seqname` not yet added

- [ ] **Step 3: Add `assets_seqname` parameter to `convert` and `bulk_convert`**

```python
@app.command()
def convert(
    source_file: str = typer.Argument(..., help="Path or URL to the .docx or .pdf file"),
    output_dir: str = typer.Option("raw", help="Output directory"),
    assets_seqname: bool = typer.Option(False, "--assets-seqname", help="Use sequential naming for asset images instead of content hash"),
):
    ...
    try:
        convert_single(src, Path(output_dir), assets_seqname=assets_seqname)
    ...
```

```python
@app.command()
def bulk_convert(
    recursive: str = typer.Option(None, "-r", "--recursive", help="Directory to scan recursively"),
    file_list: str = typer.Option(None, "-f", "--file-list", help="File containing one source per line"),
    output_dir: str = typer.Option("raw", help="Output directory"),
    output_layout: str = typer.Option("flat", "--output-layout", help="Output layout: flat or mirror"),
    assets_seqname: bool = typer.Option(False, "--assets-seqname", help="Use sequential naming for asset images instead of content hash"),
):
    ...
    for src_path in _collect_files_from_dir(root):
        try:
            convert_single(src_path, out, layout=output_layout, relative_to=root, assets_seqname=assets_seqname)
        ...
    for line in lines:
        try:
            convert_single(src, out, layout=output_layout, assets_seqname=assets_seqname)
        ...
```

- [ ] **Step 4: Update `convert_single` signature and implementation**

```python
def convert_single(
    source_path: Path,
    output_dir: Path,
    *,
    layout: Literal["flat", "mirror"] = "flat",
    relative_to: Path | None = None,
    assets_seqname: bool = False,
) -> None:
    ...
    assets_dir = assets_parent / rel / safe_stem
    converts_dir = output_dir / "converts" / rel
    converts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    if assets_seqname:
        markdown_content = converter(source_path, assets_dir, assets_dir, sequential=True)
    else:
        hash_base = assets_parent / rel
        hash_base.mkdir(parents=True, exist_ok=True)
        ref_subdir = "" if rel == Path(".") else str(rel)
        markdown_content = converter(source_path, assets_dir, hash_base, sequential=False, ref_subdir=ref_subdir)
    ...
```

- [ ] **Step 5: Update `_convert_pdf` and `_convert_docx` signatures**

```python
def _convert_pdf(src: Path, src_dir: Path, dst_dir: Path, *, sequential: bool = False, ref_subdir: str = "") -> str:
    from kbmate_cli.pdf_converter import convert_pdf
    from kbmate_cli.image_helper import extract_and_relink_images
    md = convert_pdf(str(src), str(src_dir))
    return extract_and_relink_images(md, str(src_dir), str(dst_dir), sequential=sequential, ref_subdir=ref_subdir)


def _convert_docx(src: Path, src_dir: Path, dst_dir: Path, *, sequential: bool = False, ref_subdir: str = "") -> str:
    from kbmate_cli.docx_converter import convert_docx
    from kbmate_cli.image_helper import normalize_image_refs, extract_and_relink_images
    pandoc_output = src_dir / "pandoc_output"
    md = convert_docx(str(src), str(pandoc_output))
    md = normalize_image_refs(md)
    md = extract_and_relink_images(md, str(pandoc_output), str(dst_dir), sequential=sequential, ref_subdir=ref_subdir)
    if pandoc_output.exists():
        import shutil
        shutil.rmtree(pandoc_output)
    return md
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_convert_assets_seqname_flag_in_help -v`
Expected: PASS

- [ ] **Step 7: Add integration test for non-sequential (hash) default**

```python
@patch.dict("kbmate_cli.main._CONVERTERS", {".pdf": MagicMock(return_value="# mock")})
def test_bulk_convert_assets_seqname_flag():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pdf = root / "a.pdf"
        pdf.write_text("fake")
        out = root / "out"
        result = runner.invoke(app, [
            "bulk-convert", "-r", str(root),
            "--output-dir", str(out),
            "--assets-seqname",
        ])
        assert result.exit_code == 0

        # Sequential mode should have per-doc assets subdir
        assets_dir = out / "assets" / "a"
        assert assets_dir.exists()
```

- [ ] **Step 8: Run integration test**

Run: `uv run pytest tests/test_cli.py::test_bulk_convert_assets_seqname_flag -v`
Expected: PASS

- [ ] **Step 9: Update `test_convert_pdf_with_spaces_in_filename` to pass with hash naming**

The existing test checks for per-doc subdirectory `assets/eigent_README_CN`. With default hash naming, images no longer go to per-doc subdirs. Update the test:

```python
def test_convert_pdf_with_spaces_in_filename():
    src = FIXTURE_DIR / "eigent README CN.pdf"
    out = Path("/tmp/test_cli_spaces_output")
    result = runner.invoke(app, ["convert", str(src), "--output-dir", str(out)])
    assert result.exit_code == 0, f"Failed with output: {result.output}"
    # In default hash mode, images are under hash subdirs inside assets/
    assert (out / "assets").exists()
    # At least one hash directory level exists
    hash_dirs = list((out / "assets").glob("*"))
    assert len(hash_dirs) > 0, f"No hash dirs found in {out / 'assets'}"
```

- [ ] **Step 10: Run all existing tests**

Run: `uv run pytest tests/test_cli.py tests/test_image_helper.py -v`
Expected: All tests pass. (If any fail, fix them.)

- [ ] **Step 11: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass, coverage >= 85%

- [ ] **Step 12: Commit**

```bash
git add src/kbmate_cli/main.py src/kbmate_cli/image_helper.py tests/
git commit -m "feat: add --assets-seqname flag, default to hash-based image naming"
```
