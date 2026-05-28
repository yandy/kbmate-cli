import hashlib

import pytest
from pathlib import Path
from kbmate_cli.image_helper import normalize_image_refs, extract_and_relink_images


def test_normalize_image_refs_strips_pandoc_attrs():
    md = "![alt](media/image1.png \"title\"){width=\"5in\" height=\"3in\"}"
    result = normalize_image_refs(md)
    assert "{width=" not in result
    assert "{height=" not in result
    assert "\"title\"" not in result


def test_normalize_image_refs_does_not_alter_plain_refs():
    md = "![](/assets/foo/image-001.png)"
    result = normalize_image_refs(md)
    assert result == md


def test_extract_and_relink_images():
    md_content = (
        "![](/tmp/src/doc-0001-01.png)\n"
        "![](/tmp/src/doc-0001-02.png)"
    )
    src_dir = Path("/tmp/test_relink_src")
    dst_dir = Path("/tmp/test_relink_dst")
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "doc-0001-01.png").touch()
    (src_dir / "doc-0001-02.png").touch()

    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir), sequential=True)

    assert (dst_dir / "image-001.png").exists()
    assert (dst_dir / "image-002.png").exists()
    assert "![](assets/test_relink_dst/image-001.png)" in result
    assert "![](assets/test_relink_dst/image-002.png)" in result
    assert "doc-0001-01" not in result


def test_extract_and_relink_images_hash_naming():
    content1 = b"hello world image 1"
    content2 = b"hello world image 2"
    md_content = (
        "![](/tmp/src/doc-0001-01.png)\n"
        "![](/tmp/src/doc-0001-02.png)"
    )
    src_dir = Path("/tmp/test_hash_src")
    dst_dir = Path("/tmp/test_hash_dst")
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "doc-0001-01.png").write_bytes(content1)
    (src_dir / "doc-0001-02.png").write_bytes(content2)

    hash1 = hashlib.sha256(content1).hexdigest()
    hash2 = hashlib.sha256(content2).hexdigest()

    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir), sequential=False)

    assert (dst_dir / hash1[:2] / hash1[2:4] / f"{hash1}.png").exists()
    assert (dst_dir / hash2[:2] / hash2[2:4] / f"{hash2}.png").exists()
    assert f"assets/{hash1[:2]}/{hash1[2:4]}/{hash1}.png" in result
    assert f"assets/{hash2[:2]}/{hash2[2:4]}/{hash2}.png" in result
    assert "image-001" not in result


def test_extract_and_relink_images_dedup():
    content = b"duplicate content"
    md_content = (
        "![](/tmp/src_dedup/img-a.png)\n"
        "![](/tmp/src_dedup/img-b.png)"
    )
    src_dir = Path("/tmp/test_dedup_src")
    dst_dir = Path("/tmp/test_dedup_dst")
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "img-a.png").write_bytes(content)
    (src_dir / "img-b.png").write_bytes(content)

    hash_hex = hashlib.sha256(content).hexdigest()

    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir), sequential=False)

    hash_file = dst_dir / hash_hex[:2] / hash_hex[2:4] / f"{hash_hex}.png"
    assert hash_file.exists()
    expected_ref = f"assets/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex}.png"
    assert result.count(expected_ref) == 2


def test_extract_and_relink_images_hash_ref_subdir():
    content = b"some content"
    md_content = "![](/tmp/src_ref/img.png)"
    src_dir = Path("/tmp/test_ref_src")
    dst_dir = Path("/tmp/test_ref_dst")
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "img.png").write_bytes(content)

    hash_hex = hashlib.sha256(content).hexdigest()
    result = extract_and_relink_images(
        md_content, str(src_dir), str(dst_dir),
        sequential=False, ref_subdir="subdir",
    )

    expected = f"assets/subdir/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex}.png"
    assert expected in result
