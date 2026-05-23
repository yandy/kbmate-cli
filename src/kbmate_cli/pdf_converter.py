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
