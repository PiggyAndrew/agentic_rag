from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


@dataclass
class WordBox:
    text: str
    bbox: list[int]
    source: str
    block_id: str | None = None


@dataclass
class RegionBlock:
    id: str
    kind: str
    bbox: list[int]
    text: str
    source: str
    member_word_indexes: list[int] = field(default_factory=list)
    content_type: str | None = None


def normalize_bbox(bbox: Iterable[int], width: int, height: int) -> list[int]:
    left, top, right, bottom = bbox
    return [
        max(0, min(1000, int(1000 * left / width))),
        max(0, min(1000, int(1000 * top / height))),
        max(0, min(1000, int(1000 * right / width))),
        max(0, min(1000, int(1000 * bottom / height))),
    ]


def scale_bbox(bbox: Iterable[float], scale_x: float, scale_y: float) -> list[int]:
    left, top, right, bottom = bbox
    return [
        int(round(left * scale_x)),
        int(round(top * scale_y)),
        int(round(right * scale_x)),
        int(round(bottom * scale_y)),
    ]


def ensure_output_dir(path: str) -> Path:
    output_dir = Path(path).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def clean_block_text(text: str) -> str:
    lines = [" ".join(line.strip().split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def is_mostly_numeric(text: str) -> bool:
    cleaned = "".join(ch for ch in text if ch not in " ,")
    if not cleaned:
        return False
    allowed = set("0123456789./-+")
    return all(ch in allowed for ch in cleaned)


def rect_area(bbox: list[int]) -> int:
    return max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])


def rect_intersection_area(a: list[int], b: list[int]) -> int:
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    if right <= left or bottom <= top:
        return 0
    return (right - left) * (bottom - top)


def merge_bboxes(boxes: list[list[int]]) -> list[int]:
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def overlaps_significantly(a: list[int], b: list[int], threshold: float = 0.9) -> bool:
    intersection = rect_intersection_area(a, b)
    if intersection <= 0:
        return False
    smaller = max(1, min(rect_area(a), rect_area(b)))
    return intersection / smaller >= threshold


def expand_bbox(bbox: list[int], dx: int, dy: int, max_width: int, max_height: int) -> list[int]:
    return [
        max(0, bbox[0] - dx),
        max(0, bbox[1] - dy),
        min(max_width, bbox[2] + dx),
        min(max_height, bbox[3] + dy),
    ]


def bboxes_overlap(a: list[int], b: list[int]) -> bool:
    return rect_intersection_area(a, b) > 0


def build_text_regions_from_words(words: list[WordBox], image_width: int, image_height: int) -> list[RegionBlock]:
    regions: list[RegionBlock] = []
    grouped: dict[str, list[tuple[int, WordBox]]] = {}
    for index, word in enumerate(words):
        if not word.block_id:
            continue
        grouped.setdefault(word.block_id, []).append((index, word))

    for block_id, entries in grouped.items():
        boxes = [item.bbox for _, item in entries]
        text = " ".join(item.text for _, item in entries)
        bbox = merge_bboxes(boxes)
        regions.append(
            RegionBlock(
                id=block_id,
                kind="text",
                bbox=bbox,
                text=text,
                source="ocr_text_block",
                member_word_indexes=[index for index, _ in entries],
            )
        )
    regions.sort(key=lambda item: (item.bbox[1], item.bbox[0]))
    return regions


