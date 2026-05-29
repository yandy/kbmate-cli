import hashlib
import re
import shutil
from pathlib import Path


def normalize_image_refs(markdown: str) -> str:
    result = markdown
    result = re.sub(r'\s*\{[^}]*\}', '', result)
    result = re.sub(r'\s+"[^"]*"\)', ')', result)
    return result


def extract_and_relink_images(markdown: str, src_dir: str, dst_dir: str) -> str:
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)
    dst_path.mkdir(parents=True, exist_ok=True)

    img_pattern = re.compile(r'!\[.*?\]\(([^)]+)\)')
    result = markdown

    for match in img_pattern.finditer(markdown):
        img_path = match.group(1)
        filename = Path(img_path).name
        src_file = next(src_path.rglob(filename), None)
        if src_file is not None and src_file.is_file():
            content = src_file.read_bytes()
            hash_hex = hashlib.sha256(content).hexdigest()
            hash_prefix = hash_hex[:2]
            hash_sub = hash_hex[2:4]
            hash_dir = dst_path / hash_prefix / hash_sub
            hash_dir.mkdir(parents=True, exist_ok=True)
            dst_file = hash_dir / f"{hash_hex[4:]}{src_file.suffix}"
            if not dst_file.exists():
                shutil.move(str(src_file), str(dst_file))
            else:
                src_file.unlink()
            old_ref = match.group(0)
            ref_parts = ["assets", hash_prefix, hash_sub, f"{hash_hex[4:]}{src_file.suffix}"]
            new_ref = f"![]({'/'.join(ref_parts)})"
            result = result.replace(old_ref, new_ref, 1)

    return result
