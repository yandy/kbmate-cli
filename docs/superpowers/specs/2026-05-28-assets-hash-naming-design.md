# Assets Hash Naming Design

> **Goal:** Change the default image naming strategy in kbmate-cli from sequential (`image-001.png`) to content-addressed (SHA256 hash), with a `--assets-seqname` flag to opt into the old sequential behavior.

**Architecture:** The change is contained in `image_helper.py`'s `extract_and_relink_images()`, which receives a new `sequential` boolean parameter. The hash-naming path computes SHA256 of file content, creates a two-level directory structure (`hash[:2]/hash[2:4]/fullhash.ext`), and moves the file accordingly. Markdown references are updated to match the new paths. CLI entry points (`convert`, `bulk_convert`) expose a `--assets-seqname` flag that propagates down to the converter.

**Tech Stack:** Python 3.12+, `hashlib` (stdlib), `shutil` (stdlib)

---

## Default behavior (hash naming)

When `--assets-seqname` is NOT set:

1. For each extracted image, read its content and compute SHA256 digest (full 64-character hex string)
2. Create a two-level subdirectory under the assets directory: `hash[:2] / hash[2:4] /`
3. Move the image file to `hash[:2] / hash[2:4] / fullhash.suffix`
4. If a file with the same hash already exists at the target path, skip moving (deduplication)
5. Update the markdown image reference to point to the correct relative path: `![](assets/hash[:2]/hash[2:4]/fullhash.suffix)`

### Example

Given an image `doc-0001-01.png` with SHA256 `a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6`:

- Location: `assets/a1/b2/a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6.png`
- Markdown reference: `![](assets/a1/b2/a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6.png)`

### Deduplication

If two images in the source have identical content, they will resolve to the same hash. The second occurrence will detect the target file already exists and skip the `shutil.move`, but still update the markdown reference to point to the same path.

### Directory structure change from current

Current (sequential):
```
assets/<docname>/
├── image-001.png
├── image-002.png
```

New (hash, default):
```
assets/
├── a1/
│   └── b2/
│       └── a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6.png
└── ff/
    └── ee/
        └── ffee...png
```

> **Note:** The per-document subdirectory (`<docname>/`) is removed in hash mode — all images share the flat two-level hash structure under `assets/`.

---

## `--assets-seqname` mode (sequential, current behavior)

When `--assets-seqname` is set:

1. Uses the current `image-001.png`, `image-002.png`, ... naming
2. Images are placed in `assets/<output_layout_rel>/<docname>/` (unchanged from current)
3. Behaves identically to today's `extract_and_relink_images()`

---

## CLI changes

### `convert` command

```python
def convert(
    source_file: str = typer.Argument(...),
    output_dir: str = typer.Option("raw"),
    assets_seqname: bool = typer.Option(False, "--assets-seqname", help="Use sequential naming for asset images"),
):
```

### `bulk_convert` command

```python
def bulk_convert(
    recursive: str = typer.Option(None, "-r", "--recursive"),
    file_list: str = typer.Option(None, "-f", "--file-list"),
    output_dir: str = typer.Option("raw"),
    output_layout: str = typer.Option("flat", "--output-layout"),
    assets_seqname: bool = typer.Option(False, "--assets-seqname", help="Use sequential naming for asset images"),
):
```

### Propagation path

```
convert / bulk_convert
  └─ assets_seqname (CLI parameter)
      └─ convert_single(assets_seqname=...)
          └─ _convert_pdf(src, assets_dir, assets_seqname)
             └─ extract_and_relink_images(md, src_dir, dst_dir, sequential=...)
          └─ _convert_docx(src, assets_dir, assets_seqname)
             └─ extract_and_relink_images(md, src_dir, dst_dir, sequential=...)
```

---

## Files to modify

| File | Change |
|------|--------|
| `src/kbmate_cli/main.py` | Add `assets_seqname` to `convert`, `bulk_convert`, `convert_single`, `_convert_pdf`, `_convert_docx` |
| `src/kbmate_cli/image_helper.py` | Add `sequential: bool = False` to `extract_and_relink_images()`; implement hash-naming path |
| `tests/test_image_helper.py` | Add test cases for hash naming with directory structure |
| `tests/test_cli.py` | Add CLI integration tests (if applicable) |

---

## `image_helper.py` — new `extract_and_relink_images` signature

```python
def extract_and_relink_images(
    markdown: str,
    src_dir: str,
    dst_dir: str,
    *,
    sequential: bool = False,
) -> str:
```

When `sequential=True`:
- Use current counter-based naming (`image-001.png`)

When `sequential=False` (default):
- For each image, compute SHA256 of file contents
- Construct path: `dst_dir / hash[:2] / hash[2:4] / hash{suffix}`
- Handle deduplication (skip move if target exists)
- Update markdown references accordingly

---

## Testing

- Test hash naming produces correct directory structure: `hash[:2] / hash[2:4] / fullhash.png`
- Test deduplication: two identical images → single file on disk, correct references
- Test `--assets-seqname` flag restores sequential behavior (existing tests still pass)
- Test hash collision handling
- Test markdown refs are correctly rewritten
