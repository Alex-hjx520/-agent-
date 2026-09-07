# -*- coding: utf-8 -*-
"""
根据三花样本《三花商用出品-流体控制部件》EBV 系列「冷媒二通/三通电动球阀」章节
（样本内页 三花-35~40），生成导入数据库用的 CSV。

目标表结构 electric_ball_valve：
  id(自增), model, series, refrigerant_compatibility,
  medium_temp_min/max, ambient_temp_min/max, max_working_pressure,
  cv_value, max_op_pressure_diff_h_l, max_op_pressure_diff_l_h, pipe_size,
  body_material, application_type, full_or_reduced_bore, has_charging_connector,
  certification, electrical_params(JSON), remark

说明：
- 二通技术表每行含 介质 -40/+120℃、环境 -30/+55℃；三通技术表无环境列，用通用规格 -30/+60℃
- 动作压差：二通表分 H-L / L-H 两列；三通表只有单一动作压差（填 H-L，L-H 用 "-"）
- 二通 EBV09 某些型号 L-H 为 "/"（不适用，填 "-"）
- 全通径：二通通用规格“全通径阀芯球”；三通“全不锈钢阀体”（body_material=不锈钢）
- 缺失字段用 "-"；has_charging_connector 默认 0；输出 utf-8-sig
"""
import csv
import json
from pathlib import Path

OUT_DIR = Path("数据库信息(开发结束后删除)")
OUT_FILE = OUT_DIR / "electric_ball_valve.csv"

HEADER = [
    "model", "series", "refrigerant_compatibility",
    "medium_temp_min", "medium_temp_max", "ambient_temp_min", "ambient_temp_max",
    "max_working_pressure", "cv_value",
    "max_op_pressure_diff_h_l", "max_op_pressure_diff_l_h", "pipe_size",
    "body_material", "application_type", "full_or_reduced_bore",
    "has_charging_connector", "certification", "electrical_params", "remark",
]

MWP = 4.3  # 最高工作压力 MPa（全部型号）

# ================= 二通 EBV =================
REFRIG_2W = "HCFC,HFC（R134a,R404A,R407C,R410A,R32,R454B 等）"
T_MED_2W = (-40, 120)
T_AMB_2W = (-30, 55)  # 技术参数表每行环境温度

# 电气参数（二通通用，全开脉冲按型号分档）
def elec_2w(pulses):
    return {
        "驱动方式": "2-2相励磁，单极/双极驱动可选",
        "励磁速度": "200pps（外置线圈）/100pps（EBV09内置电机）",
        "全开脉冲": pulses,
        "结束励磁模式保持": "0.1-1.0s",
        "线圈绝缘等级": "E",
        "防护等级": "IP67",
        "线圈型号": ("PQ-M10012-001059(单极,XHP-5,引线700) / PQ-M10012-001016(单极,XHP-5,引线1500)"
                      " / PQ-M10012-001002(单极,XHP-5,引线2000,适用EBV07/EBV09) / PQ-M35012-001003(双极,引线6000)"),
    }

# (model, pipe, h_l, l_h, cv, 适用无油?, 全开脉冲)
DBF_2W = [
    ("EBV03H001",  "3/8",   3,   3,   4,  False, "2800步"),
    ("EBV03H002",  "1/2",   3,   3,   6,  False, "2800步"),
    ("EBV05H050",  "5/8",   3,   3,   10, True,  "4000步"),
    ("EBV05H051",  "3/4",   3,   3,   10, True,  "4000步"),
    ("EBV07H-002", "7/8",   1.5, 0.5, 20, False, "2800步"),
    ("EBV07H-003", "1-1/8", 1.5, 0.5, 20, False, "2800步"),
    ("EBV07H-006", "7/8",   3,   1.5, 20, False, "2800步"),
    ("EBV09H008",  "1-1/8", 1.0, "-", 34, True,  "4000步"),
    ("EBV09H009",  "2-1/8", 1.0, "-", 34, True,  "4000步"),
    ("EBV09H010",  "1-5/8", 1.0, "-", 34, True,  "4000步"),
    ("EBV09H-001", "1-1/8", 3,   1,   34, False, "4000步"),
]
NOTE_2W = ("双向通断+流量调节；缓慢开启/关闭避免液锤与冲击噪音；节能（仅动作过程耗能）；"
           "全通径阀芯球流量大压损小；低内漏，全闭可当截断阀；可替代压力调节阀/电子膨胀阀/电磁阀；"
           "R32系统可用作安全阀（泄漏即截断）；安装：线圈朝上、阀体中轴线垂直偏差±15°；"
           "来源：《三花商用出品-流体控制部件》EBV系列冷媒二通电动球阀")

# ================= 三通 EBV =================
REFRIG_3W = "HFC（R134a,R404A,R407C,R410A,R32,R454B 等）"
T_AMB_3W = (-30, 60)  # 三通通用规格
ELEC_3W = {
    "驱动电压": "DC12V",
    "电机电阻": "52Ω/46Ω",
    "全开脉冲": "3800步/4400步",
    "驱动方式": "2-2相励磁，单极/双极驱动",
    "励磁速度": "100pps",
    "结束励磁模式保持": "0.1-1.0s",
    "防护等级": "IP67",
    "线圈型号": ("PQ-M10012-001059(单极,XHP-5) / PQ-M10012-001016(单极,XHP-5) "
                  "/ PQ-M10012-001002(单极,XHP-5) / PQ-M35012-001003(双极,适用EB305)"),
}
# (model, pipe, 动作压差, cv)
DBF_3W = [
    ("EBV305H001", "5/8", 3,   4),
    ("EBV305H002", "1/2", 3.1, 4),
    ("EBV309H001", "7/8", 2.8, 10),
]
NOTE_3W = ("用于商用空调热回收/恒温除湿场合，实现A、B两路出口冷媒通断与流量调节；"
           "全不锈钢阀体；精确调节流量分配、流量波动小；紧凑轻量、抗振动、动作寿命高；"
           "来源：《三花商用出品-流体控制部件》EBV系列冷媒三通电动球阀")


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEADER)

        # 二通
        for model, pipe, h_l, l_h, cv, no_oil, pulses in DBF_2W:
            app = "适用无油系统" if no_oil else "-"
            w.writerow([
                model, "EBV", REFRIG_2W,
                T_MED_2W[0], T_MED_2W[1], T_AMB_2W[0], T_AMB_2W[1],
                MWP, cv, h_l, l_h, pipe,
                "-", app, "全通径", 0, "-",
                json.dumps(elec_2w(pulses), ensure_ascii=False),
                NOTE_2W,
            ])

        # 三通
        for model, pipe, act_diff, cv in DBF_3W:
            w.writerow([
                model, "EBV", REFRIG_3W,
                T_MED_2W[0], T_MED_2W[1], T_AMB_3W[0], T_AMB_3W[1],
                MWP, cv, act_diff, "-", pipe,
                "不锈钢", "-", "-", 0, "-",
                json.dumps(ELEC_3W, ensure_ascii=False),
                NOTE_3W,
            ])
    print(f"已生成: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    build()