def load_pdf_page(input_path: Path, page_number: int, dpi: int) -> tuple[object, list[WordBox], list[RegionBlock], list[list[int]]]:
    try:
        import fitz  # type: ignore
        from PIL import Image  # type: ignore
    except Exception as exc:
        raise RuntimeError("请先安装 PyMuPDF 和 Pillow: pip install pymupdf pillow") from exc

    doc = fitz.open(input_path)
    try:
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"page_number={page_number} 超出范围, 文档共有 {len(doc)} 页")

        page = doc[page_number - 1]
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        page_rect = page.rect
        scale_x = pix.width / page_rect.width
        scale_y = pix.height / page_rect.height

        words: list[WordBox] = []
        block_to_word_indexes: dict[int, list[int]] = {}
        for item in page.get_text("words", sort=True):
            x0, y0, x1, y1, text, block_no, *_ = item
            cleaned = str(text or "").strip()
            if not cleaned:
                continue
            bbox = scale_bbox([x0, y0, x1, y1], scale_x=scale_x, scale_y=scale_y)
            block_id = f"pdf_block_{int(block_no)}"
            block_to_word_indexes.setdefault(int(block_no), []).append(len(words))
            words.append(WordBox(text=cleaned, bbox=bbox, source="pdf_text", block_id=block_id))

        regions: list[RegionBlock] = []
        drawing_rects: list[list[int]] = []
        for x0, y0, x1, y1, text, block_no, block_type in page.get_text("blocks", sort=True):
            bbox = scale_bbox([x0, y0, x1, y1], scale_x=scale_x, scale_y=scale_y)
            cleaned = clean_block_text(str(text or ""))
            if block_type == 0 and cleaned:
                block_id = f"pdf_block_{int(block_no)}"
                regions.append(
                    RegionBlock(
                        id=block_id,
                        kind="text",
                        bbox=bbox,
                        text=cleaned,
                        source="pdf_text_block",
                        member_word_indexes=block_to_word_indexes.get(int(block_no), []),
                    )
                )
            elif block_type == 1:
                regions.append(
                    RegionBlock(
                        id=f"pdf_image_{int(block_no)}",
                        kind="image",
                        bbox=bbox,
                        text=cleaned or "<embedded image>",
                        source="pdf_image_block",
                    )
                )
            elif block_type == 3:
                regions.append(
                    RegionBlock(
                        id=f"pdf_vector_{int(block_no)}",
                        kind="vector",
                        bbox=bbox,
                        text=cleaned or "<vector graphic>",
                        source="pdf_vector_block",
                    )
                )

        existing_image_boxes = [item.bbox for item in regions if item.kind == "image"]
        for image_index, image_info in enumerate(page.get_images(full=True)):
            xref = int(image_info[0])
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            for rect_index, rect in enumerate(rects):
                bbox = scale_bbox([rect.x0, rect.y0, rect.x1, rect.y1], scale_x=scale_x, scale_y=scale_y)
                if rect_area(bbox) <= 0:
                    continue
                if any(overlaps_significantly(bbox, other) for other in existing_image_boxes):
                    continue
                existing_image_boxes.append(bbox)
                regions.append(
                    RegionBlock(
                        id=f"pdf_image_xref_{xref}_{image_index}_{rect_index}",
                        kind="image",
                        bbox=bbox,
                        text=f"<embedded image xref={xref}>",
                        source="pdf_image_xref",
                    )
                )

        for drawing in page.get_drawings():
            rect = drawing.get("rect")
            if not rect:
                continue
            bbox = scale_bbox([rect.x0, rect.y0, rect.x1, rect.y1], scale_x=scale_x, scale_y=scale_y)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width <= 1 or height <= 1:
                continue
            drawing_rects.append(bbox)

        return image, words, regions, drawing_rects
    finally:
        doc.close()


def load_image(input_path: Path) -> object:
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:
        raise RuntimeError("请先安装 Pillow: pip install pillow") from exc
    return Image.open(input_path).convert("RGB")


def extract_ocr_content(image: object, ocr_lang: str) -> tuple[list[WordBox], list[RegionBlock]]:
    try:
        import pytesseract  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "当前输入没有可直接利用的 PDF 内嵌文字, 请安装 pytesseract 并确保系统已安装 Tesseract OCR"
        ) from exc

    data = pytesseract.image_to_data(
        image,
        lang=ocr_lang,
        output_type=pytesseract.Output.DICT,
        config="--psm 6",
    )

    words: list[WordBox] = []
    total = len(data.get("text", []))
    for index in range(total):
        text = str(data["text"][index] or "").strip()
        conf = str(data.get("conf", ["-1"] * total)[index]).strip()
        if not text:
            continue
        try:
            confidence = float(conf)
        except ValueError:
            confidence = -1.0
        if confidence < 0:
            continue
        left = int(data["left"][index])
        top = int(data["top"][index])
        width = int(data["width"][index])
        height = int(data["height"][index])
        block_id = f"ocr_block_{data.get('block_num', [0] * total)[index]}_{data.get('par_num', [0] * total)[index]}"
        words.append(
            WordBox(
                text=text,
                bbox=[left, top, left + width, top + height],
                source="tesseract_ocr",
                block_id=block_id,
            )
        )
    return words, build_text_regions_from_words(words, image_width=image.size[0], image_height=image.size[1])


