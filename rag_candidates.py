# -*- coding: utf-8 -*-
"""选型候选来源 v2：RAG 文档库检索 + DB 参数回填。

规则（用户确认）：
  1) 候选设备 = 从文档库（data/markdown 向量化 chunks）用 RAG 检索定位相关文档，
     再从这些文档全文抽取的型号集合 —— 不以 DB 是否导过数据为候选前提；
  2) DB 里若有该型号 → 参数回填 DB 行（source='db'，字段最完整）；
  3) DB 里没有 → 用文档文本解析的参数（source='doc'）；
     - 仅“Kv 型”设备类型（电子膨胀阀/电磁阀/干燥过滤器/压力调节阀/单向阀/球阀）
       且型号行上下文能解析出 Kv>0 的文档独有型号才进入候选（可流量判定）；
     - 四通(SHF)/热力(RFKH…)等容量型无 Kv 不做文档候选（其判定走容量表/DB）。
  4) DB 有但文档库未收录的型号（OCR/资料差异）同样回填为 db 候选，避免丢失
     已能判定的设备（文档库并非 DB 的超集）。

说明：DB 型号的完整参数最可靠 → 优先；文档只用于“DB 没有的型号”补参。
"""
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

from db_query import DEVICE_TABLES, query_database  # noqa: E402

_MD_DIR = Path("data/markdown")
_RAG_K_PER_TYPE = 15

TYPE_TOPIC = {
    "四通换向阀": "SHF SHF-G 四通换向阀 型号规格 技术参数 冷量 动作压差",
    "电子膨胀阀": "VPF DPF LPF PEV DBF 电子膨胀阀 型号 Kv值 最大工作压差 技术参数",
    "热力膨胀阀": "RFKH RFGB RFGC RFGD 热力膨胀阀 型号 名义制冷量 阀口 技术参数",
    "电磁阀": "MDF FDF LDF KDF 电磁阀 型号 Kv值 最大工作压差 技术参数 接管",
    "干燥过滤器": "DTG STG HTG 干燥过滤器 型号 技术参数 接管 滤芯",
    "压力调节阀": "LTF CTF XTF YTF PYF 压力调节阀 型号 技术参数 压力调节",
    "单向阀": "YCVS YCV CCV 单向阀 型号 技术参数 流向",
    "球阀": "SBV GBV GBVW 球阀 型号 技术参数 通径",
}
TYPE_FILES = {
    "四通换向阀": ["SHF系列四通换向阀.md", "四通换向阀应用手册.md"],
    "电子膨胀阀": ["电子膨胀阀应用手册-DPF-LPF-DPF-DPF系列.md"],
    "热力膨胀阀": ["热力膨胀阀应用手册-RFGB系列.md"],
    "电磁阀": ["KDF系列电磁阀.md"],
    "干燥过滤器": [], "压力调节阀": [], "单向阀": [], "球阀": [],
}
_MASTER_MD = "三花商用出品-流体控制部件(包含全部部件内容).md"
# 允许文档候选的“Kv 型”类型（容量型四通/热力不做 doc 候选）
_DOC_KV_TYPES = {"电子膨胀阀", "电磁阀", "干燥过滤器", "压力调节阀", "单向阀", "球阀"}

_FILE_CACHE: dict[str, str] = {}


def _text_of(name: str) -> str:
    if name not in _FILE_CACHE:
        p = _MD_DIR / str(name)
        _FILE_CACHE[name] = p.read_text(encoding="utf-8") if p.exists() else ""
    return _FILE_CACHE[name]


def _load_db_index(device_type: str) -> dict:
    """该类型 DB 全行 {model: row}（参数回填 + 兜底）。"""
    try:
        rows, _sql, _meta = query_database(device_type, {}, limit=5000)
        return {str(r.get("model", "")).strip(): dict(r) for r in rows if r.get("model")}
    except Exception as exc:
        logger.warning("[rag] %s DB 索引失败，仅文档参数：%s", device_type, exc)
        return {}


def _retrieve_sources(type_topic: str, rag_k: int) -> list[str]:
    """RAG 向量检索，返回命中的 source 文件名（唯一）。失败返回空。"""
    try:
        from tools.build_vectorstore import retrieve_docs
        docs = retrieve_docs(type_topic, k=rag_k)
    except Exception as exc:
        logger.warning("[rag] 向量检索失败：%s", exc)
        return []
    files, seen = [], set()
    for d, _sc in docs:
        src = str((d.metadata or {}).get("source") or "").strip()
        if src and src not in seen:
            seen.add(src)
            files.append(src)
    return files


def _series_pattern(device_type: str) -> str:
    series = DEVICE_TABLES.get(device_type, {}).get("series", [])
    return "|".join(re.escape(s) for s in sorted(set(series), key=len, reverse=True))


