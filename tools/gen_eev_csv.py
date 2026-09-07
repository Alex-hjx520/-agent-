# -*- coding: utf-8 -*-
"""
根据三花样本《三花商用出品-流体控制部件(包含全部部件内容)》中
电子膨胀阀 VPF / DPF / LPF / PEV 系列数据，生成导入数据库用的 CSV。

目标表结构 electronic_expansion_valve：
  id(自增), model, series, refrigerant_compatibility, medium_temp_min/max,
  ambient_temp_min/max, max_working_pressure, max_working_pressure_diff,
  kv_value, pipe_size, full_open_pulses, body_shape, has_sight_glass,
  oil_system_compatibility, certification, remark

缺失数据用 "-" 填充；has_sight_glass 用 0/1。
输出编码 utf-8-sig（Excel 可直接打开不乱码）。
"""
import csv
from pathlib import Path

OUT_DIR = Path("数据库信息(开发结束后删除)")
OUT_FILE = OUT_DIR / "electronic_expansion_valve.csv"

HEADER = [
    "model", "series", "refrigerant_compatibility",
    "medium_temp_min", "medium_temp_max",
    "ambient_temp_min", "ambient_temp_max",
    "max_working_pressure", "max_working_pressure_diff",
    "kv_value", "pipe_size", "full_open_pulses",
    "body_shape", "has_sight_glass",
    "oil_system_compatibility", "certification", "remark",
]

# ---------- 各系列通用规格 ----------
REFRIG_VPF = "R22,R134a,R404A,R407C,R410A,R507,R1234ze"
REFRIG_DPF_TS = "R22,R134a,R404A,R407C,R410A,R507,R32,R290"
REFRIG_DPF_HP = "R22,R134a,R407C,R410A,R32,R290"
REFRIG_LPF = "R22,R134a,R404A,R407C,R410A"
REFRIG_LPF_T = "R22,R134a,R404A,R407C,R410A,R744"
REFRIG_PEV = "R134a,R404A,R407C,R410A,R744"

CERT_VPF = "UL&TUV,PED,EAC"
CERT_DPF = "UL&CUL,LVD/PED"
CERT_LPF = "UL&TUV,LVD/PED"
CERT_PEV = "-"

# 介质/环境温度 (℃)
VPF_T = (-40, 90, -40, 60)
DPF_TS_T = (-40, 85, -30, 60)
DPF_HP_T = (-30, 70, -30, 60)
LPF_T = (-40, 70, -40, 60)
PEV_T = (-40, 70, -40, 55)

# VPF 各基型的 (最高工作压力 MPa, 最大工作压差 MPa, 全开脉冲)
VPF_SPEC = {
    12.5: (5.0, 3.9, 2600),
    25:   (5.0, 3.9, 2600),
    50:   (5.0, 3.9, 2600),
    100:  (5.0, 3.9, 3500),
    150:  (5.0, 3.9, 3800),
    250:  (4.5, 3.5, 3800),
    400:  (4.5, 3.5, 3800),
    800:  (2.5, 2.5, 3800),
}
VPF_KV = {12.5: 0.8, 25: 1.3, 50: 2.4, 100: 4.0, 150: 7.7, 250: 14.0, 400: 17.0, 800: 34.0}

rows = []


def add(model, series, refrigerant, temps, press, press_diff, kv,
        pipe, pulses, shape, sight, oil, cert, remark=""):
    """press/press_diff 可为数字或 "-"；kv 可为数字或 "-"。"""
    rows.append([
        model, series, refrigerant,
        temps[0], temps[1], temps[2], temps[3],
        press, press_diff, kv, pipe, pulses,
        shape, sight, oil, cert, remark,
    ])


