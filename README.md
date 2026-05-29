# kbmate-cli

知识库管家 CLI — 将 PDF / DOCX 文档转化为 Markdown，并自动提取内嵌图片。

`kbmate` 是面向知识库场景的命令行工具箱，当前聚焦于**文档入库**环节，支持单个和批量转换，可通过 URL 远程获取文档。

## 安装

```bash
# 全局安装（作为命令行工具）
uv tool install git+https://github.com/yandy/kbmate-cli.git

# 或添加到项目依赖
uv add git+https://github.com/yandy/kbmate-cli.git
```

## 使用

```bash
# 转换单个本地文档
kbmate convert 文档.pdf

# 从 URL 转换
kbmate convert https://example.com/paper.pdf

# file:// URL 转换
kbmate convert file:///path/to/文档.pdf

# 转换 DOCX 文件
kbmate convert 文档.docx

# 批量转换目录下所有文档
kbmate bulk-convert -r ./documents

# 从文件列表批量转换
kbmate bulk-convert -f filelist.txt
```

## 命令参考

### `kbmate convert` — 单个文档转换

| 参数 | 说明 |
|------|------|
| `SOURCE_FILE` | 输入文件路径或 URL（`.pdf` / `.docx` / `http(s)://` / `file://`） |
| `--output-dir` | 输出基础目录（默认 `raw`） |

### `kbmate bulk-convert` — 批量转换

| 参数 | 说明 |
|------|------|
| `-r` / `--recursive` | 递归扫描目录下的所有 `.pdf` / `.docx` |
| `-f` / `--file-list` | 从文本文件读取文件列表（每行一个路径或 URL） |
| `--output-dir` | 输出基础目录（默认 `raw`） |

`-r` 和 `-f` 必须二选一。

### 特性

- **来源去重**：基于 SHA256 文件哈希，同一内容只会转换一次
- **图片去重**：内嵌图片基于 SHA256 内容哈希去重，相同图片只存一份
- **转换记录**：自动在输出目录创建 `kbmate.db`（SQLite），记录每次转换的源文件哈希与文件名
- **自动跳过**：Markdown 已存在（相同源哈希）时自动跳过，不重复转换
- **URL 支持**：自动识别 `http(s)://` 和 `file://`，下载后转换，清理前提示临时文件位置

## 输出目录结构

```
{output_dir}/
├── assets/
│   └── ab/
│       └── cd/
│           └── ef123456...rest.png
├── converts/
│   └── ab/
│       └── cd/
│           └── ef123456...rest.md
└── kbmate.db
```

- `converts/` — 按源文件 SHA256 哈希分两级子目录存放 `.md` 文件（路径 `hash[:2]/hash[2:4]/hash[4:].md`）
- `assets/` — 按图片内容 SHA256 哈希分两级子目录存放图片（路径 `hash[:2]/hash[2:4]/hash[4:].ext`）
- `kbmate.db` — SQLite 数据库，记录转换历史

## 依赖

- Python >= 3.12
- 系统需安装 `pandoc`（用于 DOCX → Markdown 转换）
- 运行时：`typer>=0.15.0`、`pymupdf4llm`、`pypandoc`

## 开发

```bash
uv sync --dev     # 安装所有依赖（含开发依赖）
uv run pytest     # 运行测试（含覆盖率检查，要求 >= 85%）
```

### CI

项目使用 GitHub Actions 自动运行测试，覆盖 Python 3.12 / 3.13，含 `pandoc` 系统依赖安装。
