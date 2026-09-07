# -*- coding: utf-8 -*-
"""
根据三花样本《三花商用出品-流体控制部件》中
电磁阀 MDF / FDF / FDF-G / LDF / KDF 系列数据，生成导入数据库用的 CSV。

目标表结构 solenoid_valve：
  id(自增), model, series, refrigerant_compatibility, medium_temp_min/max,
  ambient_temp_min/max, max_working_pressure, kv_value,
  max_op_pressure_diff_gas/ac/dc, min_op_pressure_diff,
  actuation_type, valve_type, pipe_size, coil_model, certification, remark

缺失数据用 "-"；压力单位统一 MPa（PDF 原始即 MPa）。
输出编码 utf-8-sig（Excel 可直接打开不乱码）。
"""
import csv
import os
from pathlib import Path

OUT_DIR = Path("数据库信息(开发结束后删除)")
OUT_FILE = OUT_DIR / "solenoid_valve.csv"

HEADER = [
    "model", "series", "refrigerant_compatibility",
    "medium_temp_min", "medium_temp_max", "ambient_temp_min", "ambient_temp_max",
    "max_working_pressure", "kv_value",
    "max_op_pressure_diff_gas", "max_op_pressure_diff_ac", "max_op_pressure_diff_dc",
    "min_op_pressure_diff", "actuation_type", "valve_type",
    "pipe_size", "coil_model", "certification", "remark",
]

rows = []


def add(model, series, refrig, temps, mwp, kv, diff_gas, diff_ac, diff_dc,
        min_diff, actuation, valve_type, pipe, coil, cert, remark=""):
    """diff_* / min_diff / mwp / kv 可为数字或 "-"；temps 为 (介质min,max,环境min,max)。"""
    rows.append([
        model, series, refrig,
        temps[0], temps[1], temps[2], temps[3],
        mwp, kv, diff_gas, diff_ac, diff_dc, min_diff,
        actuation, valve_type, pipe, coil, cert, remark,
    ])


# =====================================================================
# MDF 系列（电磁阀）
#   通用：制冷剂 R22,R134a,R404A,R410A,R507；环境 -40~55℃；认证 TUV,CQC,LVD/PED
#         常闭(A03)最大工作压差 3.1MPa，配 MQ-A03 线圈
#         常开(A02)最大工作压差 2.8MPa，配 MQ-A02 线圈
#   介质温度：2H~22H / 2L~15L 为 -40~105℃；25H~40H 为 -40~140℃
#   压力单位 MPa（PDF 原始值即 MPa）
# =====================================================================
REFRIG_MDF = "R22,R134a,R404A,R410A,R507"
MDF_T_SMALL = (-40, 105, -40, 55)   # 2H~22H, 2L~15L
MDF_T_LARGE = (-40, 140, -40, 55)   # 25H~40H
CERT_MDF = "TUV,CQC,LVD/PED"

# family -> (kv, 最大工作压力, 最大工作压差, 最小动作压差, 动作方式, 阀体类型, 线圈, 温度组)
MDF_SPEC = {
    "MDF-A03-2":      (0.16, 4.9, 3.1, 0.0,   "直动式",    "常闭", "MQ-A03", MDF_T_SMALL),
    "MDF-A03-3":      (0.23, 4.9, 3.1, 0.0,   "直动式",    "常闭", "MQ-A03", MDF_T_SMALL),
    "MDF-A03-6":      (0.8,  4.9, 3.1, 0.005, "膜片先导式", "常闭", "MQ-A03", MDF_T_SMALL),
    "MDF-A03-10":     (1.9,  4.9, 3.1, 0.005, "膜片先导式", "常闭", "MQ-A03", MDF_T_SMALL),
    "MDF-A03-15-K23": (2.3,  4.9, 3.1, 0.005, "膜片先导式", "常闭", "MQ-A03", MDF_T_SMALL),
    "MDF-A03-15-K33": (3.3,  4.9, 3.1, 0.005, "膜片先导式", "常闭", "MQ-A03", MDF_T_SMALL),
    "MDF-A03-20":     (5.0,  4.9, 3.1, 0.02,  "膜片先导式", "常闭", "MQ-A03", MDF_T_SMALL),
    "MDF-A03-22":     (6.0,  4.9, 3.1, 0.02,  "膜片先导式", "常闭", "MQ-A03", MDF_T_SMALL),
    "MDF-B03-25":     (10.3, 4.5, 3.1, 0.02,  "活塞先导式", "常闭", "-",      MDF_T_LARGE),
    "MDF-B03-32":     (15.4, 4.5, 3.1, 0.02,  "活塞先导式", "常闭", "-",      MDF_T_LARGE),
    "MDF-B03-40":     (25.0, 4.5, 3.1, 0.02,  "活塞先导式", "常闭", "-",      MDF_T_LARGE),
    "MDF-A02-6":      (0.8,  4.9, 2.8, 0.005, "膜片先导式", "常开", "MQ-A02", MDF_T_SMALL),
    "MDF-A02-10":     (1.9,  4.9, 2.8, 0.005, "膜片先导式", "常开", "MQ-A02", MDF_T_SMALL),
    "MDF-A02-15-K23": (2.3,  4.9, 2.8, 0.005, "膜片先导式", "常开", "MQ-A02", MDF_T_SMALL),
    "MDF-A02-15-K33": (3.3,  4.9, 2.8, 0.005, "膜片先导式", "常开", "MQ-A02", MDF_T_SMALL),
    "MDF-A02-20":     (5.0,  4.9, 2.8, 0.02,  "膜片先导式", "常开", "MQ-A02", MDF_T_SMALL),
    "MDF-A02-22":     (6.0,  4.9, 2.8, 0.02,  "膜片先导式", "常开", "MQ-A02", MDF_T_SMALL),
}