# =====================================================================
# VPF 系列（有油系统型号）
# =====================================================================
VPF_OIL = [
    # (型号, 接管尺寸, 阀体形状, 视液镜)
    ("VPF12.5H52", "5/8×5/8",  "直通型", 0),
    ("VPF12.5H53", "7/8×7/8",  "直通型", 0),
    ("VPF12.5H58", "5/8×5/8",  "L型",    0),
    ("VPF12.5H59", "7/8×7/8",  "L型",    0),
    ("VPF25H52",   "5/8×5/8",  "直通型", 0),
    ("VPF25H53",   "7/8×7/8",  "直通型", 0),
    ("VPF25H58",   "5/8×5/8",  "L型",    0),
    ("VPF25H59",   "7/8×7/8",  "L型",    0),
    ("VPF50H01",   "7/8×1-1/8", "直通型", 1),
    ("VPF50H02",   "1-1/8×1-1/8", "直通型", 1),
    ("VPF50H03",   "1-1/8×1-3/8", "直通型", 1),
    ("VPF50H04",   "-",         "直通型", 1),
    ("VPF50H06",   "22×28mm",  "直通型", 1),
    ("VPF50H07",   "28×28mm",  "直通型", 1),
    ("VPF50H08",   "28×35mm",  "直通型", 1),
    ("VPF50H51",   "7/8×7/8",  "直通型", 0),
    ("VPF50H53",   "1-1/8×1-1/8", "直通型", 0),
    ("VPF50H54",   "1-1/8×1-3/8", "直通型", 0),
    ("VPF100H01",  "1-1/8×1-1/8", "直通型", 1),
    ("VPF100H02",  "1-1/8×1-3/8", "直通型", 1),
    ("VPF100H03",  "1-3/8×1-3/8", "直通型", 1),
    ("VPF100H05",  "28×35mm",  "直通型", 1),
    ("VPF100H06",  "28×28mm",  "直通型", 1),
    ("VPF100H51",  "1-1/8×1-1/8", "直通型", 0),
    ("VPF100H53",  "1-3/8×1-3/8", "直通型", 0),
    ("VPF150H01",  "1-1/8×1-3/8", "L型",   1),
    ("VPF150H02",  "1-5/8×1-5/8", "L型",   1),
    ("VPF250H41",  "1-1/8×1-1/8", "直通型", 1),
    ("VPF250H42",  "1-3/8×1-3/8", "直通型", 1),
    ("VPF250H43",  "1-5/8×1-5/8", "直通型", 1),
    ("VPF250H44",  "28×28mm",  "直通型", 1),
    ("VPF250H45",  "42×42mm",  "直通型", 1),
    ("VPF400H01",  "1-5/8×1-5/8", "直通型", 1),
    ("VPF400H02",  "42×42mm",  "直通型", 1),
    ("VPF400H03",  "2-1/8×2-1/8", "直通型", 1),
    ("VPF800H01",  "3-1/8×3-1/8", "直通型", 1),
]

for model, pipe, shape, sight in VPF_OIL:
    base = float(model[3:5].replace("VPF", "")) if False else None
    # 解析基型（VPF 后第一个数字段，如 VPF12.5 -> 12.5, VPF100 -> 100）
    digits = model[3:]
    base_num = None
    for sep in (".",):
        pass
    # 基型取型号开头的数字部分（直到非数字/小数点）
    import re
    m = re.match(r"(\d+(?:\.\d+)?)", model[3:])
    base_num = float(m.group(1))
    press, pdiff, pulses = VPF_SPEC[base_num]
    add(model, "VPF", REFRIG_VPF, VPF_T, press, pdiff, VPF_KV[base_num],
        pipe, pulses, shape, sight, "有油", CERT_VPF)

# VPF 系列（无油系统型号）
VPF_OILLESS = [
    ("VPF12.5H82", "5/8×5/8",    "直通型", 0),
    ("VPF25H83",   "7/8×7/8",    "直通型", 0),
    ("VPF50H81",   "7/8×7/8",    "直通型", 1),
    ("VPF50H83",   "1-1/8×1-1/8","直通型", 1),
    ("VPF100H81",  "1-1/8×1-1/8","直通型", 1),
    ("VPF100H83",  "1-3/8×1-3/8","直通型", 1),
    ("VPF150H82",  "1-5/8×1-5/8","直角型", 1),
    ("VPF250H92",  "1-3/8×1-3/8","直通型", 1),
    ("VPF250H93",  "1-5/8×1-5/8","直通型", 1),
    ("VPF400H81",  "1-5/8×1-5/8","直通型", 1),
    ("VPF400H83",  "2-1/8×2-1/8","直通型", 1),
]
for model, pipe, shape, sight in VPF_OILLESS:
    import re
    m = re.match(r"(\d+(?:\.\d+)?)", model[3:])
    base_num = float(m.group(1))
    press, pdiff, pulses = VPF_SPEC[base_num]
    add(model, "VPF", REFRIG_VPF, VPF_T, press, pdiff, VPF_KV[base_num],
        pipe, pulses, shape, sight, "无油", CERT_VPF)

