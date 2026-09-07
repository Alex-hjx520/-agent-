# -*- coding: utf-8 -*-
"""对话式流量选型：大模型需求澄清 → 流量选型 → 达标设备参数 + 报告。

协议（POST /flow/chat）：
    请求 {message, history:[用户历史文本...], params:{已确认键值}}
    响应 type:
      - clarify: {question, missing:[键], missing_cn:[中文], params}
      - error:   {detail}
      - done:    {params, demand:{m_req/Δh/ρ/制冷剂}, passed:[达标设备(含参数)],
                  demand_failures, report}
"""
import json
import re

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

# 七个必填字段：6 工况参数 + 制冷剂
FLOW_KEYS = [
    "refrigerant", "cond_temp", "evap_temp", "subcooling",
    "superheat", "delta_pressure", "required_capacity",
]
FLOW_KEY_CN = {
    "refrigerant": "制冷剂类型",
    "cond_temp": "冷凝温度(℃)",
    "evap_temp": "蒸发温度(℃)",
    "subcooling": "过冷度(K)",
    "superheat": "过热度(K)",
    "delta_pressure": "允许压降(MPa)",
    "required_capacity": "需求制冷量(kW)",
}
_NUMERIC = {"cond_temp", "evap_temp", "subcooling", "superheat", "delta_pressure", "required_capacity"}


def _is_valid(key, val):
    """字段值是否有效：制冷剂为非空文本，数值型可转 float。"""
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return False
    if key in _NUMERIC:
        try:
            return float(s) > 0 if key in ("cond_temp", "required_capacity", "delta_pressure") else True
        except ValueError:
            return False
    return True


EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "你是制冷设备流量选型的需求解析助手。从用户对话中提取选型必需参数并判断缺失项。\n"
                "必需参数（全部必填）：\n"
                "  refrigerant 制冷剂（如 R410A/R32/R134a）；cond_temp 冷凝温度(℃)；\n"
                "  evap_temp 蒸发温度(℃)；subcooling 过冷度(K)；superheat 过热度(K)；\n"
                "  delta_pressure 允许压降(MPa)；required_capacity 需求制冷量(kW)。\n"
                "只输出 JSON：{\"values\": {\"参数键\": \"提取到的值\"}, \"missing\": [\"仍缺失的参数键\"]}\n"
                "规则：\n"
                "- 缺失项 = 本次对话未提供且 已确认参数 中也没有的键；\n"
                "- 若已确认参数已有某键且用户没改，missing 不含它、values 也不重复；\n"
                "- 数值只填数字（去单位），制冷剂填大写名称；未提及/不明确的键一律进 missing；\n"
                "- 不要输出 JSON 以外的任何文字。"
            )
        ),
        ("human", "已确认参数：{known}\n用户对话需求：{user_text}"),
    ]
)

REPORT_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "你是制冷设备流量选型报告助手。根据需求与达标设备生成 Markdown 选型报告。\n"
                "结构（Markdown）：\n"
                "# 流量选型报告\n"
                "## 1. 需求与工况\n用表格列出：制冷剂、冷凝/蒸发温度、过冷度、过热度、允许压降、需求制冷量，以及计算得到的需求质量流量 m_req(kg/h)、单位焓差(kJ/kg)、阀前液密度(kg/m³)。\n"
                "## 2. 达标设备排行\n用表格：名次 | 型号 | 设备类型 | 能力指标 | 说明。能力指标按类型填写：Kv 流量阀=Kv值+允许质量流量范围(kg/h)；四通换向阀=换向容量(kW)+占需求比。达标越靠前=越紧凑（流量阀 Kv 小 / 四通容量小）。\n"
                "## 3. 达标设备参数\n对前 3 台各给一个小节（型号作标题），用两列表格列出固定参数（系列、最大工作压力、Kv、压降边界、接管尺寸、动作方式、介质温度等给出的字段）。\n"
                "## 4. 结论与建议\n列表：达标设备数、推荐首选型号及理由、若不足/无达标给下一步建议。\n"
                "要求：只汇总输入数据，不编造；Kv 越小且达标者排序越靠前（最紧凑选型）。"
            )
        ),
        ("human", "用户需求原文：{user_query}\n需求侧计算：{demand}\n达标设备（含参数）：{passed_json}\n设备类型计数：{type_summary}"),
    ]
)


def _parse_number(raw):
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _jsonable(v):
    """递归 Decimal/类型安全化，保证可 JSON 序列化。"""
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    import decimal
    if isinstance(v, decimal.Decimal):
        return float(v)
    return v


