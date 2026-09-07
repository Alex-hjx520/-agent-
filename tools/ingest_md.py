"""PDF → Markdown 摄取脚本
==========================
把 data/raw/ 下的 PDF 转成 Markdown 文档，保存到 data/markdown/，
用于搭建 RAG 知识库（大模型可识别 Markdown 的标题/列表/表格）。

底层用 pymupdf4llm（PyMuPDF 官方库）做版面分析：
  - 标题自动识别为 # / ## / ###
  - 列表识别为 - 项目符号
  - 表格转成 | a | b | Markdown 表格（含无边框表格，比 find_tables 更强）

⚠️ 注意：表格识别仍有偶发丢行/错位（如 KDF 表曾丢 KDF9H 行），
   入库前建议抽查关键型号是否齐全。

用法：
    python ingest_md.py                          # 全部 PDF
    python ingest_md.py --input data/raw         # 指定输入目录
    python ingest_md.py --output data/markdown   # 指定输出目录
"""

import argparse
import logging
from pathlib import Path

import pymupdf4llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_MD_DIR = Path("data/markdown")


def pdf_to_markdown(pdf_path: Path) -> str:
    """单个 PDF → Markdown 文本。"""
    return pymupdf4llm.to_markdown(str(pdf_path))


def process_pdfs(raw_dir: Path, md_dir: Path) -> None:
    raw_dir = Path(raw_dir)
    md_dir = Path(md_dir)

    if not raw_dir.exists():
        logger.warning("目录不存在: %s", raw_dir)
        return

    pdf_files = sorted(raw_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info("%s 下没有 PDF 文件", raw_dir)
        return

    md_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, 0

    for pdf_path in pdf_files:
        out_path = md_dir / f"{pdf_path.stem}.md"
        try:
            md = pdf_to_markdown(pdf_path)
            if not md.strip():
                logger.warning("PDF 无文本内容（可能是扫描件，需 OCR）: %s", pdf_path.name)
            out_path.write_text(md, encoding="utf-8")
            logger.info("已转换 %s -> %s (%d 字符)", pdf_path.name, out_path.name, len(md))
            ok += 1
        except Exception as e:  # noqa: BLE001
            logger.error("转换失败 %s: %s", pdf_path.name, e)
            failed += 1

    logger.info("完成：成功 %d，失败 %d，输出目录 %s", ok, failed, md_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF → Markdown 摄取")
    parser.add_argument("--input", default=DEFAULT_RAW_DIR, help="PDF 输入目录（默认 data/raw）")
    parser.add_argument("--output", default=DEFAULT_MD_DIR, help="Markdown 输出目录（默认 data/markdown）")
    args = parser.parse_args()
    process_pdfs(args.input, args.output)


if __name__ == "__main__":
    main()
