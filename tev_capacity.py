# -*- coding: utf-8 -*-
"""热力膨胀阀（TEV）「制冷量扩展表」容量判定（容量型，非 Kv 流量型）。

热力膨胀阀能力=每只阀口在该工况下能提供的实际制冷量 kW。判定流程：
  1) 系列/阀口：DB 型号的 series（RFKH 等）+ valve_orifice_no（阀口编号）；
  2) 蒸发温度 → 该阀口 11 点表插值；冷凝温度 → 相邻块(25/35/45/55℃)插值；
  3) 修正：过冷度 fsub、阀前压降 fp（表基准冷凝 32℃）；
  4) 达标：该阀制冷量 Q_valve ≥ 需求制冷量 Q_req（容量型覆盖需求）；
     容量明显过大(>1.5×需求) 提示改小阀口（固定流口不可调、难控）。
"""
import math
import re

from data.tev_capacity_data import (
    EVAP_AXIS, _FSUB, _FP_BARS, _FP_EVAP_AXIS, _FP_ROWS,
    available_refs, block_capacity,
)


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _interp(xs, ys, x):
    """一维线性插值（xs 升序，x 越界取端点）。"""
    n = len(xs)
    if n == 0:
        return None
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(n - 1):
        if xs[i] <= x <= xs[i + 1]:
            if xs[i + 1] == xs[i]:
                return ys[i]
            return ys[i] + (x - xs[i]) / (xs[i + 1] - xs[i]) * (ys[i + 1] - ys[i])
    return ys[-1]


def _ref_map(name):
    if not name:
        return None
    m = {"R22": "R22", "R134A": "R134a", "R407C": "R407C",
         "R404A": "R404A", "R410A": "R410A", "R507A": "R507"}
    return m.get(str(name).upper().replace(" ", "").replace("-", ""))


def _series_from_model_or_field(series_field, model):
    s = str(series_field or "").upper()
    if s:
        return s
    m = re_search_prefix(model)
    return m


def re_search_prefix(model):
    mm = re.search(r"(RFKH|RFGB|RFGC|RFGD10|RFGD|RFG)", str(model or "").upper())
    return mm.group(1) if mm else ""


def judge_tev(model, series_field, orifice_no, refrigerant, cond_temp, evap_temp,
              subcooling, allowed_dp_mpa, required_capacity):
    """容量型判定热力膨胀阀。返回与流量阀同构结果（kind='capacity'）。"""
    series = _series_from_model_or_field(series_field, model)
    base = {
        "model": model, "series": series_field or "", "device_type": "热力膨胀阀",
        "source": "", "kv": None, "m_min": None, "m_max": None,
        "skipped": False, "kind": "capacity",
        "cap_label": "阀制冷量", "dp_label": "修正压降",
    }
    if series != "RFKH":
        return {**base, "skipped": True,
                "reason": f"系列 {series_field or model} 尚未接入制冷量扩展表（当前支持 RFKH）"}
    refs = available_refs(series)
    if not refs:
        return {**base, "skipped": True, "reason": "RFKH 制冷量扩展表数据缺失"}
    ref = _ref_map(refrigerant)
    if ref not in refs:
        return {**base, "skipped": True,
                "reason": f"制冷量扩展表暂未收录 {refrigerant}（已收录 {'/'.join(refs)}）"}
    orifice = str(orifice_no or "").strip()
    if not orifice:
        return {**base, "skipped": True,
                "reason": "缺阀口编号（valve_orifice_no），无法查制冷量扩展表"}

    try:
        tc = float(cond_temp)
        te = float(evap_temp)
        sc = float(subcooling or 0.0)
        req = float(required_capacity)
    except (TypeError, ValueError):
        return {**base, "skipped": True, "reason": "温度/过冷/制冷量参数异常"}
    if req <= 0:
        return {**base, "skipped": True, "reason": "需求制冷量须为正"}
    # 蒸发温度截到表轴范围内
    if te < -40 or te > 10:
        return {**base, "skipped": True, "reason": f"蒸发温度 {te}℃ 超出扩展表范围(-40~10℃)"}

    # 阀口在该蒸发温度的 11 点（EVAP_AXIS 与表行一致）→ 先按表行离散值取，再对块间冷凝插值
    def _q_at_cond(cond):
        pts = [block_capacity(series, ref, cond, orifice, idx) for idx in range(len(EVAP_AXIS))]
        if any(p is None for p in pts):
            return None
        return _interp(EVAP_AXIS, pts, te)

    conds = sorted(k for k in (25, 35, 45, 55) if block_capacity(series, ref, k, orifice, 0) is not None)
    if not conds:
        return {**base, "skipped": True,
                "reason": f"扩展表中无 阀口{orifice}（冷媒{ref}）数据"}
    q1 = _q_at_cond(conds[0])
    q2 = _q_at_cond(conds[-1])
    q_at = _interp(conds, [_q_at_cond(c) for c in conds], tc)
    if q_at is None:
        return {**base, "skipped": True, "reason": "扩展表插值失败"}

    # 过冷修正 fsub
    fs = _interp(_FSUB["K"], _FSUB["f"], _clamp(sc, 0, 50))
    # 压降修正 fp（允许压降 MPa→bar，表范围 0~2bar，缺省按 1bar）
    dp_bar = 1.0 if not (allowed_dp_mpa and allowed_dp_mpa > 0) else _clamp(allowed_dp_mpa * 10.0, 0.0, 2.0)
    # fp 是 bar 离散行 × 蒸发 -40..15 列：先对 bar 行在 evap 插值得到 bar->f
    fp_by_bar = [_interp(_FP_EVAP_AXIS, row, te) for row in _FP_ROWS]
    fp = _interp(_FP_BARS, fp_by_bar, dp_bar) if fp_by_bar else 1.0

    cap = q_at * (fs or 1.0) * (fp or 1.0)
    ratio = round(cap / req, 4)
    passed = cap >= req
    if passed:
        if ratio > 1.5:
            reason = (f"阀制冷量 {cap:.2f}kW 为需求 {ratio * 100:.0f}%（固定流口过大难控，"
                      f"建议换更小阀口）")
        else:
            reason = ""
    else:
        reason = (f"阀制冷量 {cap:.2f}kW < 需求 {req:.2f}kW，"
                  f"请换更大阀口（当前阀口 {orifice}）")
    return {
        **base, "series_key": orifice, "cap_kw": round(cap, 2),
        "req_kw": round(req, 3), "ratio": ratio, "dp_bar": round(dp_bar, 2),
        "cap_at_kw": round(q_at, 2), "passed": passed, "reason": reason,
    }
