# URL 源文件支持 — 设计文档

## 概述

`kbmate convert` 命令目前只接受本地文件路径作为 `source_file` 参数。本特性使其能够自动检测 URL（`http://` / `https://` 开头），从远端下载文件到临时目录后再进行转换。

## 方案选择

采用 **方案 1：新增 `url_downloader.py` 模块**，职责清晰、测试方便、零新增依赖。

## 详细设计

### 1. URL 自动检测

`convert` 函数的 `source_file` 参数检测规则：

- 以 `http://` 或 `https://` 开头 → 视为远程 URL，走下载流程
- 以 `file://` 开头 → 解析为本地文件路径，走现有本地路径逻辑
- 否则 → 保持原有本地文件路径逻辑

`file://` 路径通过 `urllib.parse.urlparse` 解析后取 `path` 部分，支持绝对路径（`file:///home/user/doc.pdf`）和相对路径（`file://../doc.pdf`）。

### 2. 新模块 `src/kbmate_cli/url_downloader.py`

提供以下函数：

| 函数 | 签名 | 说明 |
|------|------|------|
| `is_url(s)` | `(s: str) -> bool` | 检测是否 http/https 开头 |
| `probe_content_type(url)` | `(url: str) -> str | None` | HEAD 请求获取 Content-Type |
| `guess_ext_from_url(url)` | `(url: str) -> str | None` | 从 URL 路径提取扩展名 |
| `resolve_file_type(url)` | `(url: str) -> str` | probe 优先 + guess fallback，返回后缀（`.pdf` / `.docx`） |
| `download_to_temp(url, suffix)` | `(url: str, suffix: str) -> Path` | 下载到 `tempfile.gettempdir()`，返回 Path |
| `print_cleanup_hint(path)` | `(path: Path) -> None` | 打印提示信息，告知用户临时文件位置并可手动删除 |

### 3. `main.py` 改动

在 `convert` 函数开头插入 URL 检测分支：

```
if is_url(source_file):
    suffix = resolve_file_type(source_file)
    temp_path = download_to_temp(source_file, suffix)
    try:
        # 将 temp_path 作为 source_file 传给现有逻辑
        ... 复用现有路径校验 + 转换流程...
    finally:
        print_cleanup_hint(temp_path)
else:
    ... 现有逻辑不变 ...
```

### 4. 文件类型检测策略

1. 先发 HEAD 请求，读取 `Content-Type` header
   - `application/pdf` → `.pdf`
   - `application/vnd.openxmlformats-officedocument.wordprocessingml.document` → `.docx`
2. 如果 HEAD 请求失败或 Content-Type 不匹配，fallback 到 URL 路径扩展名
3. 两者都不可识别 → 抛错误提示不支持的格式

### 5. 错误处理

- 网络错误（超时、连接拒绝、DNS 解析失败）→ `typer.Exit` 输出清晰中文提示
- 下载文件大小为 0 → 报错并退出
- Content-Type 和 URL 扩展名都无法识别 → 提示无法识别文件类型
- 临时文件写入失败 → 报错并退出

### 6. 临时文件管理

- 下载到 `tempfile.gettempdir()` / `kbmate-*` 命名的临时文件
- 转换完成后不自动删除，而是打印消息：
  `临时文件已保存至: /tmp/kbmate-xxxxx/xxx.pdf，如不需要请手动删除`
- 用户自行决定何时清理

### 7. 测试计划

新增测试文件 `tests/test_url_downloader.py`：

| 测试 | 说明 |
|------|------|
| `test_is_url_http` | http 开头返回 True |
| `test_is_url_https` | https 开头返回 True |
| `test_is_url_local_path` | 本地路径返回 False |
| `test_guess_ext_from_url_pdf` | URL 含 .pdf 返回 `.pdf` |
| `test_guess_ext_from_url_docx` | URL 含 .docx 返回 `.docx` |
| `test_guess_ext_from_url_no_ext` | URL 无扩展名返回 None |
| `test_resolve_file_type_probe_pdf` | Content-Type 为 PDF 时识别 |
| `test_resolve_file_type_probe_docx` | Content-Type 为 DOCX 时识别 |
| `test_resolve_file_type_fallback_to_url` | probe 失败时 fallback 到 URL |
| `test_resolve_file_type_no_match` | 均无匹配时抛出异常 |
| `test_download_to_temp` | 下载成功返回有效 Path（mock 网络） |
| `test_download_to_temp_network_error` | 网络错误时抛出异常 |

更新 `tests/test_cli.py` 添加一个 CLI 集成测试（mock 下载），验证 URL 路径能走通 `convert` 命令。

### 8. 不做的事

- 不支持 `ftp://` 等其他协议
- 不添加认证（Basic Auth、Token 等）
- 不支持重定向跟随之外的 HTTP 特性
- 不缓存下载文件（每次都是新下载）
