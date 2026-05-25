from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError
import tempfile
import uuid

import typer


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.startswith("file://")


def guess_ext_from_url(url: str) -> str | None:
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    return ext if ext in (".pdf", ".docx") else None


_CONTENT_TYPE_MAP = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def probe_content_type(url: str) -> str | None:
    req = Request(url, method="HEAD")
    try:
        with urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "").split(";")[0].strip()
            return _CONTENT_TYPE_MAP.get(ct)
    except URLError:
        return None


def resolve_file_type(url: str) -> str:
    ext = probe_content_type(url)
    if ext:
        return ext
    ext = guess_ext_from_url(url)
    if ext:
        return ext
    raise ValueError(f"cannot determine file type for URL: {url}")


def download_to_temp(url: str, suffix: str) -> Path:
    tmp_dir = Path(tempfile.gettempdir())
    tmp_file = tmp_dir / f"kbmate-{uuid.uuid4().hex}{suffix}"
    req = Request(url)
    with urlopen(req, timeout=30) as resp:
        tmp_file.write_bytes(resp.read())
    return tmp_file


def print_cleanup_hint(path: Path) -> None:
    typer.echo(f"临时文件已保存至: {path}，如不需要请手动删除")
