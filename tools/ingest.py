"""数据摄取脚本
==============
1. 扫描 data/raw/ 下所有 PDF，用 PyMuPDF 提取文本，保存为同名 .txt 到 data/text/
2. 从 URL 列表文件抓取网页正文，用 requests + BeautifulSoup，保存为 .txt 到 data/text/

用法：
    python ingest.py                       # 默认：处理 PDF + 网页抓取
    python ingest.py --mode pdf            # 只处理 PDF
    python ingest.py --mode web            # 只抓取网页
    python ingest.py --urls my_urls.txt    # 指定 URL 列表文件（每行一个 URL）
"""

import argparse
import logging
import re
from pathlib import Path

import pymupdf  # PyMuPDF（新版推荐 import pymupdf，替代旧的 fitz）
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_TEXT_DIR = Path("data/text")
DEFAULT_URLS_FILE = Path("data/urls.txt")

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


# ---------- PDF 处理 ----------
def _table_to_markdown(data: list[list]) -> str:
    """把表格数据转成 Markdown 表格文本（保留行列关系）。

    PyMuPDF 的 get_text() 会把表格按列打散（型号与参数失联），
    这里用结构化提取转成 | a | b | 表格，便于检索和模型理解。
    """
    if not data:
        return ""
    lines = []
    for i, row in enumerate(data):
        cells = []
        for c in row:
            s = str(c).replace("|", "\\|").replace("\n", " ").strip() if c is not None else ""
            cells.append(s)
        lines.append("| " + " | ".join(cells) + " |")
        if i == 0:
            lines.append("|" + "---|" * len(row))
    return "\n".join(lines)


def extract_pdf_text(pdf_path: Path) -> str:
    """用 PyMuPDF 提取 PDF 文本，表格自动转为 Markdown 表格。

    - 有表格的页：非表格文本 + 结构化 Markdown 表格
    - 无表格的页：普通 get_text()
    """
    doc = pymupdf.open(pdf_path)
    try:
        pages = []
        for page in doc:
            tables = page.find_tables()
            if tables.tables:
                # 1) 表格 → Markdown
                table_mds = [_table_to_markdown(t.extract()) for t in tables.tables]
                table_rects = [pymupdf.Rect(t.bbox) for t in tables.tables]

                # 2) 非表格文本：保留完全不在表格区域内的文本块
                non_table = []
                for b in page.get_text("blocks"):
                    x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
                    inside_table = any(
                        tr.x0 - 2 <= x0 and tr.y0 - 2 <= y0
                        and x1 <= tr.x1 + 2 and y1 <= tr.y1 + 2
                        for tr in table_rects
                    )
                    if not inside_table and text.strip():
                        non_table.append(text.strip())

                pages.append("\n\n".join([*non_table, *table_mds]))
            else:
                pages.append(page.get_text())
        return "\n\n".join(pages).strip()
    finally:
        doc.close()


def process_pdfs(raw_dir: Path, text_dir: Path) -> None:
    """扫描 raw_dir 下所有 PDF，提取文本并保存到 text_dir。"""
    raw_dir = Path(raw_dir)
    text_dir = Path(text_dir)

    if not raw_dir.exists():
        logger.warning("目录不存在，跳过 PDF 处理: %s", raw_dir)
        return

    pdf_files = sorted(raw_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info("data/raw/ 下没有 PDF 文件，跳过")
        return

    text_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, 0

    for pdf_path in pdf_files:
        out_path = text_dir / f"{pdf_path.stem}.txt"
        try:
            text = extract_pdf_text(pdf_path)
            if not text:
                logger.warning("PDF 无文本内容（可能是扫描件）: %s", pdf_path.name)
            out_path.write_text(text, encoding="utf-8")
            logger.info("已提取 %s -> %s (%d 字符)", pdf_path.name, out_path.name, len(text))
            ok += 1
        except Exception as exc:
            logger.exception("提取失败: %s", pdf_path)
            failed += 1

    logger.info("PDF 处理完成：成功 %d 个，失败 %d 个", ok, failed)


# ---------- 网页抓取 ----------
def extract_web_text(url: str, timeout: int = 20) -> str:
    """用 requests + BeautifulSoup 提取网页正文文本。"""
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 移除页面噪音标签
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "iframe"]):
        tag.decompose()

    # 优先正文容器：article / main / body
    main = soup.find("article") or soup.find("main") or soup.body or soup

    # 方式一：收集所有 <p> 段落
    paragraphs = [p.get_text(strip=True) for p in main.find_all("p")]
    paragraphs = [p for p in paragraphs if p]

    if paragraphs:
        text = "\n\n".join(paragraphs)
    else:
        # 方式二：回退到整个正文容器的纯文本
        text = main.get_text("\n", strip=True)

    # 清理多余空行
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def process_urls(urls_file: Path, text_dir: Path, timeout: int = 20) -> None:
    """从 URL 列表文件抓取每个网页，保存正文为 .txt。"""
    urls_file = Path(urls_file)
    text_dir = Path(text_dir)

    if not urls_file.exists():
        logger.warning("URL 列表文件不存在，跳过网页抓取: %s", urls_file)
        return

    urls = []
    for line in urls_file.read_text(encoding="utf-8-sig").splitlines():
        # strip() 去除首尾空白；再显式去除可能残留的 BOM 字符
        line = line.strip().strip("\ufeff")
        if line and not line.startswith("#"):
            urls.append(line)

    if not urls:
        logger.info("URL 列表为空（%s），跳过网页抓取", urls_file)
        return

    text_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, 0

    for url in urls:
        # 从 URL 生成安全的文件名：保留域名 + 路径摘要
        name = re.sub(r"^https?://", "", url)
        name = re.sub(r"[^\w\-.]", "_", name)
        name = name.strip("_")[:80] or "webpage"
        out_path = text_dir / f"{name}.txt"

        try:
            text = extract_web_text(url, timeout=timeout)
            out_path.write_text(text, encoding="utf-8")
            logger.info("已抓取 %s -> %s (%d 字符)", url, out_path.name, len(text))
            ok += 1
        except requests.Timeout:
            logger.warning("请求超时: %s", url)
            failed += 1
        except requests.HTTPError as exc:
            logger.warning("HTTP 错误 %s: %s", exc.response.status_code if exc.response else "?", url)
            failed += 1
        except Exception:
            logger.exception("抓取失败: %s", url)
            failed += 1

    logger.info("网页抓取完成：成功 %d 个，失败 %d 个", ok, failed)


# ---------- 入口 ----------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PDF 文本提取 + 网页正文抓取")
    parser.add_argument(
        "--mode",
        choices=["pdf", "web", "all"],
        default="all",
        help="处理模式：pdf=仅 PDF，web=仅网页，all=两者都处理（默认）",
    )
    parser.add_argument("--input", default=DEFAULT_RAW_DIR, help="PDF 输入目录（默认 data/raw）")
    parser.add_argument("--output", default=DEFAULT_TEXT_DIR, help="文本输出目录（默认 data/text）")
    parser.add_argument("--urls", default=DEFAULT_URLS_FILE, help="URL 列表文件（默认 data/urls.txt）")
    parser.add_argument("--timeout", type=int, default=20, help="网页请求超时秒数（默认 20）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.mode in ("pdf", "all"):
        process_pdfs(args.input, args.output)

    if args.mode in ("web", "all"):
        process_urls(args.urls, args.output, timeout=args.timeout)

    logger.info("全部处理完成，输出目录: %s", args.output)


if __name__ == "__main__":
    main()