# (订货型号, family, 接管尺寸, 连接方式备注)
MDF_MODELS = [
    # 螺纹式 常闭
    ("MDF-A03-2L002",   "MDF-A03-2",      "1/4", "螺纹式"),
    ("MDF-A03-3L002",   "MDF-A03-3",      "1/4", "螺纹式"),
    ("MDF-A03-3L004",   "MDF-A03-3",      "3/8", "螺纹式"),
    ("MDF-A03-6L002",   "MDF-A03-6",      "3/8", "螺纹式"),
    ("MDF-A03-6L004",   "MDF-A03-6",      "1/2", "螺纹式"),
    ("MDF-A03-10L004",  "MDF-A03-10",     "1/2", "螺纹式"),
    ("MDF-A03-10L002",  "MDF-A03-10",     "5/8", "螺纹式"),
    ("MDF-A03-15L002",  "MDF-A03-15-K23", "5/8", "螺纹式"),
    ("MDF-A03-15L004",  "MDF-A03-15-K23", "7/8", "螺纹式"),
    ("MDF-A03-15L051",  "MDF-A03-15-K33", "5/8", "螺纹式"),
    ("MDF-A03-15L052",  "MDF-A03-15-K33", "7/8", "螺纹式"),
    # 螺纹式 常开
    ("MDF-A02-6L002",   "MDF-A02-6",      "3/8", "螺纹式"),
    ("MDF-A02-6L004",   "MDF-A02-6",      "1/2", "螺纹式"),
    ("MDF-A02-10L002",  "MDF-A02-10",     "5/8", "螺纹式"),
    ("MDF-A02-10L004",  "MDF-A02-10",     "1/2", "螺纹式"),
    ("MDF-A02-15L002",  "MDF-A02-15-K23", "5/8", "螺纹式"),
    ("MDF-A02-15L004",  "MDF-A02-15-K23", "7/8", "螺纹式"),
    ("MDF-A02-15L051",  "MDF-A02-15-K33", "5/8", "螺纹式"),
    ("MDF-A02-15L052",  "MDF-A02-15-K33", "7/8", "螺纹式"),
    # 焊接式 常闭
    ("MDF-A03-2H002",   "MDF-A03-2",      "1/4",   "焊接式"),
    ("MDF-A03-2H004",   "MDF-A03-2",      "6mm",   "焊接式"),
    ("MDF-A03-3H002",   "MDF-A03-3",      "1/4",   "焊接式"),
    ("MDF-A03-3H006",   "MDF-A03-3",      "6mm",   "焊接式"),
    ("MDF-A03-3H004",   "MDF-A03-3",      "3/8",   "焊接式"),
    ("MDF-A03-3H008",   "MDF-A03-3",      "10mm",  "焊接式"),
    ("MDF-A03-6H002",   "MDF-A03-6",      "3/8",   "焊接式"),
    ("MDF-A03-6H006",   "MDF-A03-6",      "10mm",  "焊接式"),
    ("MDF-A03-6H004",   "MDF-A03-6",      "1/2",   "焊接式"),
    ("MDF-A03-6H008",   "MDF-A03-6",      "12mm",  "焊接式"),
    ("MDF-A03-10H002",  "MDF-A03-10",     "1/2",   "焊接式"),
    ("MDF-A03-10H006",  "MDF-A03-10",     "12mm",  "焊接式"),
    ("MDF-A03-10H004",  "MDF-A03-10",     "5/8",   "焊接式"),
    ("MDF-A03-15H006",  "MDF-A03-15-K23", "5/8",   "焊接式"),
    ("MDF-A03-15H004",  "MDF-A03-15-K23", "7/8",   "焊接式"),
    ("MDF-A03-15H051",  "MDF-A03-15-K33", "5/8",   "焊接式"),
    ("MDF-A03-15H052",  "MDF-A03-15-K33", "7/8",   "焊接式"),
    ("MDF-A03-20H002",  "MDF-A03-20",     "7/8",   "焊接式"),
    ("MDF-A03-20H004",  "MDF-A03-20",     "1-1/8", "焊接式"),
    ("MDF-A03-20H008",  "MDF-A03-20",     "28mm",  "焊接式"),
    ("MDF-A03-22H002",  "MDF-A03-22",     "7/8",   "焊接式"),
    ("MDF-A03-22H008",  "MDF-A03-22",     "1-1/8", "焊接式"),
    ("MDF-A03-22H012",  "MDF-A03-22",     "28mm",  "焊接式"),
    ("MDF-A03-22H004",  "MDF-A03-22",     "1-3/8", "焊接式"),
    ("MDF-B03-25H003",  "MDF-B03-25",     "1-1/8", "焊接式"),
    ("MDF-B03-25H005",  "MDF-B03-25",     "28mm",  "焊接式"),
    ("MDF-B03-25H004",  "MDF-B03-25",     "1-3/8", "焊接式"),
    ("MDF-B03-32H001",  "MDF-B03-32",     "1-3/8", "焊接式"),
    ("MDF-B03-32H002",  "MDF-B03-32",     "1-5/8", "焊接式"),
    ("MDF-B03-32H003",  "MDF-B03-32",     "42mm",  "焊接式"),
    ("MDF-B03-40H002",  "MDF-B03-40",     "1-5/8", "焊接式"),
    ("MDF-B03-40H003",  "MDF-B03-40",     "42mm",  "焊接式"),
    ("MDF-B03-40H004",  "MDF-B03-40",     "2-1/8", "焊接式"),
    # 焊接式 常开
    ("MDF-A02-6H002",   "MDF-A02-6",      "3/8",   "焊接式"),
    ("MDF-A02-6H006",   "MDF-A02-6",      "10mm",  "焊接式"),
    ("MDF-A02-6H004",   "MDF-A02-6",      "1/2",   "焊接式"),
    ("MDF-A02-6H008",   "MDF-A02-6",      "12mm",  "焊接式"),
    ("MDF-A02-10H002",  "MDF-A02-10",     "1/2",   "焊接式"),
    ("MDF-A02-10H006",  "MDF-A02-10",     "12mm",  "焊接式"),
    ("MDF-A02-10H004",  "MDF-A02-10",     "5/8",   "焊接式"),
    ("MDF-A02-15H006",  "MDF-A02-15-K23", "5/8",   "焊接式"),
    ("MDF-A02-15H004",  "MDF-A02-15-K23", "7/8",   "焊接式"),
    ("MDF-A02-15H051",  "MDF-A02-15-K33", "5/8",   "焊接式"),
    ("MDF-A02-15H052",  "MDF-A02-15-K33", "7/8",   "焊接式"),
    ("MDF-A02-20H002",  "MDF-A02-20",     "7/8",   "焊接式"),
    ("MDF-A02-20H004",  "MDF-A02-20",     "1-1/8", "焊接式"),
    ("MDF-A02-20H008",  "MDF-A02-20",     "28mm",  "焊接式"),
    ("MDF-A02-22H002",  "MDF-A02-22",     "7/8",   "焊接式"),
    ("MDF-A02-22H008",  "MDF-A02-22",     "1-1/8", "焊接式"),
    ("MDF-A02-22H012",  "MDF-A02-22",     "28mm",  "焊接式"),
    ("MDF-A02-22H004",  "MDF-A02-22",     "1-3/8", "焊接式"),
]

