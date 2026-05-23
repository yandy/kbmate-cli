# Convert DOCX/PDF to Markdown

## Overview

`kbmate-cli` needs a `convert` command that converts `.docx` and `.pdf` files to markdown format, with images extracted to an `assets` subdirectory and markdown saved to a `converts` subdirectory.

## Design

### CLI Entry Point

`pyproject.toml` 配置 `[project.scripts]` 入口，支持 `uv tool install` 安装为全局命令：

```toml
[project.scripts]
kbmate = "kbmate_cli.main:app"
```

安装后可直接使用 `kbmate convert <source_file>`。

### Development Usage

```bash
uv run kbmate convert <source_file> [--output-dir DIR]
```

### CLI Interface

Using `typer`:

- `source_file`: Path to `.docx` or `.pdf` file (required, positional)
- `--output-dir`: Output directory (default: `raw` in current directory)

### Project Structure

```
kbmate-cli/
├── src/
│   └── kbmate_cli/
│       ├── __init__.py
│       └── main.py          # typer app + convert command
├── evals/                    # test files
├── pyproject.toml
└── main.py                   # legacy entry (optional)
```

### Output Structure

```
{output_dir}/
├── assets/
│   └── {原文件名}/
│       ├── image-001.png
│       └── image-002.png
└── converts/
    └── {原文件名}.md
```

Image references in markdown use the format:
```
![](/assets/{原文件名}/{图片名})
```

### Library Choices

| Format | Library | Reason |
|--------|---------|--------|
| **PDF → Markdown** | `pymupdf4llm` | Lightweight, handles text/tables/images perfectly for English and Chinese PDFs. No heavy dependencies (unlike docling which requires PyTorch). |
| **DOCX → Markdown** | `pypandoc` | Thin Python wrapper around pandoc (system-installed). Correctly converts text, tables, and extracts images. Already tested against real files. |

### Dependencies

```toml
[project]
dependencies = [
    "pymupdf4llm",
    "pypandoc",
    "typer",
]

[project.scripts]
kbmate = "kbmate_cli.main:app"
```

`pandoc` must be available on the system (already installed at `/usr/bin/pandoc`).

### Architecture

```
src/kbmate_cli/main.py
  └── app = typer.Typer()
       └── convert()
            ├── detect format (.docx / .pdf)
            ├── PDF → pymupdf4llm.to_markdown(write_images=True, image_path=...)
            ├── DOCX → pypandoc.convert_file(extra_args=['--wrap=none', '--extract-media=...'])
            ├── post-process: fix image paths to match output structure
            └── write markdown to converts/{原文件名}.md
```

### Image Path Post-Processing

- **PDF**: pymupdf4llm saves images to `image_path` with filenames like `{filename}-{page}-{num}.png`. We rename/copy them to `assets/{原文件名}/image-{num:03d}.png` and update references in markdown.
- **DOCX**: pypandoc with `--extract-media` saves images to `{output_dir}/media/image{num}.png`. We move them to `assets/{原文件名}/image-{num:03d}.png` and update references in markdown. Additionally, strip pandoc's `{width="..." height="..."}` attributes from image references.

### Error Handling

- Raise clear error if `source_file` does not exist
- Raise clear error if file is neither `.docx` nor `.pdf`
- Raise clear error if `pandoc` is not found on system for DOCX conversion
- Handle conversion failures gracefully with informative messages

### Verification

Run conversion against test files in `evals/`:

```bash
uv run main.py convert evals/minimaxzh.docx
uv run main.py convert evals/minimax.pdf
uv run main.py convert evals/2412.20138v7.pdf
```

Verify:
- Markdown files are created in `raw/converts/`
- Images are extracted to `raw/assets/{原文件名}/`
- Image references in markdown use `![](/assets/{原文件名}/{图片名})` format
- Content is correctly converted (tables, images, Chinese text)
