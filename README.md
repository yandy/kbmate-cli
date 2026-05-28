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

# 转换 DOCX 文件
kbmate convert 文档.docx

# 批量转换目录下所有文档
kbmate bulk-convert -r ./documents

# 批量转换，镜像输入目录结构
kbmate bulk-convert -r ./documents --output-layout mirror

# 从文件列表批量转换
kbmate bulk-convert -f filelist.txt

# 使用顺序图片命名（默认基于 SHA256 哈希去重）
kbmate convert 文档.pdf --assets-seqname
```

## 命令参考

### `kbmate convert` — 单个文档转换

| 参数 | 说明 |
|------|------|
| `SOURCE_FILE` | 输入文件路径或 URL（`.pdf` / `.docx` / `http(s)://` / `file://`） |
| `--output-dir` | 输出基础目录（默认 `raw`） |
| `--assets-seqname` | 使用顺序命名 `image-001.png` 而非 SHA256 哈希 |

### `kbmate bulk-convert` — 批量转换

| 参数 | 说明 |
|------|------|
| `-r` / `--recursive` | 递归扫描目录下的所有 `.pdf` / `.docx` |
| `-f` / `--file-list` | 从文本文件读取文件列表（每行一个路径或 URL） |
| `--output-dir` | 输出基础目录（默认 `raw`） |
| `--output-layout` | 输出布局：`flat`（默认，展平）或 `mirror`（镜像目录结构，仅 `-r`） |
| `--assets-seqname` | 使用顺序图片命名而非哈希 |

`-r` 和 `-f` 必须二选一。

## 输出目录结构

**默认（SHA256 哈希命名）：**
```
{output_dir}/
├── assets/
│   └── a1/
│       └── b2/
│           └── a1b2...fullhash.png
└── converts/
    └── {文件名}.md
```

**顺序命名（`--assets-seqname`）：**
```
{output_dir}/
├── assets/
│   └── {文件名}/
│       ├── image-001.png
│       └── image-002.png
└── converts/
    └── {文件名}.md
```

## 依赖

- Python >= 3.12
- 系统需安装 `pandoc`（用于 DOCX → Markdown 转换）
- 运行时：`typer`、`pymupdf4llm`、`pypandoc`

## 开发

```bash
uv sync --dev     # 安装所有依赖（含开发依赖）
uv run pytest     # 运行测试（含覆盖率检查）
```