for model, fam, pipe, conn in MDF_MODELS:
    kv, mwp, diff, min_diff, actuation, vtype, coil, temps = MDF_SPEC[fam]
    add(model, "MDF", REFRIG_MDF, temps, mwp, kv,
        diff, diff, "-", min_diff, actuation, vtype, pipe, coil, CERT_MDF, conn)

# =====================================================================
# FDF 系列（常闭电磁阀）
#   通用：制冷剂 R22,R134a,R404A,R410A；介质/环境 -30~120/-30~50℃
#         最大工作压力 4.5MPa；认证 UL&CUL,TUV,VDE,CQC,LVD/PED
#   最大动作压差（气态/AC）；FDF8A08 配 FQ-A03 线圈，其余 FQ-A05
# =====================================================================
REFRIG_FDF = "R22,R134a,R404A,R410A"
FDF_T = (-30, 120, -30, 50)
CERT_FDF = "UL&CUL,TUV,VDE,CQC,LVD/PED"

FDF_MODELS = [
    # (型号, 动作方式, Kv, 压差, 最小压差, 接管, 线圈)
    ("FDF2A94",  "直动式", 0.08, 3.4, 0.0,   "1/4",   "FQ-A05"),
    ("FDF3A08",  "先导式", 0.26, 3.4, 0.01,  "5/16",  "FQ-A05"),
    ("FDF4A10",  "先导式", 0.30, 2.8, 0.0,   "1/4",   "FQ-A05"),
    ("FDF6A58",  "先导式", 0.56, 3.4, 0.01,  "5/16",  "FQ-A05"),
    ("FDF8A08",  "先导式", 0.94, 3.0, 0.01,  "3/8",   "FQ-A03"),
    ("FDF11A14", "先导式", 2.40, 2.8, 0.02,  "1/2",   "FQ-A05"),
    ("FDF13A08", "先导式", 3.5,  2.8, 0.02,  "5/8",   "FQ-A05"),
]
for model, actuation, kv, diff, min_diff, pipe, coil in FDF_MODELS:
    add(model, "FDF", REFRIG_FDF, FDF_T, 4.5, kv,
        diff, diff, "-", min_diff, actuation, "常闭", pipe, coil, CERT_FDF)

