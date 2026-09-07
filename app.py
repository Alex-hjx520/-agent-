"""equipment-agent FastAPI 后端入口（流量选型系统版）

仅保留新选型系统的接口：
  - GET  /health        健康检查
  - POST /select/flow   表单式流量选型（全类型候选，质量流量窗口判定）
  - POST /flow/chat     对话式流量选型（大模型澄清 → 流量选型 → 达标参数 + 报告）
  - POST /parse-doc     导入 Word/txt/md 文档为文本（工具）

运行：uvicorn app:app --host 127.0.0.1 --port 8010
"""
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from contextlib import asynccontextmanager  # noqa: E402


@asynccontextmanager
async def lifespan(_app):
    """启动预热：加载 RAG 嵌入模型并打开向量库，避免首个请求卡顿。失败不阻断。"""
    try:
        from tools.build_vectorstore import warm_vectorstore
        warm_vectorstore()
        logger.info("RAG 向量库预热完成（bge 嵌入 + Chroma 已缓存）")
    except Exception as exc:  # pragma: no cover
        logger.warning("RAG 预热失败（不影响启动，首次检索会较慢）：%s", exc)
    yield


app = FastAPI(
    title="Equipment Flow Selection API",
    description="制冷设备质量流量选型系统（FastAPI + CoolProp + RAG 文档库候选 + DeepSeek 澄清/报告）",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- LLM 懒加载单例（DeepSeek，用于对话澄清/报告） ----------
_llm = None


def get_llm():
    """惰性创建 ChatOpenAI 实例；未配置 API Key 时抛 503。"""
    global _llm
    if _llm is None:
        if not settings.has_api_key:
            raise HTTPException(
                status_code=503,
                detail="DEEPSEEK_API_KEY 未配置或仍为占位符，请编辑项目根目录的 .env 文件",
            )
        from langchain_openai import ChatOpenAI
        logger.info("初始化 ChatOpenAI: model=%s", settings.deepseek_model)
        _llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.3,
            max_tokens=2048,
            timeout=60,
            max_retries=2,
        )
    return _llm


# ---------- 请求模型 ----------
class FlowSelectRequest(BaseModel):
    """POST /select/flow 请求体（表单式流量选型）。"""

    refrigerant: str = Field(..., description="制冷剂类型，如 R410A/R32/R134a")
    cond_temp: float = Field(..., description="冷凝温度 (℃)")
    evap_temp: float = Field(..., description="蒸发温度 (℃)")
    subcooling: float = Field(0.0, description="过冷度 SC (K)")
    superheat: float = Field(5.0, description="过热度 SH (K)")
    delta_pressure: float | None = Field(
        default=None,
        description="允许压降 (MPa)：系统可给阀的压降上限；设备上界取 min(设备max, 允许压降)",
    )
    required_capacity: float = Field(..., description="需求制冷量 (kW)")
    device_type: str = Field(
        default="",
        description="候选设备类型；空 = 扫描全部类型表（凡字段齐全的型号自动参与）",
    )


class FlowChatRequest(BaseModel):
    """POST /flow/chat 请求体（对话式流量选型）。"""

    message: str = Field(..., description="用户本轮输入")
    history: list[str] = Field(
        default_factory=list,
        description="此前的用户消息（不含本轮），用于多轮累积需求",
    )
    params: dict | None = Field(default=None, description="已确认/已收集的参数键值（前端回传）")


# ---------- 接口 ----------
@app.get("/health", tags=["系统"])
def health() -> dict:
    """健康检查。"""
    return {
        "status": "ok",
        "model": settings.deepseek_model,
        "api_configured": settings.has_api_key,
    }


@app.post("/select/flow", tags=["选型"])
def select_flow(req: FlowSelectRequest) -> dict:
    """按质量流量窗口的直接选型（表单式）。

    1) CoolProp 按 需求制冷量/工况 算需求质量流量 m_req 与阀前液密度；
    2) 候选 = 数据库全部类型表（字段：kv 且 min/max 至少其一的型号参与，其余标 skipped）；
    3) 每台 m = Kv·√Δp·√(1000ρ) 算允许流量，m_req 达标即入选。
    """
    from flow_selection import flow_select
    from rag_candidates import collect_rag_candidates

    # 候选来源：RAG 文档库检索定位 + 型号抽取，DB 有则回填参数（不再直接以 DB 全表为候选）
    extra = (f"{req.refrigerant} 冷凝{req.cond_temp}℃ 蒸发{req.evap_temp}℃ "
             f"制冷量{req.required_capacity}kW" if req.refrigerant else "")
    candidates = collect_rag_candidates(req.device_type or None, extra_query=extra)
    if not candidates:
        raise HTTPException(status_code=404,
                            detail="文档库/数据库均无候选型号（请确认已构建文档库或已导入数据）。")

    out = flow_select(
        req.refrigerant, req.cond_temp, req.evap_temp,
        req.subcooling, req.superheat, req.delta_pressure,
        req.required_capacity, candidates,
    )
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail="；".join(out.get("failure", [])))
    out["device_type"] = req.device_type or "全部"
    out["candidate_total"] = len(candidates)
    out["skipped"] = sum(1 for r in out.get("results", []) if r.get("skipped"))
    out["passed_count"] = sum(1 for r in out.get("results", []) if r.get("passed"))
    return out


@app.post("/flow/chat", tags=["选型"])
def flow_chat(req: FlowChatRequest) -> dict:
    """对话式流量选型：大模型需求澄清 → 流量选型 → 达标设备参数 + 报告。

    返回 type：
      - clarify  {question, missing, missing_cn, params}  需用户补充参数
      - error    {detail}
      - done     {params, demand, passed[], passed_count, report}
    """
    from flow_chat import run_flow_chat

    return run_flow_chat(req.message, req.history, req.params)


@app.post("/parse-doc", tags=["工具"])
async def parse_doc(file: UploadFile = File(...)) -> dict:
    """导入 Word 文档需求：解析上传文档为纯文本。

    支持 .docx（python-docx 提取段落+表格）、.txt/.md（utf-8，回退 gbk）；
    .doc 为旧版 OLE 二进制，提示另存为 .docx。
    """
    import io

    name = (file.filename or "doc").strip()
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    raw = await file.read()
    if ext == "docx":
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            parts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells:
                        parts.append("，".join(cells))
            text = "\n".join(p for p in parts if p.strip())
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"docx 解析失败：{exc}") from exc
    elif ext in ("txt", "md", "markdown"):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("gbk", errors="replace")
    elif ext == "doc":
        raise HTTPException(status_code=400, detail=".doc 为旧版 Word 格式，请先用 Word 打开并「另存为 .docx」后再导入。")
    else:
        raise HTTPException(status_code=400, detail="仅支持 .docx / .txt / .md 文档。")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文档内容为空，未提取到可用的需求文本。")
    return {"filename": name, "text": text.strip()}