def _extract_doc_models(device_type: str, text: str) -> list[str]:
    pat = _series_pattern(device_type)
    if not pat:
        return []
    rx = re.compile(rf"(?<![\w\-])(?:{pat})(?![\w\-]?[A-Z])([A-Za-z0-9()（）./\-]*)")
    out, seen = [], set()
    for m in rx.finditer(text):
        tok = (m.group(0) + (m.group(1) or "")).strip()
        tok = re.sub(r"[()（）/.\-]+$", "", tok)
        if not re.search(r"\d", tok) or len(tok) < 4 or len(tok) > 32:
            continue
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def _looks_contaminated(model: str, known: set) -> bool:
    for k in known:
        if k and len(k) >= 4 and model.startswith(k) and len(model) > len(k) + 1:
            return True
    return False


# ---------- 文档参数解析（型号所在行上下文，防跨文件/跨型号串味） ----------
_KV_RE = re.compile(r"(?:Kv|KV|kv)\s*(?:值|系数)?\s*[:：=]?\s*([\d.]+)")
_PRESS_RE = [
    ("max_working_pressure", r"最大\s*工作\s*压力"),
    ("max_working_pressure_diff", r"最大\s*工作压差"),
    ("max_op_pressure_diff", r"最大\s*(?:动作|开阀)?\s*压差"),
    ("min_op_pressure_diff", r"最小\s*(?:动作|工作|开阀)?\s*压差"),
]


def _norm_pressure(v: float, unit: str) -> float:
    u = (unit or "").lower()
    if u in ("bar", "bars", "b"):
        return round(v / 10.0, 6)
    if u.startswith("kpa"):
        return round(v / 1000.0, 6)
    return round(v, 6)


def _model_context(model: str, file_texts: list[str]) -> str:
    for txt in file_texts:
        lines = txt.splitlines()
        for i, ln in enumerate(lines):
            if model in ln:
                return "\n".join(lines[max(0, i - 1): min(len(lines), i + 3)])
    return ""


def _parse_doc_params(model: str, device_type: str, ctx: str) -> dict:
    params: dict = {}
    mm = _KV_RE.search(ctx)
    if mm:
        v = float(mm.group(1))
        if v > 0:
            params["kv_value"] = v
    for key, rx in _PRESS_RE:
        pm = re.search(rf"{rx}\s*[:：=]?\s*([\d.]+)\s*(MPa|Mpa|mPa|bar|Bar|kPa|KPa)?", ctx)
        if pm:
            val = _norm_pressure(float(pm.group(1)), pm.group(2) or "MPa")
            params.setdefault(key, val)
    if not params:
        return {}
    for s in sorted(DEVICE_TABLES.get(device_type, {}).get("series", []), key=len, reverse=True):
        if model.upper().startswith(s.replace(" ", "").upper()):
            params["series"] = s
            break
    return params


# ---------- 主入口 ----------
def collect_rag_candidates(device_type: str | None = None, extra_query: str = "",
                           rag_k: int = _RAG_K_PER_TYPE) -> list[dict]:
    types = [device_type] if device_type else list(DEVICE_TABLES.keys())
    db_index = {t: _load_db_index(t) for t in types}

    cands: list[dict] = []
    seen_models: set[str] = set()

    for t in types:
        topic = (TYPE_TOPIC.get(t, t) + " " + (extra_query or "")).strip()[:400]
        sources = _retrieve_sources(topic, rag_k)
        file_names = list(dict.fromkeys(sources + TYPE_FILES.get(t, []) + [_MASTER_MD]))
        file_texts = [_text_of(f) for f in file_names]
        text = "\n".join(file_texts)

        # 1) DB 型号：文档含 → 回填；文档缺失 → DB 兜底（不丢已能判定的）
        joined_text = "".join(file_texts)
        for dbm, row in (db_index.get(t) or {}).items():
            if not dbm or dbm in seen_models:
                continue
            seen_models.add(dbm)
            cands.append({
                "model": dbm, "series": row.get("series", ""),
                "device_type": t, "parameters": dict(row),
                "source": "db", "in_doc": dbm in joined_text,
            })

        # 2) 文档独有型号（Kv 型类型 + 行上下文有 Kv）
        if t in _DOC_KV_TYPES:
            for m in _extract_doc_models(t, text):
                if not m or m in seen_models or _looks_contaminated(m, seen_models):
                    continue
                ctx = _model_context(m, file_texts)
                if not ctx:
                    continue
                params = _parse_doc_params(m, t, ctx)
                if not params.get("kv_value"):
                    continue
                seen_models.add(m)
                cands.append({
                    "model": m, "series": params.get("series", ""),
                    "device_type": t, "parameters": params, "source": "doc",
                })

    logger.info("[rag] 候选合计 %d（db %d / doc %d）", len(cands),
                sum(1 for c in cands if c["source"] == "db"),
                sum(1 for c in cands if c["source"] == "doc"))
    return cands
