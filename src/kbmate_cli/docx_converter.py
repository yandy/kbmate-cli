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
