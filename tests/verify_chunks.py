"""验证 chunk_docs.py 的切分结果（data/chunks.json）
====================================================
检查：
1. 文件存在 + JSON 合法
2. 块数统计
3. 每块必含 content / source 且内容非空
4. source 覆盖 data/text/ 下所有 .txt
5. 块大小（token 数）是否在 chunk_size 范围内

运行：
    python tests/verify_chunks.py
    python tests/verify_chunks.py --chunks data/chunks.json --input data/text
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

try:
    import tiktoken

    ENC = tiktoken.get_encoding("cl100k_base")

    def token_len(text: str) -> int:
        return len(ENC.encode(text))

    TOKEN_BACKEND = "tiktoken"
except Exception:
    def token_len(text: str) -> int:
        return len(text)

    TOKEN_BACKEND = "char-count"


def main() -> None:
    parser = argparse.ArgumentParser(description="验证切分结果")
    parser.add_argument("--chunks", default="data/chunks.json")
    parser.add_argument("--input", default="data/text", help="源 txt 目录（覆盖检查）")
    parser.add_argument("--max-chunk-size", type=int, default=500, help="块大小上限 token")
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    input_dir = Path(args.input)

    print(f"== 验证切分结果: {chunks_path} (长度函数: {TOKEN_BACKEND}) ==\n")
    checks: list[tuple[str, bool]] = []
    problems: list[str] = []

    # 1. 文件存在 + JSON 合法
    if not chunks_path.exists():
        print("[FAIL] chunks.json 不存在，请先运行 python chunk_docs.py")
        sys.exit(1)
    try:
        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        checks.append(("chunks.json 存在且 JSON 合法", True))
    except json.JSONDecodeError as exc:
        print(f"[FAIL] chunks.json 不是合法 JSON: {exc}")
        sys.exit(1)

    # 2. 块数
    total = len(chunks)
    checks.append((f"块总数: {total}", total > 0))
    if total == 0:
        problems.append("没有切分块")

    # 3. 必填字段 + 内容非空
    bad_fields = [i for i, c in enumerate(chunks)
                  if not isinstance(c, dict) or "content" not in c or "source" not in c]
    empty = [i for i, c in enumerate(chunks) if not str(c.get("content", "")).strip()]
    checks.append(("每块包含 content/source 字段", not bad_fields))
    checks.append(("无空内容块", not empty))
    if bad_fields:
        problems.append(f"缺失字段的块: {bad_fields[:5]}")
    if empty:
        problems.append(f"内容为空的块: {empty[:5]}")

    # 4. source 覆盖所有源文件
    src_files = {p.name for p in input_dir.glob("*.txt")} if input_dir.exists() else set()
    covered = {c.get("source") for c in chunks}
    missing = sorted(src_files - covered)
    checks.append((f"覆盖源文件 {len(covered)}/{len(src_files)}", not missing))
    if missing:
        problems.append(f"未切分的文件: {missing}")

    # 5. 块大小统计
    if total:
        sizes = [token_len(c["content"]) for c in chunks]
        checks.append((f"块 token 范围: {min(sizes)}~{max(sizes)}", max(sizes) <= args.max_chunk_size))
        if max(sizes) > args.max_chunk_size:
            problems.append(f"存在超大块(>{args.max_chunk_size} token): "
                            f"{[i for i, s in enumerate(sizes) if s > args.max_chunk_size][:5]}")

    # 汇总
    print()
    all_ok = True
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        all_ok = all_ok and ok
    print()
    if problems:
        print("发现问题：")
        for p in problems:
            print(f"  - {p}")
        print("\n结论：切分未完全通过，请检查以上问题。")
        sys.exit(1)
    if all_ok:
        print("结论：切分验证通过 ✅")
    else:
        print("结论：存在 FAIL 项")
        sys.exit(1)


if __name__ == "__main__":
    main()