# =====================================================================
# DPF-TS/S 系列
#   通用：介质 -40~85℃，环境 -30~60℃，全开脉冲 500，认证 UL&CUL,LVD/PED
#   最大工作压力：TS(1.0~3.2) 为 4.2MPa；S03(4.0~7.5) 为 4.5MPa
#   最大工作压差：TS(1.0~3.2) 为 3.5MPa；S03(4.0~7.5) 为 3.0MPa
#   接管：1.0~2.4 -> 6.35mm；3.0~3.2 -> 7.94mm；4.0~7.5(S03) -> 15.88mm
# =====================================================================
DPF_TS = [
    # (型号, Kv, 压力, 压差, 接管)
    ("DPF(TS)1.0C-15",   0.03, 4.2, 3.5, "6.35mm"),
    ("DPF(TS)1.3C-21",   0.05, 4.2, 3.5, "6.35mm"),
    ("DPF(TS)1.65C-36",  0.08, 4.2, 3.5, "6.35mm"),
    ("DPF(TS)1.8C-69",   0.10, 4.2, 3.5, "6.35mm"),
    ("DPF(TS)2.0C-33",   0.16, 4.2, 3.5, "6.35mm"),
    ("DPF(TS)2.2C-24",   0.20, 4.2, 3.5, "6.35mm"),
    ("DPF(TS)2.4C-40",   0.23, 4.2, 3.5, "6.35mm"),
    ("DPF(TS)3.0C-29",   0.39, 4.2, 3.5, "7.94mm"),
    ("DPF(TS)3.2C-30",   0.43, 4.2, 3.5, "7.94mm"),
    ("DPF(S03)4.0C-01",  0.50, 4.5, 3.0, "15.88mm"),
    ("DPF(S03)4.5C-01",  0.70, 4.5, 3.0, "15.88mm"),
    ("DPF(S03)5.5C-01",  0.90, 4.5, 3.0, "15.88mm"),
    ("DPF(S03)6.5C-02",  1.10, 4.5, 3.0, "15.88mm"),
    ("DPF(S03)7.0C-01",  1.22, 4.5, 3.0, "15.88mm"),
    ("DPF(S03)7.5C-01",  1.35, 4.5, 3.0, "15.88mm"),
]
for model, kv, press, pdiff, pipe in DPF_TS:
    add(model, "DPF", REFRIG_DPF_TS, DPF_TS_T, press, pdiff, kv,
        pipe, 500, "-", 0, "-", CERT_DPF)

# =====================================================================
# DPF 低温热泵系列
#   通用：介质 -30~70℃，环境 -30~60℃，最大工作压差 35bar=3.5MPa，
#         全开脉冲 500，认证 UL&CUL,LVD/PED
#   最大工作压力：1.0~2.4/3.2 为 42bar=4.2MPa；3.0 为 45bar=4.5MPa
#   阀体形状：3.0/3.2 为直角型；1.0~2.4 未标注 -> -
#   接管：1.0~2.4 -> 6.35mm；3.0/3.2 -> 7.94mm
# =====================================================================
DPF_HP = [
    # (型号, Kv, 压力, 压差, 阀体形状)   -- 尺寸暂标为-
    ("DPF(TS)1.0C-44",   0.03, 4.2, 3.5, "-"),
    ("DPF(TS)1.3C-77",   0.05, 4.2, 3.5, "-"),
    ("DPF(TS)1.65C-97",  0.08, 4.2, 3.5, "-"),
    ("DPF(TS)1.8C-137",  0.10, 4.2, 3.5, "-"),
    ("DPF(TS)2.0C-70",   0.16, 4.2, 3.5, "-"),
    ("DPF(TS)2.2C-51",   0.20, 4.2, 3.5, "-"),
    ("DPF(TS)2.4C-77",   0.23, 4.2, 3.5, "-"),
    ("DPF(TS)3.0C-75",   0.39, 4.5, 3.5, "直角型"),
    ("DPF(TS)3.2C-77",   0.43, 4.2, 3.5, "直角型"),
    ("DPF(S03)4.0C-10",  0.50, 4.5, 3.5, "直角型"),
    ("DPF(S03)4.5C-10",  0.70, 4.5, 3.5, "直角型"),
    ("DPF(S03)5.5C-10",  0.90, 4.5, 3.5, "直角型"),
    ("DPF(S03)6.0C-10",  1.10, 4.5, 3.5, "直角型"),
    ("DPF(S03)7.0C-10",  1.22, 4.5, 3.0, "直角型"),
]
for model, kv, press, pdiff, shape in DPF_HP:
    add(model, "DPF", REFRIG_DPF_HP, DPF_HP_T, press, pdiff, kv,
        "-", 500, shape, 0, "-", CERT_DPF, "低温热泵系列")

