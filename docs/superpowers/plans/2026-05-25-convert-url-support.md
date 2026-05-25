# URL 源文件支持 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `kbmate convert` 的 `source_file` 参数支持 `http://`、`https://` 和 `file://` URL。

**Architecture:** 新建 `url_downloader.py` 模块封装 URL 检测、Content-Type 探测和文件下载；`main.py` 的 `convert` 函数在开头插入 URL 检测分支。使用 `urllib.request`（stdlib），零新增依赖。

**Tech Stack:** Python 3.12, urllib (stdlib), typer

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/kbmate_cli/url_downloader.py` | 创建 | URL 检测、Content-Type 探测、下载到临时目录 |
| `src/kbmate_cli/main.py` | 修改 | 在 convert 函数开头添加 URL 检测分支 |
| `tests/test_url_downloader.py` | 创建 | url_downloader 模块的单元测试 |
| `tests/test_cli.py` | 修改 | 添加 URL 路径的 CLI 集成测试 |

---

### Task 1: `url_downloader.py` 核心逻辑 + 测试

**Files:**
- Create: `src/kbmate_cli/url_downloader.py`
- Create: `tests/test_url_downloader.py`

- [ ] **Step 1: 在 `tests/test_url_downloader.py` 中编写 `is_url` 和 `guess_ext_from_url` 的测试**

```python
import pytest
from pathlib import Path
from kbmate_cli.url_downloader import is_url, guess_ext_from_url


class TestIsUrl:
    def test_http(self):
        assert is_url("http://example.com/doc.pdf") is True

    def test_https(self):
        assert is_url("https://example.com/doc.pdf") is True

    def test_file_protocol(self):
        assert is_url("file:///home/user/doc.pdf") is True

    def test_local_path(self):
        assert is_url("/home/user/doc.pdf") is False

    def test_relative_path(self):
        assert is_url("doc.pdf") is False


class TestGuessExtFromUrl:
    def test_pdf(self):
        assert guess_ext_from_url("https://example.com/doc.pdf") == ".pdf"

    def test_docx(self):
        assert guess_ext_from_url("https://example.com/report.docx") == ".docx"

    def test_no_ext(self):
        assert guess_ext_from_url("https://example.com/download") is None

    def test_query_string(self):
        assert guess_ext_from_url("https://example.com/file.pdf?token=abc") == ".pdf"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_url_downloader.py -v`
Expected: ImportError (模块不存在)

- [ ] **Step 3: 实现 `is_url` 和 `guess_ext_from_url`**

```python
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError
import tempfile
import shutil


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.startswith("file://")


def guess_ext_from_url(url: str) -> str | None:
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    return ext if ext in (".pdf", ".docx") else None
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_url_downloader.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_url_downloader.py src/kbmate_cli/url_downloader.py
git commit -m "feat: add is_url and guess_ext_from_url to url_downloader"
```

- [ ] **Step 6: 在 `tests/test_url_downloader.py` 中编写 `probe_content_type`、`resolve_file_type` 和 `download_to_temp` 的测试**

```python
from unittest.mock import patch, MagicMock
from kbmate_cli.url_downloader import (
    is_url, guess_ext_from_url,
    probe_content_type, resolve_file_type,
    download_to_temp, print_cleanup_hint,
)


