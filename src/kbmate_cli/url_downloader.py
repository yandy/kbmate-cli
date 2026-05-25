from pathlib import Path
from urllib.parse import urlparse


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.startswith("file://")


def guess_ext_from_url(url: str) -> str | None:
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    return ext if ext in (".pdf", ".docx") else None
