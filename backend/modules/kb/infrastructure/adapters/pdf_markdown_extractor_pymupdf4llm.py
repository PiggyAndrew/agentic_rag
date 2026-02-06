from __future__ import annotations

import os
from typing import List

from backend.modules.kb.domain.ports import PdfMarkdownExtractorPort


class PyMuPdf4LlmPdfMarkdownExtractor(PdfMarkdownExtractorPort):
    def extract_markdown(self, pdf_path: str, image_dir: str) -> str:
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

        try:
            import pymupdf4llm  # type: ignore
        except Exception as e:
            raise RuntimeError("缺少依赖：请安装 pymupdf 与 pymupdf4llm") from e

        os.makedirs(image_dir, exist_ok=True)
        md = pymupdf4llm.to_markdown(
            pdf_path,
            write_images=True,
            image_path=image_dir,
            use_ocr=False,
        )
        if isinstance(md, list):
            page_texts: List[str] = []
            for page in md:
                page_texts.append(str(page.get("text")).strip())
            return "\n\n".join(t for t in page_texts if t).strip()
        return str(md).strip()

