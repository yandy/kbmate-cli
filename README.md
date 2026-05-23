# kbmate-cli

知识库管家 CLI — 管理、转换、检索你的知识资产。

`kbmate` 是面向知识库场景的命令行工具箱，围绕"文档入库 → 内容管理 → 检索使用"这条主线提供一系列功能。

## 当前功能

### 文档格式转化（`kbmate convert`）

将 `.pdf` / `.docx` 文件转化为 Markdown，并自动提取内嵌图片。

```
{output_dir}/
├── assets/
│   └── {原文件名}/
│       ├── image-001.png
│       └── image-002.png
└── converts/
    └── {原文件名}.md
```

图片引用格式：`![](/assets/{原文件名}/{图片名})`

**全局安装：**

```bash
uv tool install git+https://github.com/yandy/kbmate-cli.git
kbmate convert 文档.pdf
```

**添加到 uv project 依赖：**

```bash
uv add git+https://github.com/yandy/kbmate-cli.git
uv run kbmate convert 文档.pdf
```

## 技术栈

| 功能 | 库 |
|------|----|
| CLI 框架 | `typer` |
| PDF → Markdown | `pymupdf4llm` |
| DOCX → Markdown | `pypandoc` |

Python >= 3.12，依赖 system `pandoc`。

## 路线图

- [x] `convert` — PDF/DOCX 转 Markdown
- [ ] 更多输入格式（HTML、Markdown 规范化、图片 OCR 等）
- [ ] 知识库管理（索引、标签、搜索）
- [ ] 批量处理与管道编排
- [ ] 更多...

## 开发

```bash
uv sync          # 安装依赖
uv run pytest    # 运行测试
```
