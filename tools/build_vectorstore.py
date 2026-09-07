"""构建 Chroma 向量库 + 检索脚本
================================
1. 加载 data/chunks.json
2. HuggingFaceEmbeddings 加载 BAAI/bge-large-zh-v1.5 模型
3. 将每个块向量化，存入 Chroma（持久化目录 chroma_db）
4. 提供 retrieve_docs(query, k=5) 返回最相关 k 个文档块

用法：
    python build_vectorstore.py                  # 构建库 + 默认测试查询
    python build_vectorstore.py --query "..."    # 自定义查询
    python build_vectorstore.py --k 3            # 检索数量
    python build_vectorstore.py --rebuild        # 强制重建向量库
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 必须先加载 .env（含 HF_ENDPOINT 等配置），再导入依赖库
load_dotenv()
# huggingface.co 在国内网络常不可达，默认走镜像 hf-mirror.com
# 若系统环境或 .env 已配置 HF_ENDPOINT，则尊重已有配置（setdefault 不覆盖）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import argparse
import json
import logging
import shutil

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CHUNKS_FILE = Path("data/chunks.json")
PERSIST_DIR = "chroma_db"
COLLECTION_NAME = "equipment_chunks"
EMBED_MODEL = "BAAI/bge-large-zh-v1.5"

# BGE 系列模型在「查询端」推荐的检索前缀（文档端不加）
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


# ---------- 嵌入模型 / 向量库（进程级缓存：启动预热一次，请求复用，避免每次重新加载模型） ----------
import threading as _threading

_EMBED_LOCK = _threading.Lock()
_EMBED_CACHE = None  # HuggingFaceEmbeddings 单例
_STORE_LOCK = _threading.Lock()
_STORE_CACHE = None  # {"ts": 目录mtime, "store": Chroma, "dir":..., "name":...}


def get_embeddings() -> HuggingFaceEmbeddings:
    """获取 bge 嵌入模型（进程内单例：首次加载后缓存，后续请求复用）。"""
    global _EMBED_CACHE
    if _EMBED_CACHE is None:
        with _EMBED_LOCK:
            if _EMBED_CACHE is None:
                logger.info("加载嵌入模型 %s（首次，之后请求复用）", EMBED_MODEL)
                _EMBED_CACHE = HuggingFaceEmbeddings(
                    model_name=EMBED_MODEL,
                    model_kwargs={"device": "cpu"},                 # 无 GPU 时用 CPU，稳妥
                    encode_kwargs={"normalize_embeddings": True},   # 归一化，配合余弦相似度
                )
    return _EMBED_CACHE


def get_vectorstore(
    persist_dir: str = PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
) -> Chroma:
    """获取 Chroma 向量库（进程级缓存：首次打开后复用，避免每个请求重新加载）。

    重建向量库后需调用 refresh_vectorstore()（或重启后端）让新库生效。
    """
    global _STORE_CACHE
    cached = _STORE_CACHE
    if (
        cached
        and cached.get("dir") == persist_dir
        and cached.get("name") == collection_name
    ):
        return cached["store"]
    with _STORE_LOCK:
        cached = _STORE_CACHE
        if (
            cached
            and cached.get("dir") == persist_dir
            and cached.get("name") == collection_name
        ):
            return cached["store"]
        store = Chroma(
            embedding_function=get_embeddings(),
            persist_directory=persist_dir,
            collection_name=collection_name,
        )
        _STORE_CACHE = {"store": store, "dir": persist_dir, "name": collection_name}
    return store


def refresh_vectorstore(
    persist_dir: str = PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
) -> Chroma:
    """重建向量库后调用：丢弃缓存、重新打开新库（无需重启后端）。"""
    global _STORE_CACHE
    _STORE_CACHE = None
    return get_vectorstore(persist_dir=persist_dir, collection_name=collection_name)


def warm_vectorstore() -> None:
    """启动预热：加载嵌入模型并打开向量库，放入进程缓存（此后每个请求不再重复加载）。"""
    get_embeddings()
    get_vectorstore()
    logger.info("向量库预热完成：嵌入模型 + Chroma 已缓存（chroma_db）")


# ---------- 加载块 ----------
def load_chunks(path: Path = CHUNKS_FILE) -> list[dict]:
    """加载 chunks.json，返回 [{content, source}, ...]。"""
    if not path.exists():
        raise FileNotFoundError(f"{path} 不存在，请先运行 chunk_docs.py 生成切分块")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- 构建向量库 ----------
def build_vectorstore(
    chunks: list[dict],
    persist_dir: str = PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
    rebuild: bool = False,
) -> Chroma:
    """将 chunks 向量化并存入 Chroma 持久化库，返回 vectorstore。"""
    if rebuild and Path(persist_dir).exists():
        shutil.rmtree(persist_dir)
        global _STORE_CACHE
        _STORE_CACHE = None  # 丢弃旧库进程缓存，新库构建后由新打开生效
        logger.info("已删除旧向量库 %s（重建）", persist_dir)

    docs = [
        Document(page_content=c["content"], metadata={"source": c["source"]})
        for c in chunks
    ]

    embeddings = get_embeddings()
    logger.info("向量化 %d 个文档块，模型: %s", len(docs), EMBED_MODEL)
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=collection_name,
    )
    # chromadb 1.x 自动持久化；旧版本手动 persist()
    if hasattr(vectorstore, "persist"):
        vectorstore.persist()

    logger.info("向量库构建完成: %s（%d 块）", persist_dir, len(docs))
    return vectorstore


# ---------- 检索 ----------
def retrieve_docs(
    query: str,
    k: int = 5,
    persist_dir: str = PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
    query_instruction: str = QUERY_INSTRUCTION,
) -> list[tuple[Document, float]]:
    """从已有向量库检索与 query 最相关的 k 个文档块。

    返回 [(Document, 相似度分数), ...]，分数越高越相关。
    """
    vectorstore = get_vectorstore(persist_dir=persist_dir, collection_name=collection_name)

    # BGE 查询端加指令前缀，提升检索效果
    full_query = query_instruction + query
    logger.info("检索: k=%d query=%s", k, query)
    results = vectorstore.similarity_search_with_relevance_scores(full_query, k=k)
    return results


# ---------- 入口 ----------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建 Chroma 向量库并检索")
    parser.add_argument("--query", default=None, help="检索查询（默认: 我需要一台耐高温的泵）")
    parser.add_argument("--k", type=int, default=5, help="返回结果数（默认 5）")
    parser.add_argument("--rebuild", action="store_true", help="强制重建向量库")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # 1) 构建或复用向量库
    if Path(PERSIST_DIR).exists() and not args.rebuild:
        logger.info("向量库 %s 已存在，直接复用（用 --rebuild 可重建）", PERSIST_DIR)
    else:
        chunks = load_chunks()
        build_vectorstore(chunks, rebuild=args.rebuild)

    # 2) 测试检索
    query = args.query or "我需要一台耐高温的泵"
    print(f"\n===== 测试查询: {query} (k={args.k}) =====\n")
    results = retrieve_docs(query, k=args.k)

    if not results:
        print("未检索到任何结果，请检查向量库是否为空。")
        return

    for i, (doc, score) in enumerate(results, 1):
        src = doc.metadata.get("source", "未知来源")
        print(f"[{i}] score={score:.4f} | source={src}")
        print(f"    {doc.page_content[:150]}...")
        print()


if __name__ == "__main__":
    main()
