import pytest
from pathlib import Path
from mate_cli.image_helper import normalize_image_refs, extract_and_relink_images


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

    result = extract_and_relink_images(md_content, str(src_dir), str(dst_dir))

    assert (dst_dir / "image-001.png").exists()
    assert (dst_dir / "image-002.png").exists()
    assert "/image-001.png" in result
    assert "/image-002.png" in result
    assert "doc-0001-01" not in result