class TestProbeContentType:
    @patch("kbmate_cli.url_downloader.urlopen")
    def test_pdf_content_type(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        assert probe_content_type("https://example.com/doc") == ".pdf"

    @patch("kbmate_cli.url_downloader.urlopen")
    def test_docx_content_type(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        assert probe_content_type("https://example.com/doc") == ".docx"

    @patch("kbmate_cli.url_downloader.urlopen")
    def test_unknown_content_type(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "application/octet-stream"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        assert probe_content_type("https://example.com/doc") is None

    @patch("kbmate_cli.url_downloader.urlopen")
    def test_network_error_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("connection failed")
        assert probe_content_type("https://example.com/doc") is None


class TestResolveFileType:
    @patch("kbmate_cli.url_downloader.probe_content_type")
    def test_probe_success(self, mock_probe):
        mock_probe.return_value = ".pdf"
        assert resolve_file_type("https://example.com/doc") == ".pdf"
        mock_probe.assert_called_once()

    @patch("kbmate_cli.url_downloader.probe_content_type")
    def test_probe_fallback_to_url(self, mock_probe):
        mock_probe.return_value = None
        assert resolve_file_type("https://example.com/doc.pdf") == ".pdf"

    @patch("kbmate_cli.url_downloader.probe_content_type")
    def test_no_match_raises(self, mock_probe):
        mock_probe.return_value = None
        with pytest.raises(ValueError, match="cannot determine file type"):
            resolve_file_type("https://example.com/doc")


class TestDownloadToTemp:
    @patch("kbmate_cli.url_downloader.urlopen")
    def test_download_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"%PDF-1.4 fake content"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = download_to_temp("https://example.com/doc.pdf", ".pdf")
        assert isinstance(result, Path)
        assert result.suffix == ".pdf"
        assert result.exists()
        assert result.read_bytes() == b"%PDF-1.4 fake content"
        result.unlink()  # cleanup

    @patch("kbmate_cli.url_downloader.urlopen")
    def test_network_error_raises(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("connection refused")
        with pytest.raises(URLError):
            download_to_temp("https://example.com/doc.pdf", ".pdf")


class TestPrintCleanupHint:
    def test_prints_message(self, capsys):
        p = Path("/tmp/test_file.pdf")
        print_cleanup_hint(p)
        captured = capsys.readouterr()
        assert "/tmp/test_file.pdf" in captured.out
        assert "手动删除" in captured.out
```

- [ ] **Step 7: 运行测试验证失败**

Run: `uv run pytest tests/test_url_downloader.py -v`
Expected: New tests FAIL with ImportError or function not defined

- [ ] **Step 8: 实现 `probe_content_type`、`resolve_file_type`、`download_to_temp`、`print_cleanup_hint`**

在 `url_downloader.py` 追加：

```python
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
    tmp_file = tmp_dir / f"kbmate-{next(tempfile._get_candidate_names())}{suffix}"
    req = Request(url)
    with urlopen(req, timeout=30) as resp:
        tmp_file.write_bytes(resp.read())
    return tmp_file


def print_cleanup_hint(path: Path) -> None:
    typer.echo(f"临时文件已保存至: {path}，如不需要请手动删除")
```

需要在文件顶部添加 `import typer`。

- [ ] **Step 9: 运行测试验证通过**

Run: `uv run pytest tests/test_url_downloader.py -v`
Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add tests/test_url_downloader.py src/kbmate_cli/url_downloader.py
git commit -m "feat: add probe, download, and cleanup functions to url_downloader"
```

---

### Task 2: 集成到 CLI

**Files:**
- Modify: `src/kbmate_cli/main.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 在 `tests/test_cli.py` 中添加 URL 和 `file://` 的 CLI 集成测试**

```python
from unittest.mock import patch
from kbmate_cli.main import app


def test_convert_file_url():
    """file:// URL 应解析为本地路径并正常工作"""
    pdf = FIXTURE_DIR / "eigent README CN.pdf"
    file_url = f"file://{pdf.resolve()}"
    result = runner.invoke(app, ["convert", file_url, "--output-dir", "/tmp/test_cli_file_url"])
    assert result.exit_code == 0, f"Failed with output: {result.output}"


@patch("kbmate_cli.url_downloader.urlopen")
def test_convert_http_url(mock_urlopen):
    """http URL 应下载后转换"""
    # Mock HEAD probe
    head_resp = MagicMock()
    head_resp.headers = {"Content-Type": "application/pdf"}
    head_resp.__enter__.return_value = head_resp

    # Mock GET download
    pdf_path = FIXTURE_DIR / "eigent README CN.pdf"
    download_resp = MagicMock()
    download_resp.read.return_value = pdf_path.read_bytes()
    download_resp.__enter__.return_value = download_resp

    mock_urlopen.side_effect = [head_resp, download_resp]

    result = runner.invoke(
        app, ["convert", "https://example.com/doc.pdf", "--output-dir", "/tmp/test_cli_http_url"]
    )
    assert result.exit_code == 0, f"Failed with output: {result.output}"
    assert "临时文件已保存至" in result.stdout
```

需要补充 import：

```python
from unittest.mock import patch, MagicMock
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_cli.py::test_convert_file_url tests/test_cli.py::test_convert_http_url -v`
Expected: `test_convert_file_url` FAIL 是因为 `file://` 路径 `src.exists()` 不通过；`test_convert_http_url` 取决于 mock 行为

- [ ] **Step 3: 修改 `main.py` 添加 URL 检测分支**

在 `main.py` 开头增加 import：

```python
from kbmate_cli.url_downloader import is_url, resolve_file_type, download_to_temp, print_cleanup_hint
from urllib.parse import urlparse
```

修改 `convert` 函数，在现有 `src = Path(source_file)` 之前插入 URL 检测逻辑：

```python
@app.command()
def convert(
    source_file: str = typer.Argument(..., help="Path or URL to the .docx or .pdf file"),
    output_dir: str = typer.Option("raw", help="Output directory"),
):
    if is_url(source_file):
        if source_file.startswith("file://"):
            source_file = urlparse(source_file).path

        else:
            suffix = resolve_file_type(source_file)
            temp_path = download_to_temp(source_file, suffix)
            source_file = str(temp_path)

    src = Path(source_file)
    if not src.exists():
        typer.echo(f"Error: file not found: {source_file}", err=True)
        raise typer.Exit(code=1)

    # ... 后续代码不变 ...
```

并在 `md_path.write_text` 和 `typer.echo` 之间插入清理提示：

```python
    md_path.write_text(markdown_content, encoding="utf-8")
    typer.echo(f"Converted: {src} -> {md_path}")
    if temp_path:
        print_cleanup_hint(temp_path)
```

需要声明 `temp_path` 并在函数末尾访问，所以需要重构为在 try/finally 中处理，或使用一个变量跟踪。推荐在函数顶部声明 `temp_path = None`：

在 `src = Path(source_file)` 前添加 `temp_path = None`，然后在 `else` 分支中赋值。最后在函数末尾判断：

```python
    md_path.write_text(markdown_content, encoding="utf-8")
    typer.echo(f"Converted: {src} -> {md_path}")
    if temp_path:
        print_cleanup_hint(temp_path)
```

最终的 `convert` 函数：

```python
@app.command()
def convert(
    source_file: str = typer.Argument(..., help="Path or URL to the .docx or .pdf file"),
    output_dir: str = typer.Option("raw", help="Output directory"),
):
    temp_path: Path | None = None

    if is_url(source_file):
        if source_file.startswith("file://"):
            source_file = urlparse(source_file).path
        else:
            suffix = resolve_file_type(source_file)
            temp_path = download_to_temp(source_file, suffix)
            source_file = str(temp_path)

    src = Path(source_file)
    if not src.exists():
        typer.echo(f"Error: file not found: {source_file}", err=True)
        raise typer.Exit(code=1)

    ext = src.suffix.lower()
    if ext not in (".pdf", ".docx"):
        typer.echo(f"Error: unsupported format: {ext} (supported: .pdf, .docx)", err=True)
        raise typer.Exit(code=1)

    out_dir = Path(output_dir)
    assets_parent = out_dir / "assets"

    sanitized_ref, _ = _md_path(str(assets_parent), f"{src.stem}.x")
    safe_stem = Path(sanitized_ref).stem

    assets_dir = assets_parent / safe_stem
    converts_dir = out_dir / "converts"
    converts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    markdown_content: str = ""

    if ext == ".pdf":
        from kbmate_cli.pdf_converter import convert_pdf

        markdown_content = convert_pdf(str(src), str(assets_dir))

        from kbmate_cli.image_helper import extract_and_relink_images

        markdown_content = extract_and_relink_images(
            markdown_content, str(assets_dir), str(assets_dir)
        )

    elif ext == ".docx":
        from kbmate_cli.docx_converter import convert_docx

        pandoc_output = assets_dir / "pandoc_output"
        markdown_content = convert_docx(str(src), str(pandoc_output))

        from kbmate_cli.image_helper import normalize_image_refs, extract_and_relink_images

        markdown_content = normalize_image_refs(markdown_content)
        markdown_content = extract_and_relink_images(
            markdown_content, str(pandoc_output), str(assets_dir)
        )
        if pandoc_output.exists():
            import shutil

            shutil.rmtree(pandoc_output)

    md_path = converts_dir / f"{safe_stem}.md"
    md_path.write_text(markdown_content, encoding="utf-8")
    typer.echo(f"Converted: {src} -> {md_path}")
    if temp_path:
        print_cleanup_hint(temp_path)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_cli.py::test_convert_file_url tests/test_cli.py::test_convert_http_url -v`
Expected: Both PASS

Run: `uv run pytest` — 全部已有测试也不应被破坏
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kbmate_cli/main.py tests/test_cli.py
git commit -m "feat: integrate URL support into kbmate convert command"
```
