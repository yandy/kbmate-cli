# Convert docx/pdf to Markdown

## Overview

`uv run main.py convert` command converts `.docx` and `.pdf` files to markdown format. Images are extracted to an `assets` subdirectory and the markdown is saved to a `converts` subdirectory.

## Input Parameters

- **source_file**: Path to the `.docx` or `.pdf` file to convert
- **output_dir**: Output directory (default: `raw` in current directory)

## Output Structure

```
{output_dir}/
├── assets/
│   └── {原文件名}/
│       ├── image-001.png
│       └── image-002.png
└── converts/
    └── {原文件名}.md
```

## Image Reference Format

All images in the markdown file are referenced using the format:
```
![](/assets/{原文件名}/{图片名})
```