# =====================================================================
# FDF-G 系列（不锈钢常闭电磁阀）
#   通用：制冷剂 R134a,R404A,R410A；介质/环境 -30~120/-30~50℃
#         最大工作压力 4.2MPa；认证 UL&CUL,TUV(申请中)；线圈 FQ-A05
# =====================================================================
REFRIG_FDFG = "R134a,R404A,R410A"
CERT_FDFG = "UL&CUL,TUV(申请中)"

FDFG_MODELS = [
    # (型号, 动作方式, Kv, 压差, 最小压差kPa, 接管)   -- 新增大口径型号尺寸图未给出 -> -
    ("FDF2AG01",  "直动式", 0.08, 3.4, 0,    "1/4"),
    ("FDF3AG01",  "先导式", 0.30, 3.4, 5,    "5/16"),
    ("FDF4AG200", "先导式", 0.43, 3.0, 0,    "5/16"),
    ("FDF6AG01",  "先导式", 0.56, 3.4, 5,    "5/16"),
    ("FDF8AG01",  "先导式", 0.95, 3.1, 7,    "-"),
    ("FDF11AG01", "先导式", 2.58, 3.1, 7,    "-"),
    ("FDF13AG01", "先导式", 3.45, 2.8, 7,    "-"),
]
for model, actuation, kv, diff, min_kpa, pipe in FDFG_MODELS:
    add(model, "FDF-G", REFRIG_FDFG, FDF_T, 4.5, kv,
        diff, diff, "-", min_kpa / 1000, actuation, "常闭", pipe, "FQ-A05", CERT_FDFG)

# =====================================================================
# LDF 系列（低内漏常闭电磁阀）
#   通用：制冷剂 R22,R410A,R134a,R404A；介质/环境 -30~120/-30~50℃
#         最大工作压力 4.2MPa；最大工作压差(气态/AC) 3.1MPa；线圈 FQ-A05
#   认证：样本未标注 -> -
# =====================================================================
REFRIG_LDF = "R22,R410A,R134a,R404A"
LDF_T = (-30, 120, -30, 50)
CERT_LDF = "-"

