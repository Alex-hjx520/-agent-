# -*- coding: utf-8 -*-
"""按【质量流量窗口】的直接选型核心（新选型逻辑）。

需求输入（用户提供）：
    refrigerant 制冷剂、cond_temp 冷凝温度(℃)、evap_temp 蒸发温度(℃)、
    subcooling 过冷度(K)、superheat 过热度(K)、allowed_dp_mpa 允许压降(MPa)、
    required_capacity 需求制冷量(kW)

需求侧（CoolProp 物性）：
    Δh = h(蒸发压, te+SH) − h(过冷液, tc−SC)        [J/kg]
    需求质量流量 m_req = required_capacity·3.6e6 / Δh  [kg/h]
    阀前液密度 ρ = D(tc−SC, 液)                       [kg/m³]

设备侧（候选必须【字段齐全】：kv_value + 最小/最大阀前压降，缺任一整台不参与）：
    m = Kv·√(Δp_bar)·√(1000·ρ)                        [kg/h]
    Δp 上界取 min(设备最大压降, 用户允许压降)（允许压降=系统可给阀的压降上限）
    Δp 下界取 设备最小压降；若 允许压降 < 设备最小压降 → 该设备无法参与（窗口空）

达标判定：m_min ≤ m_req ≤ m_max
"""
import math

try:  # noqa: E402
    from CoolProp.CoolProp import PropsSI  # type: ignore
    _HAS_COOLPROP = True
except Exception:  # pragma: no cover
    PropsSI = None
    _HAS_COOLPROP = False

# 用户写法 → CoolProp 介质名
_REF_MAP = {
    "R22": "R22", "R32": "R32", "R134A": "R134a", "R404A": "R404A",
    "R407C": "R407C", "R410A": "R410A", "R507": "R507A", "R507A": "R507A",
    "R290": "R290", "R448A": "R448A", "R449A": "R449A", "R454B": "R454B",
    "R1234YF": "R1234yf", "R1234ZE": "R1234ze(E)", "R744": "R744", "CO2": "R744",
}
_BAR_MPA = 10.0  # 1 MPa = 10 bar（Kv 公式用 bar）


def _resolve_refrigerant(name):
    if not name:
        return None
    return _REF_MAP.get(str(name).upper().replace(" ", "").replace("-", ""))