def collect_page_content(
    input_path: Path,
    page_number: int,
    dpi: int,
    ocr_lang: str,
) -> tuple[object, list[WordBox], list[RegionBlock], list[list[int]]]:
    suffix = input_path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        image, words, regions, drawing_rects = load_pdf_page(input_path=input_path, page_number=page_number, dpi=dpi)
        if words:
            return image, words, regions, drawing_rects
        ocr_words, ocr_regions = extract_ocr_content(image=image, ocr_lang=ocr_lang)
        return image, ocr_words, ocr_regions, []

    if suffix in IMAGE_SUFFIXES:
        image = load_image(input_path)
        ocr_words, ocr_regions = extract_ocr_content(image=image, ocr_lang=ocr_lang)
        return image, ocr_words, ocr_regions, []

    raise ValueError(f"暂不支持的输入格式: {input_path.suffix}")


def detect_three_regions(
    image_width: int,
    image_height: int,
    text_regions: list[RegionBlock],
    drawing_rects: list[list[int]],
) -> list[RegionBlock]:
    page_bbox = [0, 0, image_width, image_height]

    frame_candidates = [
        bbox
        for bbox in drawing_rects
        if bbox[0] <= image_width * 0.05
        and bbox[1] <= image_height * 0.05
        and bbox[2] >= image_width * 0.75
        and bbox[3] >= image_height * 0.75
    ]
    sheet_frame_bbox = max(frame_candidates, key=rect_area) if frame_candidates else page_bbox

    title_candidates = [
        bbox
        for bbox in drawing_rects
        if bbox[0] >= image_width * 0.75
        and (bbox[2] - bbox[0]) >= image_width * 0.06
        and (bbox[2] - bbox[0]) <= image_width * 0.25
        and (bbox[3] - bbox[1]) >= image_height * 0.6
    ]
    right_text_boxes = [region.bbox for region in text_regions if region.bbox[0] >= image_width * 0.84]
    if title_candidates:
        title_block_bbox = max(title_candidates, key=rect_area)
        related_right_text = [bbox for bbox in right_text_boxes if bbox[0] >= title_block_bbox[0] - image_width * 0.02]
        if related_right_text:
            title_block_bbox = merge_bboxes([title_block_bbox, *related_right_text])
    elif right_text_boxes:
        title_block_bbox = merge_bboxes(right_text_boxes)
    else:
        title_block_bbox = [
            int(image_width * 0.84),
            int(image_height * 0.02),
            int(image_width * 0.98),
            int(image_height * 0.98),
        ]

    legend_candidates = [
        region.bbox
        for region in text_regions
        if region.bbox[0] <= image_width * 0.2 and region.bbox[1] <= image_height * 0.22
    ]
    legend_bbox = merge_bboxes(legend_candidates) if legend_candidates else None
    if legend_bbox:
        legend_bbox = expand_bbox(
            legend_bbox,
            dx=int(image_width * 0.01),
            dy=int(image_height * 0.01),
            max_width=image_width,
            max_height=image_height,
        )

    non_title_text_regions = [
        region
        for region in text_regions
        if region.bbox[0] < title_block_bbox[0] - image_width * 0.01
        and not (legend_bbox and overlaps_significantly(region.bbox, legend_bbox, threshold=0.8))
    ]

    elevation_label_regions = [
        region
        for region in non_title_text_regions
        if "ELEVATION" in region.text.upper()
    ]
    elevation_label_regions.sort(key=lambda item: item.bbox[1])

    final_regions = [
        RegionBlock(
            id="sheet_frame",
            kind="region",
            bbox=sheet_frame_bbox,
            text="整张图框范围",
            source="layout_heuristic",
            content_type="sheet_frame",
        ),
        RegionBlock(
            id="title_block",
            kind="region",
            bbox=title_block_bbox,
            text="图框标题栏范围",
            source="layout_heuristic",
            content_type="title_block",
        ),
    ]

    if not elevation_label_regions:
        fallback_bbox = [
            int(sheet_frame_bbox[0] + image_width * 0.05),
            int(sheet_frame_bbox[1] + image_height * 0.1),
            int(title_block_bbox[0] - image_width * 0.02),
            int(sheet_frame_bbox[3] - image_height * 0.05),
        ]
        final_regions.append(
            RegionBlock(
                id="elevation_region_1",
                kind="region",
                bbox=fallback_bbox,
                text="立面图区域，包含标注与立面标题",
                source="layout_heuristic",
                content_type="elevation_region",
            )
        )
        return final_regions

    for index, label in enumerate(elevation_label_regions):
        # Elevation titles usually sit below the view body.
        # Search a tall window above each title instead of slicing by midpoint
        # between adjacent titles, which can cut off the upper half of a view.
        band_top = max(int(sheet_frame_bbox[1] + image_height * 0.02), int(label.bbox[1] - image_height * 0.34))
        band_bottom = min(int(sheet_frame_bbox[3] - image_height * 0.02), int(label.bbox[3] + image_height * 0.08))

        label_center_x = (label.bbox[0] + label.bbox[2]) / 2
        label_right_x = label.bbox[2]
        candidate_parts: list[list[int]] = [label.bbox]
        label_text = label.text.replace("\n", " ").strip()

        nearby_left_regions = [
            region
            for region in non_title_text_regions
            if region is not label
            and abs(region.bbox[1] - label.bbox[1]) <= image_height * 0.03
            and region.bbox[2] <= label.bbox[0] + image_width * 0.03
            and region.bbox[0] >= label.bbox[0] - image_width * 0.12
        ]
        for region in nearby_left_regions:
            candidate_parts.append(region.bbox)
            label_text = f"{region.text.strip()} {label_text}".strip()

        candidate_drawings = [
            bbox
            for bbox in drawing_rects
            if rect_area(bbox) >= 25
            and bbox[0] < title_block_bbox[0] - image_width * 0.01
            and bbox[1] >= band_top - image_height * 0.02
            and bbox[3] <= band_bottom + image_height * 0.02
            and bbox[2] >= label_right_x - image_width * 0.03
            and bbox[0] <= title_block_bbox[0] - image_width * 0.04
            and abs(((bbox[0] + bbox[2]) / 2) - max(label_center_x, image_width * 0.42)) <= image_width * 0.42
            and not (legend_bbox and overlaps_significantly(bbox, legend_bbox, threshold=0.8))
        ]

        core_drawings = [
            bbox
            for bbox in candidate_drawings
            if (bbox[2] - bbox[0]) >= image_width * 0.08
            and (bbox[3] - bbox[1]) >= image_height * 0.035
        ]
        if not core_drawings:
            core_drawings = [
                bbox
                for bbox in candidate_drawings
                if (bbox[2] - bbox[0]) >= image_width * 0.04
                and (bbox[3] - bbox[1]) >= image_height * 0.02
            ]
        if core_drawings:
            core_bbox = merge_bboxes(core_drawings)
        elif candidate_drawings:
            core_bbox = merge_bboxes(candidate_drawings)
        else:
            core_bbox = label.bbox

        text_capture_bbox = expand_bbox(
            core_bbox,
            dx=int(image_width * 0.035),
            dy=int(image_height * 0.06),
            max_width=image_width,
            max_height=image_height,
        )
        text_capture_bbox[1] = max(band_top, min(text_capture_bbox[1], label.bbox[1] - int(image_height * 0.02)))
        text_capture_bbox[3] = min(band_bottom, max(text_capture_bbox[3], label.bbox[3] + int(image_height * 0.03)))
        text_capture_bbox[2] = min(text_capture_bbox[2], int(title_block_bbox[0] - image_width * 0.02))

        candidate_text = []
        for region in non_title_text_regions:
            bbox = region.bbox
            if bbox[1] < band_top - image_height * 0.01 or bbox[3] > band_bottom + image_height * 0.01:
                continue
            if legend_bbox and overlaps_significantly(bbox, legend_bbox, threshold=0.8):
                continue
            if bboxes_overlap(bbox, text_capture_bbox):
                candidate_text.append(bbox)
                continue
            # Also keep title line and labels immediately below the drawing.
            if abs(bbox[1] - label.bbox[1]) <= image_height * 0.03 and abs(((bbox[0] + bbox[2]) / 2) - label_center_x) <= image_width * 0.18:
                candidate_text.append(bbox)
                continue
            # Keep nearby dimension / annotation text around the drawing body.
            if bbox[2] >= core_bbox[0] - image_width * 0.06 and bbox[0] <= core_bbox[2] + image_width * 0.06:
                candidate_text.append(bbox)

        candidate_parts.extend(core_drawings or candidate_drawings)
        candidate_parts.extend(candidate_text)

        region_bbox = merge_bboxes(candidate_parts)
        region_bbox = expand_bbox(
            region_bbox,
            dx=int(image_width * 0.006),
            dy=int(image_height * 0.008),
            max_width=image_width,
            max_height=image_height,
        )
        region_bbox[0] = max(region_bbox[0], max(int(sheet_frame_bbox[0] + image_width * 0.01), text_capture_bbox[0]))
        region_bbox[1] = max(region_bbox[1], band_top)
        region_bbox[2] = min(region_bbox[2], min(int(title_block_bbox[0] - image_width * 0.02), text_capture_bbox[2]))
        region_bbox[3] = min(region_bbox[3], band_bottom)
        final_regions.append(
            RegionBlock(
                id=f"elevation_region_{index + 1}",
                kind="region",
                bbox=region_bbox,
                text=f"{label_text} 立面图区域，包含标注与立面标题",
                source="layout_heuristic",
                content_type="elevation_region",
            )
        )

    deduped_regions: list[RegionBlock] = final_regions[:2]
    for region in final_regions[2:]:
        if any(bboxes_overlap(region.bbox, existing.bbox) and overlaps_significantly(region.bbox, existing.bbox, threshold=0.75) for existing in deduped_regions[2:]):
            continue
        deduped_regions.append(region)
    return deduped_regions


