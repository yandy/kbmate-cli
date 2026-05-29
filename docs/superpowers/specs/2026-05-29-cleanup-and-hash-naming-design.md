# Cleanup & Hash Naming Design

## Overview

Remove two legacy CLI options (`--output-layout`, `--assets-seqname`), introduce source-file hash-based markdown
output paths with automatic skip-on-duplicate, fix asset filename redundancy (already split by directory levels),
and record source hash ↔ source filename relationships in a SQLite DB.

## Changes

### 1. Remove `--output-layout`

**Files:** `src/kbmate_cli/main.py`

- `bulk_convert`: delete `--output-layout` option, remove validation (`if output_layout not in ...`) and error branches.
- `convert_single`: delete `layout` and `relative_to` parameters. `rel` is always `Path(".")`.
- The `mirror`-specific branch in `bulk_convert` file-list path is also removed.

### 2. Remove `--assets-seqname`

**Files:** `src/kbmate_cli/main.py`, `src/kbmate_cli/image_helper.py`

- `convert` and `bulk_convert`: delete `--assets-seqname` option.
- `convert_single`: delete `assets_seqname` parameter; always use hash-based naming.
- `_convert_pdf` / `_convert_docx`: delete `sequential` parameter.
- `extract_and_relink_images`: delete `sequential` parameter and its code branch (lines 35–41).

### 3. Source-file hash naming for markdown + skip-on-duplicate

**File:** `src/kbmate_cli/main.py`

In `convert_single`:

1. Compute `source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()`
2. Derive output path: `converts/<hash[:2]>/<hash[2:4]>/<hash[4:]>.md`
3. If the file already exists, print a skip message and return immediately.
4. Otherwise proceed with conversion and write to that path.

### 4. Fix redundant asset filename

**File:** `src/kbmate_cli/image_helper.py`

Currently: `assets/a1/b2/a1b2c3....png`
After fix: `assets/a1/b2/c3d4....png` (filename uses `hash[4:]`)

Affects `image_helper.py:50` (dst_file name) and `image_helper.py:56` (ref_parts).

### 5. Use `tempfile.mkdtemp()` for image extraction

**File:** `src/kbmate_cli/main.py`

- Replace `assets_parent / rel / safe_stem` temp dir creation with `tempfile.mkdtemp(dir=assets_parent)`.
- No explicit cleanup needed — OS temp dir management handles it.
- Remove the existing after-conversion cleanup logic that only removes empty dirs (`.rmdir()` on empty `safe_stem` dir).

### 6. SQLite record DB

**File:** `src/kbmate_cli/main.py`

A lightweight SQLite DB (`kbmate.db`) stored in `output_dir` to record each conversion:

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS conversions (
    source_hash TEXT NOT NULL,
    source_name TEXT NOT NULL,
    converted_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source_hash, source_name)
);
```

**Behavior:**
- Only writes to DB when an actual conversion happens (not on skip).
- `INSERT OR IGNORE` — if the same hash+name is converted again, no duplicate.
- Used purely for traceability (not for skip decision; skip is file-existence based).
- `sqlite3` is stdlib — no extra dependency.

### 7. Version bump

`pyproject.toml`: `0.4.0` → `1.0.0`

## Tests

### Remove
- `test_bulk_convert_assets_seqname_flag`
- `test_bulk_convert_recursive_dir_mirror`
- `test_bulk_convert_file_list_rejects_mirror`
- `test_bulk_convert_invalid_layout`
- `test_convert_single_mirror_relative_to_fails`
- `test_extract_and_relink_images` (sequential test)
- `test_extract_and_relink_images_hash_ref_subdir` (ref_subdir is no longer needed)

### Update
- `test_extract_and_relink_images_hash_naming`: asset paths → `hash[4:]`
- `test_extract_and_relink_images_dedup`: same
- `test_bulk_convert_recursive_dir_flat`: remove output-layout flags
- `test_bulk_convert_file_list`: remove output-layout flags
- `test_bulk_convert_file_list_with_url`: remove output-layout flags
- `test_bulk_convert_runtime_error_continues_r`: remove output-layout flags
- `test_bulk_convert_runtime_error_continues_f`: remove output-layout flags
- `test_bulk_convert_continue_on_error`: remove output-layout flags
- `test_bulk_convert_file_list_url_error`: remove output-layout flags
- `test_bulk_convert_file_list_file_not_found_with_temp`: remove output-layout flags
- remove `test_convert_single_cleans_up_empty_assets_dir` (no longer relevant)
- remove `test_bulk_convert_flat_cleans_up_empty_assets_dirs` (no longer relevant)

### Add
- `test_convert_skip_duplicate`: convert same source twice, second skips
- `test_convert_skip_by_hash_content_equivalence`: same content different filenames → skip
- `test_convert_records_db`: after conversion, `kbmate.db` has the right record
- `test_convert_skip_does_not_record_db`: skip case does not write to DB

## Files Changed / Created

| File | Type |
|------|------|
| `src/kbmate_cli/main.py` | code |
| `src/kbmate_cli/image_helper.py` | code |
| `tests/test_cli.py` | tests |
| `tests/test_image_helper.py` | tests |
| `pyproject.toml` | version |
| `output_dir/kbmate.db` | runtime artifact (sqlite, auto-created) |
