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
    counter = 1
    result = markdown

    for match in img_pattern.finditer(markdown):
        img_path = match.group(1)
        src_file = src_path / Path(img_path).name
        if src_file.exists():
            new_name = f"image-{counter:03d}{src_file.suffix}"
            dst_file = dst_path / new_name
            shutil.copy2(str(src_file), str(dst_file))
            old_ref = match.group(0)
            new_ref = f"![](/assets/{dst_path.name}/{new_name})"
            result = result.replace(old_ref, new_ref, 1)
            counter += 1

    return result