def run_layoutlmv3(
    image: object,
    words: list[WordBox],
    model_name: str,
    max_length: int,
) -> tuple[dict[str, object], list[int]]:
    try:
        import torch  # type: ignore
        from transformers import LayoutLMv3Model, LayoutLMv3Processor  # type: ignore
    except Exception as exc:
        raise RuntimeError("请先安装 transformers 和 torch: pip install transformers torch") from exc

    width, height = image.size
    word_texts = [item.text for item in words]
    boxes = [normalize_bbox(item.bbox, width, height) for item in words]

    processor = LayoutLMv3Processor.from_pretrained(
        model_name,
        apply_ocr=False,
        local_files_only=True,
    )
    model = LayoutLMv3Model.from_pretrained(
        model_name,
        low_cpu_mem_usage=True,
        local_files_only=True,
    )
    model.eval()

    encoding = processor(
        image,
        word_texts,
        boxes=boxes,
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=max_length,
    )

    with torch.no_grad():
        outputs = model(**encoding)

    last_hidden_state = outputs.last_hidden_state[0]
    cls_embedding = last_hidden_state[0].detach().cpu().tolist()
    word_ids = encoding.word_ids(batch_index=0)
    used_word_indexes = sorted({index for index in word_ids if index is not None})

    summary: dict[str, object] = {
        "image_size": {"width": width, "height": height},
        "input_word_count": len(words),
        "used_word_count": len(used_word_indexes),
        "truncated": len(used_word_indexes) < len(words),
        "sequence_length": int(last_hidden_state.shape[0]),
        "hidden_size": int(last_hidden_state.shape[1]),
        "cls_embedding_preview": cls_embedding[:16],
    }
    return summary, used_word_indexes


