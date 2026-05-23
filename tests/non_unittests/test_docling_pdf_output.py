from __future__ import annotations

import argparse
import html
import shutil
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.modules.kb.domain.enums import PdfDocumentType
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_docling import DoclingPdfMarkdownExtractor


DEFAULT_PDF_PATH = ROOT_DIR / "tests" / "testfiles" / "test drawing reading.pdf"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "tests" / "outputs" / "docling_debug" / "test_drawing_reading"
IMAGE_INDEX_NAME = "images_index.txt"
IMAGE_GALLERY_NAME = "images_gallery.html"


def render_docling_markdown(pdf_path: Path, output_dir: Path) -> Path:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_dir = output_dir / "images"
    markdown_path = output_dir / f"{pdf_path.stem}.docling.md"

    extractor = DoclingPdfMarkdownExtractor()
    extraction = extractor.extract(str(pdf_path), str(image_dir), PdfDocumentType.document)
    markdown_path.write_text(extraction.markdown, encoding="utf-8")
    write_image_index(output_dir=output_dir, image_dir=image_dir)
    return markdown_path


def _list_image_files(image_dir: Path) -> list[Path]:
    if not image_dir.is_dir():
        return []
    return sorted(path for path in image_dir.iterdir() if path.is_file())


def write_image_index(output_dir: Path, image_dir: Path) -> None:
    image_files = _list_image_files(image_dir)
    index_path = output_dir / IMAGE_INDEX_NAME
    gallery_path = output_dir / IMAGE_GALLERY_NAME

    lines = [f"图片目录: {image_dir}", f"图片数量: {len(image_files)}", ""]
    lines.extend(str(path.name) for path in image_files)
    index_path.write_text("\n".join(lines), encoding="utf-8")

    gallery_blocks: list[str] = []
    for image_path in image_files:
        rel_path = image_path.relative_to(output_dir).as_posix()
        safe_name = html.escape(image_path.name)
        gallery_blocks.append(
            "\n".join(
                [
                    '<div class="card">',
                    f"<h3>{safe_name}</h3>",
                    f'<a href="{rel_path}" target="_blank" rel="noopener noreferrer">',
                    f'<img src="{rel_path}" alt="{safe_name}">',
                    "</a>",
                    f'<p><code>{rel_path}</code></p>',
                    "</div>",
                ]
            )
        )

    gallery_html = "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8">',
            "  <title>Docling 图片预览</title>",
            "  <style>",
            "    body { font-family: Arial, sans-serif; margin: 24px; }",
            "    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }",
            "    .card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; background: #fff; }",
            "    img { width: 100%; height: auto; border: 1px solid #eee; background: #fafafa; }",
            "    code { word-break: break-all; }",
            "  </style>",
            "</head>",
            "<body>",
            f"  <h1>Docling 图片预览</h1>",
            f"  <p>图片目录: <code>{html.escape(str(image_dir))}</code></p>",
            f"  <p>图片数量: {len(image_files)}</p>",
            '  <div class="grid">',
            *gallery_blocks,
            "  </div>",
            "</body>",
            "</html>",
        ]
    )
    gallery_path.write_text(gallery_html, encoding="utf-8")


def print_summary(pdf_path: Path, markdown_path: Path) -> None:
    content = markdown_path.read_text(encoding="utf-8")
    image_dir = markdown_path.parent / "images"
    image_files = _list_image_files(image_dir)
    image_count = len(image_files)
    preview = content[:4000]
    index_path = markdown_path.parent / IMAGE_INDEX_NAME
    gallery_path = markdown_path.parent / IMAGE_GALLERY_NAME

    print(f"PDF: {pdf_path}")
    print(f"Markdown 输出: {markdown_path}")
    print(f"图片输出目录: {image_dir}")
    print(f"Markdown 字符数: {len(content)}")
    print(f"Markdown 行数: {len(content.splitlines())}")
    print(f"图片文件数: {image_count}")
    print(f"图片清单: {index_path}")
    print(f"图片预览页: {gallery_path}")
    if image_files:
        print("\n===== 图片文件列表 =====\n")
        for image_path in image_files:
            print(image_path.name)
    print("\n===== Markdown Preview Start =====\n")
    print(preview)
    if len(content) > len(preview):
        print("\n... (预览已截断，完整内容请打开输出文件查看) ...")
    print("\n===== Markdown Preview End =====")


def main() -> None:
    parser = argparse.ArgumentParser(description="使用真实 PDF 调试 Docling markdown 输出")
    parser.add_argument("--pdf", default=str(DEFAULT_PDF_PATH), help="待解析 PDF 路径")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    output_dir = Path(args.output_dir).resolve()
    markdown_path = render_docling_markdown(pdf_path=pdf_path, output_dir=output_dir)
    print_summary(pdf_path=pdf_path, markdown_path=markdown_path)


if __name__ == "__main__":
    main()
