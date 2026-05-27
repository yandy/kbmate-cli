# bulk-convert 命令设计

## 动机

原 `kbmate convert` 只支持单个文件转换。当需要批量处理目录下或文件列表中的多个 PDF/DOCX 时，需要新增 `bulk-convert` 子命令，职责分离，不污染原命令。

## 命令签名

```
kbmate bulk-convert -r <目录> [--output-dir <路径>] [--output-layout {flat,mirror}]
kbmate bulk-convert -f <文件列表路径> [--output-dir <路径>] [--output-layout {flat,mirror}]
```

- `-r` / `--recursive`: 递归扫描目录下所有 `.pdf`/`.docx` 文件
- `-f` / `--file-list`: 从文本文件中按行读取文件地址（支持本地路径和 URL）
- `-r` 和 `-f` 互斥
- `--output-dir`: 输出根目录，默认 `raw`
- `--output-layout`: 输出结构布局，`flat`（默认）或 `mirror`

## 架构

```python
convert(source_file, output_dir)               # 原命令不变
  └─ convert_single(source_file, output_dir)

bulk-convert(-r DIR | -f FILE, output_dir, layout)  # 新命令
  ├─ _collect_files_from_dir(dir) / _collect_files_from_list(filelist)
  └─ for each file:
       └─ convert_single(... relative_to=...)
```

### convert_single 函数

提取现有 `convert` 命令的核心逻辑为可复用的函数：

```python
def convert_single(
    source_path: Path,
    output_dir: Path,
    layout: Literal["flat", "mirror"] = "flat",
    relative_to: Path | None = None,
) -> None:
```

- 处理单个文件的转换（不含 URL 解析 — URL 在调用前已完成下载）
- `layout="flat"`: 输出文件直接放入 `converts/` 和 `assets/`
- `layout="mirror"`: 根据 `relative_to` 保持目录层次

## 文件变更

### src/kbmate_cli/main.py

1. 提取 `convert_single()` 函数
2. 原 `convert` 命令体内改为调用 `convert_single()`
3. 新增 `bulk_convert` 命令
4. 新增辅助函数：
   - `_collect_files_from_dir(root: Path) -> list[Path]` — 递归扫描
   - `_collect_files_from_list(filelist: Path) -> list[str]` — 读取文件列表

### tests/test_cli.py

新增测试（使用 typer CliRunner）：
- `test_bulk_convert_recursive_dir_flat`
- `test_bulk_convert_recursive_dir_mirror`
- `test_bulk_convert_file_list`
- `test_bulk_convert_file_list_with_urls`
- `test_bulk_convert_mutual_exclusive_r_and_f`
- `test_bulk_convert_invalid_dir`

## 输出路径规则

假设输入目录为 `docs/`，包含 `docs/sub/a.pdf` 和 `docs/b.docx`：

### flat 模式 (默认)

```
raw/
├── converts/
│   ├── a.md
│   └── b.md
└── assets/
    ├── a/
    │   └── ... (图片文件)
    └── b/
        └── ...
```

### mirror 模式

```
raw/
├── converts/
│   ├── sub/
│   │   └── a.md
│   └── b.md
└── assets/
    ├── sub/
    │   └── a/
    │       └── ...
    └── b/
        └── ...
```

## 错误处理

- 单个文件转换失败不应中断整个批量过程，记录错误并继续
- 汇总报告：批量结束后显示成功/失败计数
- `-r` 指定的目录不存在时立即报错退出
- `-f` 指定的文件不存在或格式错误时立即报错退出