def save_image(image: object, output_dir: Path) -> str:
    image_name = "page.png"
    image_path = output_dir / image_name
    image.save(image_path)
    return image_name


def preview_text(text: str, limit: int = 80) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 3] + "..."


def color_for_content_type(content_type: str | None) -> str:
    palette = {
        "sheet_frame": "#22c55e",
        "title_block": "#ef4444",
        "elevation_region": "#3b82f6",
    }
    return palette.get(content_type or "elevation_region", "#6ee7ff")


def build_html(
    image_name: str,
    image_width: int,
    image_height: int,
    regions: list[RegionBlock],
    used_word_indexes: list[int],
    model_label_text: str,
) -> str:
    boxes_html: list[str] = []
    for index, region in enumerate(regions):
        left = region.bbox[0] / image_width * 100
        top = region.bbox[1] / image_height * 100
        width = max(0.3, (region.bbox[2] - region.bbox[0]) / image_width * 100)
        height = max(0.3, (region.bbox[3] - region.bbox[1]) / image_height * 100)
        content_type = region.content_type or "general_text"
        color = color_for_content_type(content_type)
        label = json.dumps(f"{index}: {content_type} | {preview_text(region.text or region.kind)}")
        boxes_html.append(
            f'<div class="bbox" title={label} data-kind="{content_type}" style="left:{left:.4f}%;top:{top:.4f}%;width:{width:.4f}%;height:{height:.4f}%;border-color:{color};background:{color}18;">'
            f'<span>{content_type}</span>'
            "</div>"
        )

    used_index_set = set(used_word_indexes)
    type_order = ["sheet_frame", "title_block", "elevation_region"]
    legend_items = []
    for content_type in type_order:
        color = color_for_content_type(content_type)
        legend_items.append(f'<span><i style="background:{color};"></i>{content_type}</span>')
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LayoutLMv3 Block Demo</title>
  <style>
    body {{
      margin: 0;
      background: #0f1115;
      color: #eef2ff;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }}
    .wrap {{
      padding: 20px;
      max-width: 1440px;
      margin: 0 auto;
    }}
    .legend {{
      margin-bottom: 12px;
      color: #c7d2fe;
      font-size: 14px;
    }}
    .legend span {{
      display: inline-block;
      margin-right: 16px;
      margin-bottom: 8px;
    }}
    .legend i {{
      display: inline-block;
      width: 10px;
      height: 10px;
      margin-right: 6px;
      border-radius: 999px;
    }}
    .stage {{
      position: relative;
      width: 100%;
      max-width: 1400px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 12px;
      overflow: hidden;
      background: #111827;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .overlay {{
      position: absolute;
      inset: 0;
    }}
    .bbox {{
      position: absolute;
      border: 2px solid;
      box-sizing: border-box;
      overflow: visible;
    }}
    .bbox:hover {{
      z-index: 2;
      box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.18);
    }}
    .bbox span {{
      position: absolute;
      left: 0;
      top: -20px;
      padding: 2px 6px;
      border-radius: 999px;
      background: rgba(15, 17, 21, 0.9);
      color: #fff;
      font-size: 11px;
      white-space: nowrap;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="legend">
      <span><i style="background:#6ee7ff;"></i>{model_label_text}</span>
      {''.join(legend_items)}
    </div>
    <div class="stage">
      <img src="./{image_name}" alt="page" />
      <div class="overlay">
        {''.join(boxes_html)}
      </div>
    </div>
  </div>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a block-level LayoutLMv3 demo on a single-page PDF or image.")
    parser.add_argument("--input", required=True, help="PDF or image path")
    parser.add_argument("--output-dir", default="tmp/layoutlmv3_demo", help="Output directory")
    parser.add_argument("--page-number", type=int, default=1, help="1-based page number for PDF input")
    parser.add_argument("--dpi", type=int, default=200, help="PDF render DPI")
    parser.add_argument("--ocr-lang", default="eng", help="Tesseract OCR language, used when embedded PDF text is unavailable")
    parser.add_argument("--model-name", default="microsoft/layoutlmv3-base", help="Hugging Face model id")
    parser.add_argument("--max-length", type=int, default=512, help="Max transformer sequence length")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        print(f"输入文件不存在: {input_path}")
        return 2

    output_dir = ensure_output_dir(args.output_dir)
    image, words, text_regions, drawing_rects = collect_page_content(
        input_path=input_path,
        page_number=args.page_number,
        dpi=args.dpi,
        ocr_lang=args.ocr_lang,
    )
    if not words:
        print("未提取到任何文字框, 无法送入 LayoutLMv3。")
        return 3

    model_label_text = ""
    try:
        summary, used_indexes = run_layoutlmv3(
            image=image,
            words=words,
            model_name=args.model_name,
            max_length=args.max_length,
        )
        image_size = summary["image_size"]
        model_label_text = f"used words by model: {len(used_indexes)}"
    except Exception as exc:
        image_size = {"width": image.size[0], "height": image.size[1]}
        used_indexes = []
        summary = {
            "image_size": image_size,
            "input_word_count": len(words),
            "used_word_count": 0,
            "truncated": False,
            "sequence_length": 0,
            "hidden_size": 0,
            "cls_embedding_preview": [],
            "model_skipped": True,
            "model_error": str(exc),
        }
        model_label_text = "model skipped (layout regions still generated)"
    final_regions = detect_three_regions(
        image_width=image_size["width"],
        image_height=image_size["height"],
        text_regions=text_regions,
        drawing_rects=drawing_rects,
    )
    summary["detected_region_count"] = len(final_regions)
    summary["elevation_region_count"] = sum(1 for item in final_regions if item.content_type == "elevation_region")
    summary["detected_regions"] = [
        {"id": item.id, "bbox": item.bbox, "content_type": item.content_type}
        for item in final_regions
    ]
    summary["raw_text_block_count"] = len(text_regions)
    summary["raw_drawing_rect_count"] = len(drawing_rects)

    image_name = save_image(image=image, output_dir=output_dir)
    html = build_html(
        image_name=image_name,
        image_width=image_size["width"],
        image_height=image_size["height"],
        regions=final_regions,
        used_word_indexes=used_indexes,
        model_label_text=model_label_text,
    )

    html_path = output_dir / "layoutlmv3_demo.html"
    json_path = output_dir / "layoutlmv3_summary.json"
    words_path = output_dir / "layoutlmv3_words.json"
    regions_path = output_dir / "layoutlmv3_regions.json"

    html_path.write_text(html, encoding="utf-8")
    json_payload = {
        "input_path": str(input_path),
        "page_number": args.page_number,
        "model_name": args.model_name,
        **summary,
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    words_path.write_text(json.dumps([asdict(item) for item in words], ensure_ascii=False, indent=2), encoding="utf-8")
    regions_path.write_text(json.dumps([asdict(item) for item in final_regions], ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"summary json: {json_path}")
    print(f"words json:   {words_path}")
    print(f"regions json: {regions_path}")
    print(f"html preview: {html_path}")
    print(f"input words:  {summary['input_word_count']}")
    print(f"raw text blocks:{summary['raw_text_block_count']}")
    print(f"raw drawing rects:{summary['raw_drawing_rect_count']}")
    print(f"final regions:{summary['detected_region_count']}")
    print(f"used words:   {summary['used_word_count']}")
    print(f"truncated:    {summary['truncated']}")
    print("")
    print("说明:")
    print("1. LayoutLMv3 仍以词级文字框作为模型输入。")
    print("2. 最终只输出 3 个 region: sheet_frame、title_block、elevation_region。")
    print("3. region 检测依赖 PDF 的文字块和矢量绘图对象，不再输出零散类别。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
