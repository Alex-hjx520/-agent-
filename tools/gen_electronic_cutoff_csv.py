# -*- coding: utf-8 -*-
"""
根据三花样本《三花商用出品-流体控制部件》DBF12 系列「电子截断阀」章节，
生成导入数据库用的 CSV。

目标表结构 electronic_cutoff_valve：
  id(自增), model, series, refrigerant_compatibility,
  medium_temp_min/max, ambient_temp_min/max,
  max_working_pressure, kv_value, max_working_pressure_diff,
  reverse_opening_pressure_diff, body_shape, pipe_inlet_size, pipe_outlet_size,
  certification, electrical_params(JSON), remark

数据来源（PDF 三花商用出品-流体控制部件，DBF12 系列电子截断阀页）：
- 通用规格：介质温度 -25~+110℃，环境温度 -30~+70℃（通电率 50% 以下）
  全开脉冲 500，介质 HCFC/HFC（R410A/R32/R134a/R404A/R407C/R507 等）
- 技术参数：Kv 4.2 m³/h，最大工作压力 4.2MPa，最大工作压差 3.5MPa，
  逆向开阀压差 3.5MPa（DBF12H51 / DBF12H03 同系列参数）
- 电气参数（通用）：12VDC 步进、260mA/相、46±3.7Ω/相 等 → electrical_params JSON
- 外形尺寸（各型号不同）写入 remark 备注

缺失字段用 "-"；输出 utf-8-sig（Excel 可直接打开不乱码）。
"""
import csv
import json
from pathlib import Path

OUT_DIR = Path("数据库信息(开发结束后删除)")
OUT_FILE = OUT_DIR / "electronic_cutoff_valve.csv"

HEADER = [
    "model", "series", "refrigerant_compatibility",
    "medium_temp_min", "medium_temp_max", "ambient_temp_min", "ambient_temp_max",
    "max_working_pressure", "kv_value", "max_working_pressure_diff",
    "reverse_opening_pressure_diff", "body_shape", "pipe_inlet_size", "pipe_outlet_size",
    "certification", "electrical_params", "remark",
]

# 系列通用值
SERIES = "DBF12"
REFRIG = "HCFC,HFC（R410A,R32,R134a,R404A,R407C,R507 等）"
T_MED = (-25, 110)
T_AMB = (-30, 70)
MWP = 4.2        # 最大工作压力 MPa
KV = 4.2         # Kv m³/h
MWP_DIFF = 3.5   # 最大工作压差 MPa
REV_DIFF = 3.5   # 逆向开阀压差 MPa

# 电气参数（系列通用）→ JSON 列
ELECTRICAL = {
    "驱动电压": "12VDC±10%，矩形波",
    "励磁方式": "1-2相（推荐）/2-2相（可选）",
    "线圈电流": "260mA/相（20℃）",
    "线圈电阻": "46±3.7Ω/相（20℃）",
    "动作方式": "4相8拍永磁型步进电机，直动式",
    "励磁速度": "30-62pps",
    "全开脉冲": "500",
    "全开至全关最短动作时间": "13s（40pps）",
    "线圈绝缘等级": "E",
    "防护等级": "IP67",
    "线圈型号": "PQ-M08012-000001",
}

# 备注模板（通用说明）
COMMON_NOTE = ("双向流通适用于热泵等可逆系统；平衡流口设计反向开阀压差达3.5MPa防反向打开；"
               "渐进式开启降低噪音；可替代电磁阀；适用于商用空调/热泵热回收多联机控制室内机通断；"
               "安装：推荐线圈朝上、横管为进口管竖管为出口管；相对湿度95%RH以下；"
               "来源：《三花商用出品-流体控制部件》DBF12系列电子截断阀")

rows = [
    # model, remark（附加各型号外形尺寸）
    ("DBF12H51", "外形尺寸：F147/G75/H69，接管外径ØD15.88/ØN21.7；"),
    ("DBF12H03", "外形尺寸：F138/G68/H62，接管外径ØD15.95/ØN21.7/I15；"),
]


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    electrical = json.dumps(ELECTRICAL, ensure_ascii=False)
    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for model, dim_note in rows:
            writer.writerow([
                model, SERIES, REFRIG,
                T_MED[0], T_MED[1], T_AMB[0], T_AMB[1],
                MWP, KV, MWP_DIFF, REV_DIFF,
                "-", "-", "-", "-",
                electrical,
                dim_note + COMMON_NOTE,
            ])
    print(f"已生成: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    build()
