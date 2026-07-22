#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import fitz


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def image_area_ratio(page_dict: dict, page_area: float) -> tuple[int, float]:
    count = 0
    area = 0.0
    for block in page_dict.get("blocks", []):
        if block.get("type") != 1:
            continue
        count += 1
        x0, y0, x1, y1 = block.get("bbox", (0, 0, 0, 0))
        area += max(0.0, x1 - x0) * max(0.0, y1 - y0)
    return count, min(1.0, area / max(page_area, 1.0))


def estimate_image_tokens(width_px: int, height_px: int) -> int:
    # Heuristique volontairement prudente; le budget réel est ensuite borné par le profil fournisseur.
    tiles = math.ceil(width_px / 512) * math.ceil(height_px / 512)
    return 256 + tiles * 256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pages-dir", required=True)
    parser.add_argument("--native-dir", required=True)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--fallback-dpi", type=int, default=110)
    parser.add_argument("--min-native-chars", type=int, default=40)
    parser.add_argument("--visual-mode", choices=["ocr-only", "auto", "all"], default="auto")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    pages_dir = Path(args.pages_dir).resolve()
    native_dir = Path(args.native_dir).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)
    native_dir.mkdir(parents=True, exist_ok=True)

    document = fitz.open(input_path)
    pages: list[dict] = []

    for index in range(document.page_count):
        page_number = index + 1
        page_id = f"page_{page_number:04d}"
        page = document.load_page(index)
        native_text = page.get_text("text", sort=True).strip()
        native_path = native_dir / f"{page_id}.txt"
        native_path.write_text(native_text, encoding="utf-8")

        page_dict = page.get_text("dict")
        page_area = float(page.rect.width * page.rect.height)
        images, image_ratio = image_area_ratio(page_dict, page_area)
        drawings = len(page.get_drawings())
        needs_ocr = len(native_text) < args.min_native_chars
        substantial_visual = image_ratio >= 0.05 or drawings >= 5
        requires_vision = (
            args.visual_mode == "all"
            or needs_ocr
            or (args.visual_mode == "auto" and substantial_visual)
        )

        image_path = None
        fallback_path = None
        estimated_tokens = max(256, math.ceil(len(native_text) / 4))
        if requires_vision:
            pix = page.get_pixmap(dpi=args.dpi, alpha=False)
            image_path_obj = pages_dir / f"{page_id}.png"
            pix.save(image_path_obj)
            fallback_pix = page.get_pixmap(dpi=args.fallback_dpi, alpha=False)
            fallback_path_obj = pages_dir / f"{page_id}.low.png"
            fallback_pix.save(fallback_path_obj)
            image_path = str(image_path_obj)
            fallback_path = str(fallback_path_obj)
            estimated_tokens = estimate_image_tokens(pix.width, pix.height) + 600

        fingerprint_pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2), alpha=False)
        pages.append({
            "pageNumber": page_number,
            "pageId": page_id,
            "sourceHash": sha256_bytes(fingerprint_pix.samples),
            "widthPt": float(page.rect.width),
            "heightPt": float(page.rect.height),
            "nativeTextChars": len(native_text),
            "nativeTextPath": str(native_path),
            "imageCount": images,
            "imageAreaRatio": round(image_ratio, 6),
            "drawingCount": drawings,
            "estimatedInputTokens": estimated_tokens,
            "requiresVision": requires_vision,
            **({"imagePath": image_path, "fallbackImagePath": fallback_path} if image_path else {})
        })

    result = {"schemaVersion": "1.0", "totalPages": document.page_count, "pages": pages}
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    document.close()


if __name__ == "__main__":
    main()
