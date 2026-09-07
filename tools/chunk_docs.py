"""文档清洗 + 切分脚本
======================
1. 读取 data/text/ 下所有 .txt 文件
2. 简单清洗：去除多余空行、页眉页脚标记（页码/网址/版权行）、连续重复行、首尾空白
3. 使用 LangChain 的 RecursiveCharacterTextSplitter 按 500 token / 50 token 重叠切分
4. 保存为 data/chunks.json: [{"content": "...", "source": "文件名"}, ...]

用法：
    python chunk_docs.py                          # 默认参数
    python chunk_docs.py --input data/text        # 指定输入目录
    python chunk_docs.py --output data/chunks.json
    python chunk_docs.py --chunk-size 500 --overlap 50
"""

import argparse
import json
import logging
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_INPUT_DIR = Path("data/text")
DEFAULT_OUTPUT = Path("data/chunks.json")


# ---------- token 长度函数（优先 tiktoken，失败则回退字符数） ----------
try:
    import tiktoken

    _ENCODER = tiktoken.get_encoding("cl100k_base")

    def token_len(text: str) -> int:
        """按 token 计算文本长度（DeepSeek/OpenAI 同款分词器）。"""
        return len(_ENCODER.encode(text))

    TOKEN_BACKEND = "tiktoken(cl100k_base)"
except Exception:  # tiktoken 不可用时回退到字符计数
    def token_len(text: str) -> int:
        return len(text)

    TOKEN_BACKEND = "len(字符数)"


# ---------- 页眉页脚 / 噪音行模式 ----------
NOISE_PATTERNS = [
    re.compile(r"^[-\u2014\u2013\s]*\d{1,4}[-\u2014\u2013\s]*$"),          # 纯数字页码: "- 3 -"
    re.compile(r"^第\s*[0-9一二三四五六七八九十百]+\s*页"                     # 中文页码: "第 3 页"
               r"\s*(?:/\s*共\s*[0-9一二三四五六七八九十百]+\s*页)?\s*$"),
    re.compile(r"^page\s*\d+\s*(?:of\s*\d+)?\s*$", re.IGNORECASE),          # Page 3 / Page 3 of 10
    re.compile(r"^(?:https?://|www\.)\S+$", re.IGNORECASE),                 # 独立 URL 行
    re.compile(r"^_*>+\s*(?:https?://)?(?:www\.)?\S+_*$", re.IGNORECASE),   # Markdown 化页脚: "**>>> www...**"
    re.compile(r"^三花-\s*\d+\s*$"),                                          # 三花样本页脚: "三花-63"
    re.compile(r"^\d{3,5}\s+SANHUA\s*$", re.IGNORECASE),                      # OCR 页眉噪音: "888 SANHUA"
    re.compile(r"^©\s*\d{4}.{0,60}$"),                                       # 版权行: "© 2024 ..."
]


def clean_text(text: str) -> str:
    """简单清洗：去页眉页脚标记、连续重复行、合并多余空行、去首尾空白。"""
    cleaned: list[str] = []
    prev_line: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()

        # 空行：只保留一个空行作为段落分隔（合并多余空行）
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue

        # 页眉页脚 / 噪音行
        if any(p.match(line) for p in NOISE_PATTERNS):
            continue

        # 连续重复行（页眉页脚常逐页重复同一行）
        if line == prev_line:
            continue

        cleaned.append(line)
        prev_line = line

    # 去掉首尾空行，并把 3 个以上连续换行压成 2 个
    result = "\n".join(cleaned).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清洗并切分 data/text/ 下的文档")
    parser.add_argument("--input", default=DEFAULT_INPUT_DIR, help="输入目录（默认 data/text）")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="输出 JSON 路径（默认 data/chunks.json）")
    parser.add_argument("--chunk-size", type=int, default=500, help="每块大小 token（默认 500）")
    parser.add_argument("--overlap", type=int, default=50, help="块间重叠 token（默认 50）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input)
    output = Path(args.output)

    if not input_dir.exists():
        logger.error("输入目录不存在: %s", input_dir)
        raise SystemExit(1)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        length_function=token_len,          # 按 token 计算（tiktoken）
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],  # 中文友好分隔符
        keep_separator=True,
    )

    logger.info("切分参数: chunk_size=%d, overlap=%d, length_function=%s",
                args.chunk_size, args.overlap, TOKEN_BACKEND)

    txt_files = sorted(list(input_dir.glob("*.txt")) + list(input_dir.glob("*.md")))
    if not txt_files:
        logger.warning("%s 下没有 .txt/.md 文件", input_dir)
        return

    all_chunks: list[dict] = []

    for txt_path in txt_files:
        raw = txt_path.read_text(encoding="utf-8-sig")  # 兼容 BOM
        cleaned = clean_text(raw)
        pieces = splitter.split_text(cleaned)

        for piece in pieces:
            if piece.strip():
                all_chunks.append({
                    "content": piece,
                    "source": txt_path.name,
                })

        logger.info(
            "%s: 原始 %d 字符 → 清洗后 %d 字符 → %d 块",
            txt_path.name, len(raw), len(cleaned), len(pieces),
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("完成：共 %d 块，已保存到 %s", len(all_chunks), output)


if __name__ == "__main__":
    main()