# =====================================================================
# DBF 系列（电子膨胀阀）
#   通用：介质 -40~80℃，环境 -40~80℃，全开脉冲 500，
#         最大工作压力 49bar=4.9MPa，最大工作压差 35bar=3.5MPa，
#         认证/接管尺寸/阀体形状图片未给出 -> -
#   直线形流量曲线(H710) 与 折线形流量曲线-S曲线(H760) 各 4 个型号
# =====================================================================
REFRIG_DBF = "R22,R134a,R407C,R410A,R507,R32"
DBF_T = (-40, 80, -40, 80)

DBF_EEV = [
    # (型号, Kv, 流量曲线备注)
    ("DBF04H710", 0.5, "直线形流量曲线"),
    ("DBF05H710", 0.7, "直线形流量曲线"),
    ("DBF06H710", 0.9, "直线形流量曲线"),
    ("DBF07H710", 1.1, "直线形流量曲线"),
    ("DBF04H760", 0.5, "折线形流量曲线(S曲线)"),
    ("DBF05H760", 0.7, "折线形流量曲线(S曲线)"),
    ("DBF06H760", 0.9, "折线形流量曲线(S曲线)"),
    ("DBF07H760", 1.1, "折线形流量曲线(S曲线)"),
]
for model, kv, remark in DBF_EEV:
    add(model, "DBF", REFRIG_DBF, DBF_T, 4.9, 3.5, kv,
        "-", 500, "-", 0, "-", "-", remark)

# =====================================================================
# DBF12 系列（电子截断阀）
#   通用：介质 -25~110℃，环境 -30~70℃，全开脉冲 500，
#         最大工作压力 4.2MPa，最大工作压差 3.5MPa，
#         认证/接管尺寸/阀体形状图片未给出 -> -
# =====================================================================
REFRIG_DBF12 = "R410A,R32,R134a,R404A,R407C,R507"
DBF12_T = (-25, 110, -30, 70)

DBF12_EEV = [
    # (型号, Kv)
    ("DBF12H51", 4.2),
    ("DBF12H03", 4.2),
]
for model, kv in DBF12_EEV:
    add(model, "DBF12", REFRIG_DBF12, DBF12_T, 4.2, 3.5, kv,
        "-", 500, "-", 0, "-", "-", "电子截断阀")

# =====================================================================
# LPF 系列
#   型号（按图）：LPF03~32 含 T(CO2 专用)/H 三版，另有大口径 LPF45/52/55/62
#   通用：全开脉冲 500，认证 UL&TUV,LVD/PED；单向流通；接管尺寸图未给出 -> -
#   温度：LPF03~32/T/H 介质 -40~70℃ 环境 -40~60℃；LPF45~62 介质/环境 -40~80℃
#   压力：
#     LPF03~32    42bar / 35bar
#     LPF45~62    49bar / 35bar
#     LPF03T~24T  90bar / 50bar（CO2 专用，含 R744）
#     LPF30T~32T  90bar / 35bar（CO2 专用，含 R744）
#     LPF03H~32H  42bar / 35bar
#   注：压力单位统一用 bar（与 PEV 一致）
# =====================================================================
LPF_KV = {
    "LPF03": 0.009, "LPF05": 0.014, "LPF08": 0.025, "LPF10": 0.04,
    "LPF14": 0.08,  "LPF18": 0.12,  "LPF24": 0.20,  "LPF30": 0.27,
    "LPF32": 0.30,
    "LPF45": 0.5,   "LPF52": 0.7,   "LPF55": 0.9,   "LPF62": 1.1,
}
LPF_FAMILIES = ["03", "05", "08", "10", "14", "18", "24", "30", "32"]
LPF_LARGE_T = (-40, 80, -40, 80)

# 标准 LPF（03~32）[bar]
for f in LPF_FAMILIES:
    model = f"LPF{f}"
    add(model, "LPF", REFRIG_LPF, LPF_T, 42, 35, LPF_KV[model],
        "-", 500, "-", 0, "-", CERT_LPF)

# LPF-T（CO2 专用，03T~32T，含 R744）[bar]
for f in LPF_FAMILIES:
    model = f"LPF{f}T"
    pdiff = 50 if int(f) <= 24 else 35   # 03T~24T 压差 50bar；30T~32T 35bar
    add(model, "LPF", REFRIG_LPF_T, LPF_T, 90, pdiff, LPF_KV[f"LPF{f}"],
        "-", 500, "-", 0, "-", CERT_LPF, "CO2系统专用")