def _extract_json(content):
    """从 LLM 输出提取 JSON 对象：去 ```json``` 围栏，取首尾平衡花括号。"""
    txt = str(content or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", txt)
    if fence:
        txt = fence.group(1).strip()
    a, b = txt.find("{"), txt.rfind("}")
    if a != -1 and b > a:
        txt = txt[a:b + 1]
    return json.loads(txt)


def run_flow_chat(message: str, history: list, params: dict | None) -> dict:
    """一轮对话处理：澄清缺失 → 齐了走流量选型并出报告。"""
    from app import get_llm  # 延迟导入

    known = {k: v for k, v in (params or {}).items() if _is_valid(k, v)}
    user_text = "；".join([*(history or []), message or ""]).strip()

    # 1) LLM 抽取
    llm = get_llm()
    resp = (EXTRACT_PROMPT | llm).invoke({
        "known": json.dumps(known, ensure_ascii=False),
        "user_text": user_text,
    })
    try:
        parsed = _extract_json(resp.content)
    except Exception as exc:
        return {"type": "error", "detail": f"需求解析失败：{exc}"}

    new_params = dict(known)
    for k, v in (parsed.get("values") or {}).items():
        if k in FLOW_KEYS and _is_valid(k, v):
            if k in _NUMERIC:
                nv = _parse_number(v)
                if nv is not None:
                    new_params[k] = nv
            else:
                new_params[k] = str(v).upper().replace(" ", "")
    missing = parsed.get("missing") or []
    missing = [k for k in missing if k in FLOW_KEYS and not _is_valid(k, new_params.get(k))]
    # 兜底：仍无值的键补进 missing
    for k in FLOW_KEYS:
        if k not in missing and not _is_valid(k, new_params.get(k)):
            missing.append(k)

    if missing:
        missing_cn = [FLOW_KEY_CN[k] for k in missing]
        q = ("还需要您提供以下信息以完成流量选型：" +
             "、".join(missing_cn) + "。\n例如：制冷剂 R410A，冷凝温度 45℃，蒸发温度 5℃，过冷度 5K，过热度 5K，允许压降 0.5MPa，需求制冷量 20kW。")
        return {"type": "clarify", "question": q, "missing": missing,
                "missing_cn": missing_cn, "params": new_params}

    # 2) 需求侧计算
    from flow_selection import demand_side, flow_select
    d = demand_side(new_params.get("refrigerant"), new_params.get("cond_temp"),
                    new_params.get("evap_temp"), new_params.get("subcooling"),
                    new_params.get("superheat"), new_params.get("required_capacity"))
    if not d.get("ok"):
        return {"type": "error", "detail": "；".join(d.get("failure", []))}

    # 3) 候选：RAG 文档库定位 + DB 参数回填 + 流量选型
    from flow_selection import extract_kv, extract_pressure_range
    cands = collect_all_candidates(user_text)
    out = flow_select(new_params.get("refrigerant"), new_params.get("cond_temp"),
                      new_params.get("evap_temp"), new_params.get("subcooling"),
                      new_params.get("superheat"), new_params.get("delta_pressure"),
                      new_params.get("required_capacity"), cands)
    if not out.get("ok"):
        return {"type": "error", "detail": "；".join(out.get("failure", []))}
    results = out.get("results", [])
    passed = [r for r in results if r.get("passed")]

    # 达标设备附原始固定参数（含 Kv/压力/接管等）
    from collections import Counter
    by_model = {c["model"]: (c["device_type"], c.get("parameters") or {}) for c in cands}
    passed_cards = []
    for r in passed[:12]:
        dt, raw = by_model.get(r["model"], ("", {}))
        raw = _jsonable(raw)
        keep = {
            "series": raw.get("series", ""),
            "kv_value": raw.get("kv_value"),
            "max_working_pressure": raw.get("max_working_pressure"),
            "pipe_size": raw.get("pipe_size"),
            "actuation_type": raw.get("actuation_type"),
            "valve_type": raw.get("valve_type"),
            "medium_temp_range": raw.get("medium_temp_range"),
            "refrigerant_compatibility": str(raw.get("refrigerant_compatibility", ""))[:80],
            "certification": raw.get("certification"),
        }
        pc = {
            "model": r["model"], "device_type": dt, "kv": r.get("kv"),
            "m_min": r.get("m_min"), "m_max": r.get("m_max"), "pos": r.get("pos"),
            "fixed_params": {k: v for k, v in keep.items() if v not in (None, "")},
        }
        if r.get("kind") == "capacity":
            pc.update({
                "kind": "capacity", "series_key": r.get("series_key"),
                "cap_kw": r.get("cap_kw"), "req_kw": r.get("req_kw"),
                "dp_bar": r.get("dp_bar"), "ratio": r.get("ratio"),
            })
        passed_cards.append(pc)

    # 4) 报告
    type_summary = dict(Counter(r.get("device_type") for r in passed))
    report = ""
    try:
        rr = (REPORT_PROMPT | llm).invoke({
            "user_query": user_text,
            "demand": json.dumps(d, ensure_ascii=False),
            "passed_json": json.dumps(passed_cards[:8], ensure_ascii=False),
            "type_summary": json.dumps(type_summary, ensure_ascii=False),
        })
        report = str(rr.content).strip()
    except Exception:
        report = "（报告生成失败，请查看上方达标设备）"

    return {
        "type": "done",
        "params": new_params,
        "demand": {k: d.get(k) for k in ("refrigerant", "m_req", "delta_h", "rho_liq")},
        "allowed_dp_mpa": new_params.get("delta_pressure"),
        "passed": passed_cards,
        "passed_count": len(passed),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "candidate_total": len(cands),
        "results": results,
        "report": report,
    }


def collect_all_candidates(extra_query: str = "") -> list[dict]:
    """候选来源（v2）：RAG 文档库检索定位型号 → DB 有回填参数 / 无则文档参数。

    原“数据库全表扫描”候选已废弃（DB 仅作参数回填）。
    """
    from rag_candidates import collect_rag_candidates
    return collect_rag_candidates(extra_query=extra_query or "")