def _num(v):
    """宽松转 float；空/'-'/None 返回 None。"""
    if v in (None, "", "-"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extract_kv(p: dict):
    """候选 Kv 值（m³/h），>0 才有效。兼容 kv_value/Kv值。"""
    v = _num(p.get("kv_value") or p.get("Kv值"))
    return v if v and v > 0 else None


def extract_pressure_range(p: dict):
    """提取候选 最小/最大阀前压降 (MPa)，>0 才有效；可只给其一（None = 该边界未提供）。

    兼容数据库列（min_op_pressure_diff / max_op_pressure_diff_gas·ac·dc /
    max_op_pressure_diff / max_working_pressure_diff / min_opening_pressure_diff_gas）
    与文档中文键（最大/最小阀前压降、最大/最小工作压差、最大/最小动作压差）。
    多个上界（gas/ac/dc）取最小值=最保守；多个下界取最大值=最保守。
    """
    max_keys = (
        "max_op_pressure_diff_gas", "max_op_pressure_diff_ac", "max_op_pressure_diff_dc",
        "max_op_pressure_diff", "max_working_pressure_diff",
        "最大阀前压降", "最大工作压差", "最大动作压差", "最大压差AC",
    )
    min_keys = (
        "min_op_pressure_diff", "min_opening_pressure_diff_gas", "min_working_pressure_diff",
        "最小阀前压降", "最小工作压差", "最小动作压差", "最小开阀压差",
    )
    hi_vals = [x for x in (_num(p.get(k)) for k in max_keys) if x and x > 0]
    lo_vals = [x for x in (_num(p.get(k)) for k in min_keys) if x and x > 0]
    hi_val = min(hi_vals) if hi_vals else None   # 上界取最严（小）
    lo_val = max(lo_vals) if lo_vals else None   # 下界取最严（大）
    return lo_val, hi_val


def _m_flow(kv, dp_bar, rho):
    """质量流量公式：m[kg/h] = Kv·√(Δp_bar)·√(1000·ρ)。"""
    return kv * math.sqrt(max(dp_bar, 0.0)) * math.sqrt(1000.0 * rho)


def demand_side(refrigerant, cond_temp, evap_temp, subcooling, superheat, required_capacity):
    """需求侧：算 Δh、阀前液密度 ρ、需求质量流量 m_req。返回 dict 或 {'ok':False,failure:[...]}。"""
    if not _HAS_COOLPROP:
        return {"ok": False, "failure": ["CoolProp 未安装，无法计算制冷剂物性。"]}
    ref = _resolve_refrigerant(refrigerant)
    if not ref:
        return {"ok": False, "failure": [f"无法识别的制冷剂：{refrigerant}。"]}
    for label, v in (("冷凝温度", cond_temp), ("蒸发温度", evap_temp), ("需求制冷量", required_capacity)):
        if v is None:
            return {"ok": False, "failure": [f"缺少{label}。"]}
    try:
        tc = float(cond_temp)
        te = float(evap_temp)
        sc = float(subcooling or 0.0)
        sh = float(superheat or 0.0)
        req_kw = float(required_capacity)
        if req_kw <= 0:
            return {"ok": False, "failure": ["需求制冷量必须为正数。"]}
        if tc <= te:
            return {"ok": False, "failure": [f"冷凝温度 {tc}℃ 应高于蒸发温度 {te}℃。"]}
        t_liq = tc - sc + 273.15
        p_evap = PropsSI("P", "T", te + 273.15, "Q", 1.0, ref)      # Pa
        h_liq = PropsSI("H", "T", t_liq, "Q", 0.0, ref)             # 阀前过冷液焓 J/kg
        h_out = PropsSI("H", "T", te + sh + 273.15, "P", p_evap, ref)  # 蒸发器出口过热焓
        rho_liq = PropsSI("D", "T", t_liq, "Q", 0.0, ref)           # 阀前液密度 kg/m³
        d_h = h_out - h_liq
        if d_h <= 0:
            return {"ok": False, "failure": ["焓差非正，请检查温度/过冷/过热取值。"]}
        m_req = round(req_kw * 3.6e6 / d_h, 3)                       # kg/h
        return {
            "ok": True, "refrigerant": ref, "m_req": m_req,
            "delta_h": round(d_h / 1000.0, 3), "rho_liq": round(rho_liq, 2),
        }
    except Exception as exc:
        return {"ok": False, "failure": [f"CoolProp 物性计算失败：{exc}"]}


def score_device(kv, dp_min_mpa, dp_max_mpa, allowed_dp_mpa, m_req, rho_liq):
    """单台判定：需求质量流量 m_req 是否在该设备压降边界允许的质量流量范围内。

    边界策略（压降→流量单调，故“需求流量 ≤ 某压降对应流量”等价于“所需压降 ≤ 该压降”）：
      - 有最大压降 → 只约束上界：m_req ≤ m_max（m_max 在 min(设备max, 允许压降) 下算出）
      - 有最小压降 → 只约束下界：m_req ≥ m_min
      - 两者都有 → 窗口 [m_min, m_max]；都没有 → 无法判定
    允许压降 = 系统可给阀的压降上限（只影响上界）。
    """
    lo_mpa = dp_min_mpa if (dp_min_mpa and dp_min_mpa > 0) else None
    hi_mpa = dp_max_mpa if (dp_max_mpa and dp_max_mpa > 0) else None
    if allowed_dp_mpa and allowed_dp_mpa > 0:
        hi_mpa = min(hi_mpa, allowed_dp_mpa) if hi_mpa else allowed_dp_mpa

    m_min = round(_m_flow(kv, lo_mpa * _BAR_MPA, rho_liq), 3) if lo_mpa else None
    m_max = round(_m_flow(kv, hi_mpa * _BAR_MPA, rho_liq), 3) if hi_mpa else None
    dp_eff = (round(lo_mpa, 4) if lo_mpa else None,
              round(hi_mpa, 4) if hi_mpa else None)

    if lo_mpa and hi_mpa and hi_mpa < lo_mpa:
        return {"passed": False, "m_min": m_min, "m_max": m_max, "dp_eff": dp_eff,
                "pos": None,
                "reason": f"允许压降({allowed_dp_mpa}MPa)低于设备最小压降({lo_mpa}MPa)，无法工作"}
    if lo_mpa is None and hi_mpa is None:
        return {"passed": False, "m_min": None, "m_max": None, "dp_eff": (None, None),
                "pos": None, "reason": "无压降边界（min/max 均未提供）"}
    if lo_mpa is None:
        # 只有最大压降：需求 m_req 不超过上限即可（只需小于最大压降对应流量）
        passed = m_req <= m_max
        return {"passed": passed, "m_min": None, "m_max": m_max, "dp_eff": dp_eff,
                "pos": None,
                "reason": "" if passed else
                f"需求 m_req {m_req}kg/h 超过该设备最大允许流量 {m_max}kg/h（仅给最大压降）"}
    if hi_mpa is None:
        # 只有最小压降：需求 m_req 不低于下限即可（只需大于最小压降对应流量）
        passed = m_req >= m_min
        return {"passed": passed, "m_min": m_min, "m_max": None, "dp_eff": dp_eff,
                "pos": None,
                "reason": "" if passed else
                f"需求 m_req {m_req}kg/h 低于该设备最小允许流量 {m_min}kg/h（仅给最小压降）"}
    # 双边窗口
    passed = m_min <= m_req <= m_max
    pos = round((m_req - m_min) / (m_max - m_min), 4) if m_max > m_min else None
    return {"passed": passed, "m_min": m_min, "m_max": m_max, "dp_eff": dp_eff,
            "pos": pos,
            "reason": "" if passed else ("低于下限" if m_req < m_min else "超过上限")}


def flow_select(refrigerant, cond_temp, evap_temp, subcooling, superheat,
                allowed_dp_mpa, required_capacity, candidates):
    """直接选型主入口。

    candidates: [{model, series?, parameters:{kv_value, min/max 压降...}}]
    返回 {demand:{...}, results:[...]}；每候选：
      - 有 kv 且至少有 min/max 之一 → 参与判定（单边：只给 max 判 m_req≤m_max；只给 min 判 m_req≥m_min）
      - 无 kv 或 min/max 均无 → skipped（标注原因）
    """
    d = demand_side(refrigerant, cond_temp, evap_temp, subcooling, superheat, required_capacity)
    if not d.get("ok"):
        return {"ok": False, "failure": d.get("failure", []), "demand": None, "results": []}
    m_req = d["m_req"]
    rho = d["rho_liq"]
    results = []
    for c in candidates or []:
        p = c.get("parameters") or {}
        model = c.get("model", "")
        dt = c.get("device_type")
        # 容量型设备（非 Kv 流量型）：四通=换向容量表；热力膨胀阀=制冷量扩展表
        if dt == "四通换向阀":
            from four_way_capacity import judge_four_way
            fr = judge_four_way(model, c.get("series") or p.get("series", ""),
                                refrigerant, cond_temp, evap_temp,
                                allowed_dp_mpa, required_capacity)
            fr["source"] = c.get("source", "")
            results.append(fr)
            continue
        if dt == "热力膨胀阀":
            from tev_capacity import judge_tev
            tr = judge_tev(model, c.get("series") or p.get("series", ""),
                           p.get("valve_orifice_no"), refrigerant, cond_temp, evap_temp,
                           subcooling, allowed_dp_mpa, required_capacity)
            tr["source"] = c.get("source", "")
            results.append(tr)
            continue
        kv = extract_kv(p)
        lo, hi = extract_pressure_range(p)
        if kv is None or (lo is None and hi is None):
            reason = ("缺 kv 值，无法算流量" if kv is None else
                      "无压降边界（min/max 均未提供）")
            results.append({"model": model, "series": p.get("series", ""),
                            "device_type": c.get("device_type", ""), "source": c.get("source", ""),
                            "kv": kv, "skipped": True, "reason": reason})
            continue
        s = score_device(kv, lo, hi, allowed_dp_mpa, m_req, rho)
        results.append({
            "model": model, "series": p.get("series", ""),
            "device_type": c.get("device_type", ""), "source": c.get("source", ""),
            "kv": kv, "skipped": False, "kind": "flow", "m_req": m_req,
            **s,
        })

    # 排序：达标靠前；达标组内 容量型(四通,容量升序) 在前、流量型(Kv 升序紧凑) 在后
    def _skey(r):
        grp = 0 if r.get("passed") else (2 if r.get("skipped") else 1)
        if r.get("kind") == "capacity":
            return (grp, 0, r.get("cap_kw") or 0.0)
        return (grp, 1, r.get("kv") or 1e9)
    results.sort(key=_skey)
    return {"ok": True, "demand": {k: d.get(k) for k in ("refrigerant", "m_req", "delta_h", "rho_liq")},
            "allowed_dp_mpa": allowed_dp_mpa, "results": results}
