"""PDF 图片 OCR 脚本：用 RapidOCR 识别 PDF 中的图片/扫描件文字，转成 Markdown
================================================================================
背景：部分 PDF（热力膨胀阀-RFGB、电子膨胀阀-DPF-LPF 应用手册）是整页图片的扫描件，
     纯文本提取得到 0 字符。本脚本逐页渲染为图片 → RapidOCR 识别 → 输出 Markdown，
     与 ingest_md.py 的输出合并进知识库。

用法：
    python ocr_pdfs.py                          # 只 OCR 纯扫描件 PDF → data/markdown/
    python ocr_pdfs.py --all                    # 所有 PDF 每页都 OCR（慢，含插图）
    python ocr_pdfs.py --input data/raw --output data/markdown
    python ocr_pdfs.py --dpi 200 --page 1-5     # 指定分辨率 / 页码范围（1 起）
"""

import argparse
import io
import logging
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from rapidocr import RapidOCR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path("data/raw")
DEFAULT_OUTPUT = Path("data/markdown")
SCANNED_THRESHOLD = 0.5  # 无文字页占比超过该值视为扫描件


def pdf_is_scanned(doc: pymupdf.Document, threshold: float = SCANNED_THRESHOLD) -> bool:
    """纯图片页（无文字）占比超过 threshold 视为扫描件。"""
    if len(doc) == 0:
        return False
    empty = sum(1 for p in doc if not p.get_text().strip())
    return empty / len(doc) >= threshold


def ocr_page_image(page: pymupdf.Page, engine: RapidOCR, dpi: int) -> str:
    """渲染单页为图片并 OCR，返回该页 markdown 文本。"""
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    arr = np.asarray(img)
    out = engine(arr)
    md = out.to_markdown() if out.txts else ""
    return md.strip()


def process_pdf(pdf_path: Path, engine: RapidOCR, dpi: int, mode: str,
                page_range: str | None, out_dir: Path) -> int:
    doc = pymupdf.open(pdf_path)
    pages = list(range(len(doc)))
    if page_range:
        # "1-5" / "3" / "1,3,5"
        sel: set[int] = set()
        for part in page_range.split(","):
            if "-" in part:
                a, b = part.split("-", 1)
                sel.update(range(int(a) - 1, int(b)))
            else:
                sel.add(int(part) - 1)
        pages = sorted(sel)

    scanned = pdf_is_scanned(doc)
    parts: list[str] = []
    for i in pages:
        page = doc[i]
        has_text = bool(page.get_text().strip())
        if mode == "all" or not has_text:
            md = ocr_page_image(page, engine, dpi)
            if md:
                parts.append(f"## 第 {i + 1} 页\n\n{md}")
        elif mode == "scanned":
            logger.info("  - 第 %d 页有文字，跳过（用 --all 强制 OCR）", i + 1)
    doc.close()

    if not parts:
        logger.warning("%s: 无 OCR 内容", pdf_path.name)
        return 0

    header = f"# {pdf_path.stem}（OCR 识别，来源：{pdf_path.name}）\n\n"
    content = header + "\n\n---\n\n".join(parts)
    out_path = out_dir / (pdf_path.stem + ".md")
    out_path.write_text(content, encoding="utf-8")
    logger.info("%s: OCR %d 页 → %s（%d 字符）",
                pdf_path.name, len(parts), out_path.name, len(content))
    return len(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="用 RapidOCR 识别 PDF 图片/扫描件文字")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="PDF 目录（默认 data/raw）")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="输出目录（默认 data/markdown）")
    parser.add_argument("--mode", choices=["scanned", "all"], default="scanned",
                        help="scanned=只 OCR 纯扫描件(默认)；all=所有 PDF 每页都 OCR")
    parser.add_argument("--dpi", type=int, default=200, help="渲染分辨率（默认 200）")
    parser.add_argument("--page", default=None, help="页码范围，如 1-5 / 3 / 1,3,5")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input)
    out_dir = Path(args.output)
    if not input_dir.exists():
        logger.error("输入目录不存在: %s", input_dir)
        raise SystemExit(1)
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = RapidOCR()
    pdfs = sorted(input_dir.glob("*.pdf"))
    total_pages = 0
    for pdf in pdfs:
        # 只处理扫描件（除非 --all）
        if args.mode == "scanned":
            probe = pymupdf.open(pdf)
            scanned = pdf_is_scanned(probe)
            probe.close()
            if not scanned:
                logger.info("%s: 非扫描件，跳过（用 --all 可强制）", pdf.name)
                continue
        total_pages += process_pdf(pdf, engine, args.dpi, args.mode, args.page, out_dir)
    logger.info("完成：共识别 %d 页 → %s", total_pages, out_dir)


if __name__ == "__main__":
    main()