# LPF-H（03H~32H）[bar]
for f in LPF_FAMILIES:
    model = f"LPF{f}H"
    add(model, "LPF", REFRIG_LPF, LPF_T, 42, 35, LPF_KV[f"LPF{f}"],
        "-", 500, "-", 0, "-", CERT_LPF)

# 大口径 LPF45~62（介质/环境 -40~80℃，压力 49bar）[bar]
for f in ["45", "52", "55", "62"]:
    model = f"LPF{f}"
    add(model, "LPF", REFRIG_LPF, LPF_LARGE_T, 49, 35, LPF_KV[model],
        "-", 500, "-", 0, "-", CERT_LPF)

# =====================================================================
# PEV 系列（脉冲式膨胀阀）
#   通用：介质 -40~70℃（出口侧可 -60℃），环境 -40~55℃，制冷剂含 R744
#         最高工作压力 90bar，全开脉冲：无（脉冲宽度调节）-> -
#   最大工作压差（液态）按型号 35/30/25/18bar（压力单位统一用 bar）
#   接管尺寸按图（Øe 进口 × Ød 出口）
# =====================================================================
PEV = [
    # (型号, Kv, 压差bar, 进口, 出口)
    ("PEV0-1",   0.003, 35, "3/8", "1/2"),
    ("PEV0-2",   0.003, 35, "10mm", "12mm"),
    ("PEV1-1",   0.009, 35, "3/8", "1/2"),
    ("PEV1-2",   0.009, 35, "10mm", "12mm"),
    ("PEV2-1",   0.016, 35, "3/8", "1/2"),
    ("PEV2-2",   0.016, 35, "10mm", "12mm"),
    ("PEV3-1",   0.024, 35, "3/8", "1/2"),
    ("PEV3-1S",  0.024, 35, "3/8", "1/2"),
    ("PEV3-2",   0.024, 35, "10mm", "12mm"),
    ("PEV3-2S",  0.024, 35, "10mm", "12mm"),
    ("PEV3.5-1",  0.035, 30, "3/8", "1/2"),
    ("PEV3.5-1S", 0.035, 35, "3/8", "1/2"),
    ("PEV3.5-2",  0.035, 30, "10mm", "12mm"),
    ("PEV3.5-2S", 0.035, 35, "10mm", "12mm"),
    ("PEV4-1",   0.046, 30, "3/8", "1/2"),
    ("PEV4-1S",  0.046, 35, "3/8", "1/2"),
    ("PEV4-2",   0.046, 30, "10mm", "12mm"),
    ("PEV4-2S",  0.046, 35, "10mm", "12mm"),
    ("PEV5-1",   0.064, 25, "3/8", "1/2"),
    ("PEV5-1S",  0.064, 35, "3/8", "1/2"),
    ("PEV5-2",   0.064, 25, "10mm", "12mm"),
    ("PEV5-2S",  0.064, 35, "10mm", "12mm"),
    ("PEV6-1",   0.114, 18, "3/8", "1/2"),
    ("PEV6-1S",  0.114, 35, "3/8", "1/2"),
    ("PEV6-2",   0.114, 18, "10mm", "12mm"),
    ("PEV6-2S",  0.114, 35, "10mm", "12mm"),
]
for model, kv, pdiff, e, d in PEV:
    add(model, "PEV", REFRIG_PEV, PEV_T, 90, pdiff, kv,
        f"{e}×{d}", "-", "-", 0, "-", CERT_PEV, "脉冲式膨胀阀，无全开脉冲")

# ---------- 写出（先写临时文件再原子替换，避免文件被编辑器占用时报错） ----------
import os
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_FILE = OUT_DIR / ".eev_tmp.csv"
with open(TMP_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(HEADER)
    writer.writerows(rows)
try:
    os.replace(TMP_FILE, OUT_FILE)
except PermissionError:
    # 目标文件被占用（如在编辑器中打开）时，改用覆盖写
    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)
    if TMP_FILE.exists():
        TMP_FILE.unlink()

# 简单校验：型号唯一性
models = [r[0] for r in rows]
assert len(models) == len(set(models)), "存在重复型号！"

from collections import Counter
counts = Counter(r[1] for r in rows)
print(f"已生成 {OUT_FILE}，共 {len(rows)} 行")
print("各系列数量:", dict(counts))
