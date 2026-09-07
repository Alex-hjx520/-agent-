"""PDF 插图提取脚本：把 PDF 内嵌图片提取到 data/images/，并在 markdown 中插入引用
==================================================================================
背景：当前 RAG 管道（bge 嵌入 + DeepSeek 纯文本）无法直接分析图片，
     但可以把 PDF 里的插图提取成图片文件，并在对应 markdown 末尾追加"插图清单"，
     为以后接入视觉大模型（Qwen-VL / GPT-4V 等）或前端展示做预留。

用法：
    python extract_images.py                          # 默认 data/raw -> data/images/ + 追加引用到 data/markdown/
    python extract_images.py --min-area 5000          # 过滤小于 5000pt² 的小图（logo 等）
    python extract_images.py --input data/raw --output data/images --markdown data/markdown
    python extract_images.py --no-append              # 只提取图片，不改 markdown
"""

import argparse
import io
import logging
from pathlib import Path

import pymupdf
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path("data/raw")
DEFAULT_IMAGE_DIR = Path("data/images")
DEFAULT_MD_DIR = Path("data/markdown")


def short_stem(stem: str, limit: int = 10) -> str:
    """截短 PDF 名作为图片前缀（避免文件名过长）。"""
    name = "".join(ch for ch in stem if ch not in '()（） ')
    return name[:limit]


def extract_pdf_images(pdf_path: Path, out_dir: Path, min_area: int) -> list[tuple[int, str, float]]:
    """提取 PDF 内嵌图片，返回 [(页码, 文件名, 页上面积pt²)]。"""
    doc = pymupdf.open(pdf_path)
    prefix = short_stem(pdf_path.stem)
    seen: set[int] = set()
    items: list[tuple[int, str, float]] = []
    for pno in range(len(doc)):
        page = doc[pno]
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen:
                continue
            seen.add(xref)
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            r = rects[0]
            area = r.width * r.height
            if area < min_area:
                continue
            info = doc.extract_image(xref)
            ext = info["ext"]
            try:
                pil_img = Image.open(io.BytesIO(info["image"])).convert("RGB")
            except Exception:
                continue
            fname = f"{prefix}_p{pno + 1}_{xref}.{ext}"
            pil_img.save(out_dir / fname)
            items.append((pno + 1, fname, area))
    doc.close()
    return items


def append_image_section(pdf_path: Path, md_dir: Path, items: list[tuple[int, str, float]]) -> None:
    """在对应 markdown 末尾追加插图清单。"""
    md_path = md_dir / (pdf_path.stem + ".md")
    if not md_path.exists():
        logger.warning("markdown 不存在，跳过追加: %s", md_path.name)
        return
    lines = ["", "---", "", "## 产品插图（提取自 PDF，供视觉模型/前端使用）", "",
             "> 当前纯文本 RAG 不直接分析图片，此清单为接入视觉模型或前端展示预留。"]
    for pno, fname, area in items:
        lines.append(f"- 第 {pno} 页：![]({Path('..') / 'images' / fname}) `{fname}`")
    block = "\n".join(lines).replace("\\", "/") + "\n"
    with open(md_path, "a", encoding="utf-8") as f:
        f.write(block)
    logger.info("%s: 追加 %d 张插图引用", md_path.name, len(items))


def pdf_is_scanned(doc: pymupdf.Document, threshold: float = 0.5) -> bool:
    """纯图片页（无文字）占比超过 threshold 视为扫描件（整页是图，不是插图，跳过）。"""
    if len(doc) == 0:
        return False
    empty = sum(1 for p in doc if not p.get_text().strip())
    return empty / len(doc) >= threshold


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="提取 PDF 插图并追加引用到 markdown")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="PDF 目录（默认 data/raw）")
    parser.add_argument("--output", default=DEFAULT_IMAGE_DIR, help="图片输出目录（默认 data/images）")
    parser.add_argument("--markdown", default=DEFAULT_MD_DIR, help="markdown 目录（默认 data/markdown）")
    parser.add_argument("--min-area", type=int, default=3000,
                        help="过滤页上面积小于该值(pt²)的图，默认 3000（过滤小 logo/装饰）")
    parser.add_argument("--no-append", action="store_true", help="只提取图片，不追加 markdown 引用")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input)
    img_dir = Path(args.output)
    md_dir = Path(args.markdown)
    if not input_dir.exists():
        logger.error("输入目录不存在: %s", input_dir)
        raise SystemExit(1)
    img_dir.mkdir(parents=True, exist_ok=True)

    for pdf in sorted(input_dir.glob("*.pdf")):
        # 扫描件整页都是图片，跳过（非插图，且 OCR 已处理）
        probe = pymupdf.open(pdf)
        scanned = pdf_is_scanned(probe)
        probe.close()
        if scanned:
            logger.info("%s: 扫描件，跳过插图提取", pdf.name)
            continue
        items = extract_pdf_images(pdf, img_dir, args.min_area)
        logger.info("%s: 提取 %d 张图 → %s", pdf.name, len(items), img_dir)
        if items and not args.no_append:
            append_image_section(pdf, md_dir, items)
    logger.info("完成，图片已保存到 %s", img_dir)


if __name__ == "__main__":
    main()