LDF_MODELS = [
    # (型号, 动作方式, Kv, 最小压差, 接管)
    ("LDF2A01", "直动式", 0.12, 0.0,   "1/4"),
    ("LDF2A02", "直动式", 0.12, 0.0,   "1/4"),
    ("LDF3A08", "先导式", 0.35, 0.005, "1/4"),
    ("LDF4A08", "先导式", 0.4,  0.005, "1/4"),
    ("LDF6A07", "先导式", 0.6,  0.0,   "5/16"),
    ("LDF6A08", "先导式", 0.8,  0.005, "5/16"),
    ("LDF8A01", "先导式", 0.9,  0.005, "3/8"),
    ("LDF8A02", "先导式", 1.1,  0.005, "3/8"),
]
for model, actuation, kv, min_diff, pipe in LDF_MODELS:
    add(model, "LDF", REFRIG_LDF, LDF_T, 4.2, kv,
        3.1, 3.1, "-", min_diff, actuation, "常闭", pipe, "FQ-A05", CERT_LDF)

# =====================================================================
# KDF 系列（电磁阀，活塞先导式，常闭）
#   通用：制冷剂 HCFC,HFC；介质/环境 -40~140/-30~55℃
#         最大工作压力 4.5MPa；认证：样本未标注 -> -
#   压差：气态/AC = 3.1MPa；DC = 2.8MPa；最小动作压差 7kPa = 0.007MPa
#   交流(H)配 FQ-A05/HQ 线圈；直流(HD)配 FQ-D13 线圈
# =====================================================================
REFRIG_KDF = "HCFC,HFC"
KDF_T = (-40, 140, -30, 55)
CERT_KDF = "-"
KDF_KV = {"KDF3": 0.26, "KDF4": 0.5, "KDF6": 0.8, "KDF9": 1.3, "KDF10": 2.0, "KDF15": 2.8}

# (交流型号, 直流型号, 接管)
KDF_MODELS = [
    ("KDF3H01",  "KDF3HD01",  "1/4"),
    ("KDF3H02",  "KDF3HD02",  "6mm"),
    ("KDF3H03",  "KDF3HD03",  "3/8"),
    ("KDF3H04",  "KDF3HD04",  "10mm"),
    ("KDF4H01",  "KDF4HD01",  "3/8"),
    ("KDF4H02",  "KDF4HD02",  "10mm"),
    ("KDF4H03",  "KDF4HD03",  "1/2"),
    ("KDF4H04",  "KDF4HD04",  "12mm"),
    ("KDF6H01",  "KDF6HD01",  "3/8"),
    ("KDF6H02",  "KDF6HD02",  "10mm"),
    ("KDF6H03",  "KDF6HD03",  "1/2"),
    ("KDF6H04",  "KDF6HD04",  "12mm"),
    ("KDF9H01",  "KDF9HD01",  "1/2"),
    ("KDF9H02",  "KDF9HD02",  "5/8"),
    ("KDF9H03",  "KDF9HD03",  "12mm"),
    ("KDF10H01", "KDF10HD01", "1/2"),
    ("KDF10H02", "KDF10HD02", "5/8"),
    ("KDF10H03", "KDF10HD03", "12mm"),
    ("KDF15H01", "KDF15HD01", "5/8"),
    ("KDF15H02", "KDF15HD02", "7/8"),
    ("KDF15H03", "KDF15HD03", "3/4"),
]
import re
for ac, dc, pipe in KDF_MODELS:
    base = re.match(r"KDF\d+", ac).group(0)   # 如 KDF3, KDF10
    kv = KDF_KV[base]
    add(ac, "KDF", REFRIG_KDF, KDF_T, 4.5, kv,
        3.1, 3.1, 2.8, 0.007, "活塞先导式", "常闭", pipe, "FQ-A05/HQ", CERT_KDF, "交流线圈")
    add(dc, "KDF", REFRIG_KDF, KDF_T, 4.5, kv,
        3.1, 3.1, 2.8, 0.007, "活塞先导式", "常闭", pipe, "FQ-D13", CERT_KDF, "直流线圈")

# ---------- 写出（先写临时文件再原子替换，避免文件被编辑器占用时报错） ----------
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_FILE = OUT_DIR / ".sv_tmp.csv"
with open(TMP_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(HEADER)
    writer.writerows(rows)
try:
    os.replace(TMP_FILE, OUT_FILE)
except PermissionError:
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
