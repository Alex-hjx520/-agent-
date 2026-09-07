# -*- coding: utf-8 -*-
"""四通换向阀「换向容量」选型判定（容量型，非 Kv 流量型）。

四通换向阀的能力标定是换向名义容量（冷量 KW），厂家给 SHF（铜）/ SHF-G（不锈钢）
的冷量选型表：按 制冷剂 × ΔP(0.1/0.2bar) × 工况(1/2) 查名义容量。

判定逻辑（用户早期确认的规则）：
  - 制冷剂须在容量表列内（R22/R134a/R407C/R410A/R32）；
  - ΔP 取 min(用户允许压降×10, 0.2bar)，未给默认 0.1bar；落在 (0.1,0.2) 内线性插值；
  - 工况接近度 t∈[0,1]（0=工况1 tc38/te5，1=工况2 tc54.4/te7.2）加权工况1/工况2 容量；
  - 需求制冷量 req_kw；容量比 ratio = 换向容量 / req_kw；
  - 达标：ratio ≥ 0.6（选型表注明 R32 系统容量须 ≥60%，且不建议用于 <60% 的系统）。
"""
import math
import re

from data.shf_capacity_data import (
    _SHF_CAP, _SHFG_CAP,
    _SHF_SERIES, _SHFG_SERIES,
    shf_capacity,
)

_CU_POOL = {int(s) for s in _SHF_SERIES}
_G_POOL = {int(s) for s in _SHFG_SERIES}


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _ref_map(name):
    if not name:
        return None
    m = {
        "R22": "R22", "R32": "R32", "R134A": "R134a", "R134A(E)": "R134a",
        "R407C": "R407C", "R410A": "R410A", "R404A": "R404A",
    }
    return m.get(str(name).upper().replace(" ", "").replace("-", ""))


def parse_shf_series(model, series_field):
    """把 DB 型号解析为容量表系列数字 + 是否 G。

    铜（series='SHF'）：SHF-4H-23U-P-A → 4；SHF(L)-100-1012 → 100
    不锈钢（series='SHF-G'）：SHF(G)-13H-45 → 13；SHF-35B-79G47 → 35
    保留连字符再取数字块，只认落进该材质系列集合的数字（规格号/接管号不落集合，
    避免 SHF-50-79G45 误认 5079 粘连）。
    """
    model = str(model or "").upper()
    series_field = str(series_field or "")
    is_g = "G" in series_field.upper()
    # 去除括号（不取连字符）
    nm = re.sub(r"[()（）]", "", model)
    nums = re.findall(r"\d+", nm)
    pool = _G_POOL if is_g else _CU_POOL
    for n in nums:
        try:
            v = int(n)
        except ValueError:
            continue
        if v in pool:
            return v, is_g
    return None, is_g


def judge_four_way(model, series_field, refrigerant, cond_temp, evap_temp,
                   allowed_dp_mpa, required_capacity):
    """容量型判定四通换向阀。返回选型结果 dict（与流量阀同构，kind='capacity'）。

    返回键：model/series/device_type/source/kind/skipped/…
      - skipped=True（无法按容量表判）→ reason
      - 参与：cap_kw 换向容量、req_kw 需求容量、ratio、dp_bar、passed、reason
    """
    series_num, is_g = parse_shf_series(model, series_field)
    base = {
        "model": model, "series": series_field or "", "device_type": "四通换向阀",
        "source": "", "kv": None, "m_min": None, "m_max": None,
        "skipped": False, "kind": "capacity",
        "cap_label": "换向容量", "dp_label": "换向压降",
    }
    if series_num is None:
        return {**base, "skipped": True,
                "reason": "型号无对应容量表系列（需 SHF 铜 / SHF-G 不锈钢规格）"}
    ref = _ref_map(refrigerant)
    table_refs = ("R22", "R407C", "R410A", "R134a", "R32") if is_g else \
                 ("R22", "R134a", "R407C", "R410A", "R32")
    if ref not in table_refs:
        return {**base, "skipped": True,
                "reason": f"容量表未收录制冷剂 {refrigerant}（仅 {'/'.join(table_refs)}）"}

    try:
        tc = float(cond_temp)
        te = float(evap_temp)
        req = float(required_capacity)
    except (TypeError, ValueError):
        return {**base, "skipped": True, "reason": "温度/制冷量参数异常"}
    if req <= 0:
        return {**base, "skipped": True, "reason": "需求制冷量须为正"}

    # ΔP：允许压降(MPa)→bar，封顶 0.2bar（容量表仅 0.1/0.2 两档）
    dp_mpa = allowed_dp_mpa if (allowed_dp_mpa and allowed_dp_mpa > 0) else None
    dp_bar = 0.1 if dp_mpa is None else _clamp(dp_mpa * 10.0, 0.1, 0.2)

    # 工况接近度 t
    t = _clamp(0.5 * (tc - 38.0) / (54.4 - 38.0) + 0.5 * (te - 5.0) / (7.2 - 5.0), 0.0, 1.0)

    def _at(cond_idx):
        c_lo = shf_capacity(series_num, ref, cond_idx, 0, is_g)
        c_hi = shf_capacity(series_num, ref, cond_idx, 1, is_g)
        if dp_bar <= 0.1:
            return c_lo
        if dp_bar >= 0.2:
            return c_hi
        return c_lo + (dp_bar - 0.1) / (0.2 - 0.1) * (c_hi - c_lo)

    c1 = _at(0)
    c2 = _at(1)
    cap = (1.0 - t) * c1 + t * c2
    ratio = round(cap / req, 4) if req else 0.0
    passed = ratio >= 0.6
    reason = ""
    if passed:
        if ratio < 1.0:
            reason = (f"换向容量 {cap:.1f}kW 为需求的 {ratio * 100:.0f}%"
                      f"（≥60% 可换向，余量偏紧，建议加大系列）")
        elif ref == "R32" and ratio < 1.3:
            reason = f"R32 系统：容量为需求 {ratio * 100:.0f}%，已≥60%，请复核低压差换向"
    else:
        need = round(req * 0.6, 1)
        reason = (f"换向容量 {cap:.1f}kW < 需求 60%（需 ≥{need}kW），"
                  f"请升级到更大系列")
    return {
        **base, "series_key": (f"{series_num}G" if is_g else str(series_num)),
        "cap_kw": round(cap, 2), "req_kw": round(req, 3),
        "dp_bar": round(dp_bar, 2), "ratio": ratio,
        "passed": passed, "reason": reason,
    }
