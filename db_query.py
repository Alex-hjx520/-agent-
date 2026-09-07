"""数据库直查选型模块（不用大模型）
==================================
根据用户自然语言，用**规则/正则**提取选型条件，直接 SQL 查询 MySQL 数据库中的
8 张选型表（four_way_valve / electronic_expansion_valve / thermostatic_expansion_valve /
solenoid_valve / filter_drier / pressure_regulating_valve / check_valve / ball_valve），
返回符合要求的设备型号。

与 RAG 模式的区别：
    - RAG 模式（用大模型）   ：语义理解 + 知识库 + DeepSeek 生成
    - 数据库模式（本模块）   ：关键词/正则提取条件 → 精确 SQL 查询，无大模型参与

用法：
    from db_query import parse_query, query_database

    parsed = parse_query("我需要一台电磁阀，最大工作压力4.5MPa，Kv值2.8")
    rows, device_type, sql = query_database(parsed, limit=20)
"""

import logging
import re

import pymysql

from config import settings

logger = logging.getLogger(__name__)

MAX_RESULTS = 20  # 默认最多返回条数


# =====================================================================
# 1. 设备类型 → 表名 + 系列关键词
# =====================================================================
DEVICE_TABLES: dict[str, dict] = {
    "四通换向阀": {
        "table": "four_way_valve",
        "extra_tables": ["four_way_valve_stainless"],   # SHF-G 不锈钢在独立表，需一并查
        "keywords": ["四通", "四通换向阀", "换向阀"],
        "series": ["SHF-G", "SHF", "SHF-G不锈钢"],
    },
    "电子膨胀阀": {
        "table": "electronic_expansion_valve",
        "keywords": ["电子膨胀阀", "电子膨胀", "EEV"],
        "series": ["VPF", "DPF", "LPF", "PEV", "DBF12", "DBF"],
    },
    "热力膨胀阀": {
        "table": "thermostatic_expansion_valve",
        "keywords": ["热力膨胀阀", "热力膨胀", "膨胀阀"],
        "series": ["RFKH", "RFGB", "RFGC", "RFGD"],
    },
    "电磁阀": {
        "table": "solenoid_valve",
        "keywords": ["电磁阀"],
        "series": ["MDF", "FDF-G", "FDF", "LDF", "KDF"],
    },
    "干燥过滤器": {
        "table": "filter_drier",
        "keywords": ["干燥过滤器", "过滤器", "干燥"],
        "series": ["DTG", "STG", "HTG"],
    },
    "压力调节阀": {
        "table": "pressure_regulating_valve",
        "keywords": ["压力调节阀", "调节阀", "冷凝压力", "蒸发压力", "吸气压力", "卸荷阀", "喷液阀"],
        "series": ["LTF", "CTF", "XTF", "YTF", "PYF"],
    },
    "单向阀": {
        "table": "check_valve",
        "keywords": ["单向阀", "止回阀"],
        "series": ["YCVS", "CCV", "YCV"],
    },
    "球阀": {
        "table": "ball_valve",
        "keywords": ["球阀"],
        "series": ["SBV", "GBVW", "GBV"],
    },
}

# 各表可选条件字段（用于查询）：字段名 → (比较语义)
# 比较语义：
#   "ge"  设备参数 >= 用户值（设备能力要足够）
#   "le"  设备参数 <= 用户值
#   "like"  LIKE '%值%'
#   "range_temp_min/max" 温度区间匹配
TABLE_CONDITIONS: dict[str, dict[str, str]] = {
    "four_way_valve": {
        "max_working_pressure": "ge", "max_op_pressure_diff": "ge",
        "min_op_pressure_diff": "le", "pipe_size": "like", "model": "like",
        "series": "like", "refrigerant_compatibility": "like",
        "frequency_type": "eq", "medium_temp_min": "ge", "medium_temp_max": "le",
        "ambient_temp_min": "ge", "ambient_temp_max": "le",
    },
    "electronic_expansion_valve": {
        "max_working_pressure": "ge", "max_working_pressure_diff": "ge",
        "kv_value": "ge", "pipe_size": "like", "model": "like", "series": "like",
        "refrigerant_compatibility": "like", "oil_system_compatibility": "like",
        "full_open_pulses": "ge", "body_shape": "like",
        "medium_temp_min": "ge", "medium_temp_max": "le",
        "ambient_temp_min": "ge", "ambient_temp_max": "le",
    },
    "thermostatic_expansion_valve": {
        "max_working_pressure": "ge", "model": "like", "series": "like",
        "refrigerant_compatibility": "like", "balance_type": "like",
        "inlet_pipe_size": "like", "outlet_pipe_size": "like",
        "evaporating_temp_min": "ge", "evaporating_temp_max": "le",
        "ambient_temp_min": "ge", "ambient_temp_max": "le",
    },
    "solenoid_valve": {
        "max_working_pressure": "ge", "kv_value": "ge",
        "max_op_pressure_diff_gas": "ge", "max_op_pressure_diff_ac": "ge",
        "max_op_pressure_diff_dc": "ge", "min_op_pressure_diff": "le",
        "actuation_type": "like", "valve_type": "eq", "pipe_size": "like",
        "model": "like", "series": "like", "refrigerant_compatibility": "like",
        "coil_model": "like", "medium_temp_min": "ge", "medium_temp_max": "le",
        "ambient_temp_min": "ge", "ambient_temp_max": "le",
    },
    "filter_drier": {
        "max_working_pressure": "ge", "model": "like", "series": "like",
        "refrigerant_compatibility": "like", "connection_type": "like",
        "filter_element_type": "like", "oil_compatibility": "like",
        "installation_position": "like", "medium_temp_min": "ge", "medium_temp_max": "le",
        "ambient_temp_min": "ge", "ambient_temp_max": "le",
    },
    "pressure_regulating_valve": {
        "max_working_pressure": "ge", "kv_value": "ge", "model": "like",
        "series": "like", "refrigerant_compatibility": "like",
        "pressure_adjust_range": "like", "factory_set_pressure": "ge",
        "pipe_size": "like", "valve_structure": "like",
        "medium_temp_min": "ge", "medium_temp_max": "le",
        "ambient_temp_min": "ge", "ambient_temp_max": "le",
    },
    "check_valve": {
        "max_working_pressure": "ge", "kv_value": "ge",
        "min_opening_pressure_diff_gas": "le", "pipe_size": "like",
        "body_type": "like", "installation_orientation": "like",
        "model": "like", "series": "like", "refrigerant_compatibility": "like",
        "medium_temp_min": "ge", "medium_temp_max": "le",
    },
    "ball_valve": {
        "max_working_pressure": "ge", "kv_value": "ge", "pipe_size": "like",
        "model": "like", "series": "like", "refrigerant_compatibility": "like",
        "full_or_reduced_bore": "like", "body_material": "like",
        "applicable_medium": "like", "medium_temp_min": "ge", "medium_temp_max": "le",
        "ambient_temp_min": "ge", "ambient_temp_max": "le",
    },
}

# 条件放宽优先级：数值越大越先被放宽/去掉（降级查询用）。未列出的默认 50。
# 语义：全开脉冲/冷媒/材质等“次要”条件最先放宽；Kv/压差次之；
#       最大工作压力较硬；系列/型号最硬（尽量保留）。
RELAX_PRIORITY: dict[str, int] = {
    "full_open_pulses": 100,
    "refrigerant_compatibility": 95,
    "oil_system_compatibility": 90,
    "body_material": 85,
    "full_or_reduced_bore": 80,
    "body_shape": 78,
    "frequency_type": 76,
    "pipe_size": 72,
    "actuation_type": 70,
    "valve_type": 68,
    "installation_orientation": 65,
    "connection_type": 64,
    "filter_element_type": 62,
    "installation_position": 60,
    "medium_temp_min": 55, "medium_temp_max": 55,
    "ambient_temp_min": 52, "ambient_temp_max": 52,
    "evaporating_temp_min": 55, "evaporating_temp_max": 55,
    "min_op_pressure_diff": 45,
    "min_opening_pressure_diff_gas": 45,
    "kv_value": 40,
    "max_op_pressure_diff": 35, "max_working_pressure_diff": 35,
    "max_op_pressure_diff_gas": 35, "max_op_pressure_diff_ac": 35,
    "max_op_pressure_diff_dc": 35,
    "max_working_pressure": 25,
    "series": 10,
    "model": 5,
}
DEFAULT_RELAX = 50


# 结果展示的列（每张表显示哪些字段）
TABLE_SHOW_COLS: dict[str, list[str]] = {
    "four_way_valve": ["model", "series", "max_working_pressure", "max_op_pressure_diff",
                       "pipe_size", "frequency_type", "medium_temp_min", "medium_temp_max"],
    "electronic_expansion_valve": ["model", "series", "max_working_pressure",
                                   "max_working_pressure_diff", "kv_value", "pipe_size",
                                   "full_open_pulses", "oil_system_compatibility"],
    "thermostatic_expansion_valve": ["model", "series", "max_working_pressure",
                                     "balance_type", "inlet_pipe_size", "outlet_pipe_size",
                                     "evaporating_temp_min", "evaporating_temp_max"],
    "solenoid_valve": ["model", "series", "max_working_pressure", "kv_value",
                       "max_op_pressure_diff_gas", "actuation_type", "valve_type", "pipe_size"],
    "filter_drier": ["model", "series", "max_working_pressure", "connection_type",
                     "filter_element_type", "nominal_volume", "installation_position"],
    "pressure_regulating_valve": ["model", "series", "max_working_pressure", "kv_value",
                                  "pressure_adjust_range", "factory_set_pressure", "pipe_size"],
    "check_valve": ["model", "series", "max_working_pressure", "kv_value",
                    "min_opening_pressure_diff_gas", "pipe_size", "body_type"],
    "ball_valve": ["model", "series", "max_working_pressure", "kv_value", "pipe_size",
                   "full_or_reduced_bore", "body_material", "applicable_medium"],
}

# 数据库列 → 中文显示名（用于回复）
COL_LABELS = {
    "model": "型号", "series": "系列", "max_working_pressure": "最大工作压力(MPa)",
    "max_op_pressure_diff": "最大动作压差(MPa)", "min_op_pressure_diff": "最小动作压差(MPa)",
    "max_working_pressure_diff": "最大工作压差(MPa)", "kv_value": "Kv值",
    "pipe_size": "接管尺寸", "frequency_type": "定频/变频", "full_open_pulses": "全开脉冲",
    "oil_system_compatibility": "有油/无油", "balance_type": "平衡方式",
    "inlet_pipe_size": "进口接管", "outlet_pipe_size": "出口接管",
    "evaporating_temp_min": "蒸发温度下限(℃)", "evaporating_temp_max": "蒸发温度上限(℃)",
    "medium_temp_min": "介质温度下限(℃)", "medium_temp_max": "介质温度上限(℃)",
    "ambient_temp_min": "环境温度下限(℃)", "ambient_temp_max": "环境温度上限(℃)",
    "max_op_pressure_diff_gas": "最大压差气态(MPa)", "max_op_pressure_diff_ac": "最大压差AC(MPa)",
    "max_op_pressure_diff_dc": "最大压差DC(MPa)", "min_op_pressure_diff_gas": "最小开阀压差(MPa)",
    "actuation_type": "动作方式", "valve_type": "阀体类型", "coil_model": "线圈",
    "connection_type": "接口", "filter_element_type": "滤芯", "nominal_volume": "名义容积",
    "installation_position": "安装位置", "pressure_adjust_range": "压力调节范围",
    "factory_set_pressure": "出厂设定压力(MPa)", "body_type": "阀体类型",
    "min_opening_pressure_diff_gas": "最小开阀压差(MPa)", "installation_orientation": "安装方向",
    "full_or_reduced_bore": "全/缩径", "body_material": "阀体材料", "applicable_medium": "适用介质",
    "refrigerant_compatibility": "制冷剂", "certification": "认证", "remark": "备注",
}


# =====================================================================
# 2. 设备类型识别
# =====================================================================
def detect_device_type(text: str) -> str | None:
    """根据关键词识别设备类型；无明确类型时返回 None。"""
    for device, cfg in DEVICE_TABLES.items():
        # 先按系列名识别（更精确，如 "SHF 四通" 已含类型词）
        if any(kw in text for kw in cfg["keywords"]):
            return device
    # 退化：仅凭系列名（如用户只输入 "我要 KDF 电磁阀" 已含类型词；"KDF" 单独出现）
    for device, cfg in DEVICE_TABLES.items():
        for s in cfg["series"]:
            if re.search(rf"\b{s}\b", text):
                return device
    return None


# =====================================================================
# 3. 条件提取（正则解析自然语言）
# =====================================================================
_NUM = r"([\d.]+)"
_OP = r"(?:约|大概|左右|不小于|至少|≥|>=|不大于|最多|≤|<=|=|≈)?"


def _to_num(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def extract_conditions(text: str) -> dict:
    """从自然语言提取条件，返回 {列名: (操作符, 值/字符串)}。
    支持字段：型号/系列/压力/Kv/压差/温度/冷媒/接管/通径/脉冲/动作方式/阀体类型/有油无油。
    """
    cond: dict = {}

    # ---- 型号（优先精确匹配） ----
    m = re.search(r"(?:型号|model)\s*[为:：是]?\s*([A-Za-z0-9][A-Za-z0-9\-()（）./]*[A-Za-z0-9])", text, re.I)
    if m:
        cond["model"] = ("like", m.group(1).strip())

    # ---- 系列 ----
    m = re.search(r"(?:系列|series)\s*[为:：是]?\s*([A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])", text, re.I)
    if m:
        cond["series"] = ("like", m.group(1).strip())
    else:
        # 直接识别系列名（如 KDF、VPF、SHF-G）
        for device, cfg in DEVICE_TABLES.items():
            for s in cfg["series"]:
                if re.search(rf"(?<![\w-]){re.escape(s)}(?![\w-])", text):
                    cond["series"] = ("like", s)
                    break
            if "series" in cond:
                break

    # ---- 最大工作压力 ----
    m = re.search(r"(?:最大工作压力|最高工作压力|工作压力|耐压|承压|压力)\s*" + _OP + r"\s*" + _NUM, text)
    if m:
        cond["max_working_pressure"] = ("ge", _to_num(m.group(1)))

    # ---- 压差 ----
    m = re.search(r"(?:最大(?:工作|动作)?压差|压差)\s*" + _OP + r"\s*" + _NUM, text)
    if m:
        cond["_pressure_diff"] = ("ge", _to_num(m.group(1)))

    # ---- Kv 值 ----
    m = re.search(r"(?:Kv|kv|KV)\s*(?:值)?\s*" + _OP + r"\s*" + _NUM, text)
    if m:
        cond["kv_value"] = ("ge", _to_num(m.group(1)))

    # ---- 温度（介质温度 区间，如 -40~80 或 80） ----
    m = re.search(r"(?:介质温度|适用温度|温度)\s*[为:：]?\s*(-?[\d.]+)\s*~?\s*(-?[\d.]*)\s*℃?", text)
    if m:
        t_min = _to_num(m.group(1))
        t_max = _to_num(m.group(2))
        if t_min is not None:
            cond["medium_temp_min"] = ("ge", t_min)
        if t_max is not None:
            cond["medium_temp_max"] = ("le", t_max)
    else:
        m = re.search(r"(?:介质温度|适用温度|温度)\s*(?:不低于|≥|>=|至少)?\s*(-?[\d.]+)\s*℃?", text)
        if m:
            cond["medium_temp_min"] = ("ge", _to_num(m.group(1)))

    # ---- 冷媒（R22/R410A/CO2/R744 等，直接扫描代号出现即可） ----
    m = re.search(r"(R\d{3}[A-Za-z]*|CO2|R744|R134a|R404A|R410A|R407C|R32|R22|R290|R1234yf|R1234ze)", text, re.I)
    if m:
        cond["refrigerant_compatibility"] = ("like", m.group(1).upper())

    # ---- 接管/配管尺寸 ----
    m = re.search(r"(?:接管|配管|管径|接口|连接管)\s*(?:尺寸)?\s*[为:：]?\s*([\d./\-×A-Za-z]+)", text)
    if m:
        cond["pipe_size"] = ("like", m.group(1).strip())

    # ---- 全开脉冲 ----
    m = re.search(r"(?:全开脉冲|脉冲)\s*[为:：]?\s*" + _NUM, text)
    if m:
        cond["full_open_pulses"] = ("ge", _to_num(m.group(1)))

    # ---- 动作方式（直动/先导） ----
    if re.search(r"直动", text):
        cond["actuation_type"] = ("like", "直动")
    elif re.search(r"先导", text):
        cond["actuation_type"] = ("like", "先导")

    # ---- 阀体类型（常闭/常开） ----
    if re.search(r"常闭", text):
        cond["valve_type"] = ("eq", "常闭")
    elif re.search(r"常开", text):
        cond["valve_type"] = ("eq", "常开")

    # ---- 有油/无油（电子膨胀阀） ----
    if re.search(r"无油", text):
        cond["oil_system_compatibility"] = ("like", "无油")
    elif re.search(r"有油", text):
        cond["oil_system_compatibility"] = ("like", "有油")

    # ---- 球阀：全通径/缩径、阀体材料 ----
    if re.search(r"全通径|全通", text):
        cond["full_or_reduced_bore"] = ("like", "全通径")
    elif re.search(r"缩径", text):
        cond["full_or_reduced_bore"] = ("like", "缩径")
    for mat in ("不锈钢", "黄铜"):
        if mat in text:
            cond["body_material"] = ("like", mat)
            break

    return cond


# =====================================================================
# 4. 条件映射到具体表 + SQL 构建
# =====================================================================
def _map_pressure_diff(cond: dict, table: str) -> dict:
    """把通用"压差"条件映射到具体表的压差列。"""
    if "_pressure_diff" not in cond:
        return cond
    val = cond.pop("_pressure_diff")
    if table == "solenoid_valve":
        cond["max_op_pressure_diff_gas"] = val
    elif table == "electronic_expansion_valve":
        cond["max_working_pressure_diff"] = val
    else:
        cond["max_op_pressure_diff"] = val
    return cond


def _build_sql_for_table(table: str, conditions: dict, limit: int, conditions_map: dict) -> tuple[str, list]:
    """按指定表生成参数化 SQL。conditions_map 为该表的可选字段映射。"""
    conditions = _map_pressure_diff(dict(conditions), table)
    allowed = conditions_map

    where: list[str] = []
    params: list = []

    for col, (op, val) in conditions.items():
        if col not in allowed:
            continue  # 该表没有此列，忽略
        if op == "ge":
            where.append(f"{col} >= %s")
            params.append(val)
        elif op == "le":
            where.append(f"{col} <= %s")
            params.append(val)
        elif op == "eq":
            where.append(f"{col} = %s")
            params.append(val)
        elif op == "like":
            where.append(f"{col} LIKE %s")
            params.append(f"%{val}%")

    where_sql = " AND ".join(where) if where else "1=1"
    sql = f"SELECT * FROM {table} WHERE {where_sql} ORDER BY model LIMIT {int(limit)}"
    return sql, params


def build_sql(device_type: str, conditions: dict, limit: int = MAX_RESULTS) -> tuple[str, list]:
    """生成主表的参数化 SQL。返回 (sql, params)。"""
    table = DEVICE_TABLES[device_type]["table"]
    return _build_sql_for_table(table, conditions, limit, TABLE_CONDITIONS.get(table, {}))


# =====================================================================
# 5. 数据库连接 / 查询
# =====================================================================
def _connect() -> pymysql.connections.Connection:
    if not settings.has_mysql_config:
        raise ConnectionError(
            "MySQL 未配置或未连接：请在 .env 中填写 MYSQL_HOST/MYSQL_PORT/"
            "MYSQL_USER/MYSQL_PASSWORD/MYSQL_DB（参考 .env.example）"
        )
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_db,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def _existing_tables(conn: pymysql.connections.Connection) -> set[str]:
    """返回库中所有表名。"""
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        return {list(r.values())[0] for r in cur.fetchall()}


def _exec(conn: pymysql.connections.Connection, sql: str, params: list) -> list[dict]:
    """执行查询并返回字典行列表（pymysql fetchall 返回 tuple，统一转 list）。"""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def load_kv_index() -> dict[str, str]:
    """从数据库各含 kv_value 的表加载 {型号: kv} 映射（RAG 候选缺 kv 时回填用）。

    同时登记「精确大写」与「归一化」（去空格/括号/横线/大写）两种 key，
    便于 RAG/LLM 返回的型号写法与库内写法（如 DPF(TS)1.0C-15）互相匹配。
    失败/未配置 MySQL 时返回空 dict（调用方静默跳过回填）。
    """
    index: dict[str, str] = {}
    try:
        if not settings.has_mysql_config:
            return index
        conn = _connect()
        try:
            existing = _existing_tables(conn)
            tables: list[str] = []
            for cfg in DEVICE_TABLES.values():
                if cfg.get("table") in existing:
                    tables.append(cfg["table"])
                for t in cfg.get("extra_tables") or []:
                    if t in existing:
                        tables.append(t)
            for table in set(tables):
                try:
                    rows = _exec(
                        conn,
                        f"SELECT model, kv_value FROM `{table}` "
                        f"WHERE kv_value IS NOT NULL AND kv_value <> ''",
                        [],
                    )
                except Exception:
                    continue
                for r in rows:
                    m = str(r.get("model") or "").strip()
                    kv = r.get("kv_value")
                    if not m or kv in (None, ""):
                        continue
                    kv = str(kv).strip()
                    key = m.upper()
                    index.setdefault(key, kv)
                    index.setdefault(re.sub(r"[()（）\s-]", "", key), kv)
        finally:
            conn.close()
    except Exception as exc:
        print(f"[kv回填] 加载数据库索引失败: {exc}")
    return index


def _query_tables(conn, cfg: dict, existing: set[str], conditions: dict, limit: int) -> tuple[list[dict], str]:
    """对主表 + 附加表执行查询并去重。返回 (rows, sql)。"""
    main_table = cfg["table"]
    main_map = TABLE_CONDITIONS.get(main_table, {})
    sql, params = _build_sql_for_table(main_table, conditions, limit, main_map)
    rows = _exec(conn, sql, params)
    for t in cfg.get("extra_tables", []):
        if t in existing:
            sql_t, p_t = _build_sql_for_table(t, conditions, limit, main_map)
            rows += _exec(conn, sql_t, p_t)
    # 按 model 去重
    seen: set[str] = set()
    uniq: list[dict] = []
    for r in rows:
        m = r.get("model")
        if m in seen:
            continue
        seen.add(m)
        uniq.append(r)
    return uniq, sql


def query_database(device_type: str, conditions: dict, limit: int = MAX_RESULTS) -> tuple[list[dict], str, dict]:
    """执行数据库查询，返回 (rows, sql, meta)。

    降级策略：先用全部条件精确查询；若无匹配，按 RELAX_PRIORITY 从“次要”到“主要”
    逐步放宽（去掉）条件，找到第一个有结果的条件组合，并在 meta 中说明哪些条件未判断。

    meta = {"relaxed": bool, "dropped": [被放宽/未判断的列...], "kept": [生效的列...]}

    异常：未配置连接 → ConnectionError；连不上/查询失败 → ConnectionError；
          表不存在/字段不一致 → ValueError。
    """
    cfg = DEVICE_TABLES[device_type]
    main_table = cfg["table"]
    logger.info("[DB] %s | 主表 %s | 原始条件=%s", device_type, main_table, conditions)

    try:
        conn = _connect()
    except pymysql.MySQLError as exc:
        raise ConnectionError(f"无法连接 MySQL：{exc}") from exc
    try:
        existing = _existing_tables(conn)
        if main_table not in existing:
            raise ValueError(
                f"数据表 {main_table} 不存在。请先在数据库中执行「数据库信息(开发结束后删除)/schema_all_tables.sql」"
                f"建表并导入 CSV 数据。"
            )

        # 1) 全部条件精确查询
        rows, sql = _query_tables(conn, cfg, existing, conditions, limit)
        if rows:
            logger.info("[DB] 精确匹配 %d 条", len(rows))
            return rows, sql, {"relaxed": False, "dropped": [], "kept": list(conditions)}

        # 2) 逐步放宽：按优先级（数值大=次要）依次去掉条件，直到有结果
        dropped: list[str] = []
        remaining: dict = dict(conditions)
        ordered = sorted(remaining.keys(), key=lambda c: RELAX_PRIORITY.get(c, DEFAULT_RELAX), reverse=True)
        last_rows, last_sql = rows, sql
        for col in ordered:
            remaining.pop(col, None)
            dropped.append(col)
            if not remaining:
                last_rows, last_sql = _query_tables(conn, cfg, existing, {}, limit)  # 只剩类型
                break
            last_rows, last_sql = _query_tables(conn, cfg, existing, remaining, limit)
            if last_rows:
                break

        logger.info("[DB] 降级匹配 %d 条，未判断条件=%s", len(last_rows), dropped)
        return last_rows, last_sql, {"relaxed": True, "dropped": dropped, "kept": list(remaining)}
    except pymysql.ProgrammingError as exc:
        raise ValueError(
            f"数据库查询失败（数据表可能不存在或字段不一致）：{exc}。"
            f"请检查 schema_all_tables.sql 建表是否完整、CSV 列名是否与表字段一致。"
        ) from exc
    except pymysql.MySQLError as exc:
        raise ConnectionError(f"数据库查询失败：{exc}") from exc
    finally:
        conn.close()


def parse_query(text: str) -> dict:
    """解析自然语言 → {device_type, conditions}。"""
    device_type = detect_device_type(text)
    conditions = extract_conditions(text)
    return {"device_type": device_type, "conditions": conditions}


# =====================================================================
# 6. 结果格式化
# =====================================================================
def _describe_columns(cols: list[str], table: str) -> str:
    """把列名列表转成中文描述（供降级说明）。"""
    names = []
    for c in cols:
        # 通用压差映射回中文标签
        names.append(COL_LABELS.get(c, c))
    return "、".join(names) if names else "—"


def format_db_reply(device_type: str, rows: list[dict], conditions: dict, meta: dict | None = None) -> str:
    """把数据库查询结果格式化为可读文本。

    meta: query_database 返回的 {"relaxed", "dropped", "kept"}；
          降级时（relaxed=True）会说明哪些条件未判断、当前为最匹配型号。
    """
    meta = meta or {"relaxed": False, "dropped": [], "kept": []}
    table = DEVICE_TABLES[device_type]["table"]
    show_cols = TABLE_SHOW_COLS[table]

    cond_desc = _describe_conditions(conditions, table)
    header = f"推荐设备类型：{device_type}（数据库查询）"
    if cond_desc:
        header += f"\n查询条件：{cond_desc}"

    lines = [header]

    # 降级说明
    dropped = meta.get("dropped", []) or []
    if dropped:
        lines.append(
            f"\n⚠️ 未找到完全符合全部条件的型号，已自动放宽以下条件"
            f"（未进行判断）：{_describe_columns(dropped, table)}"
        )
        lines.append("以下为当前条件下最匹配的型号：")

    if not rows:
        lines.append("\n未找到符合条件的产品（该类型数据库暂无匹配数据）。")
        return "\n".join(lines)

    lines.append(f"\n共找到 {len(rows)} 个匹配型号：\n")
    for r in rows:
        parts = []
        for col in show_cols:
            if col not in r or r[col] in (None, "", "-"):
                continue
            label = COL_LABELS.get(col, col)
            parts.append(f"{label}={r[col]}")
        model = r.get("model", "?")
        lines.append(f"- {model}" + (f" ｜ {'，'.join(parts[1:])}" if len(parts) > 1 else ""))
    return "\n".join(lines)


def _describe_conditions(conditions: dict, table: str) -> str:
    """把条件转成中文描述（供回复显示）。"""
    conditions = _map_pressure_diff(dict(conditions), table)
    desc: list[str] = []
    op_map = {"ge": "不低于", "le": "不高于", "eq": "=", "like": "包含"}
    for col, (op, val) in conditions.items():
        label = COL_LABELS.get(col, col)
        if op == "like":
            desc.append(f"{label}含“{val}”")
        else:
            desc.append(f"{label}{op_map.get(op, op)}{val}")
    return "；".join(desc) if desc else "无（返回全部）"


# =====================================================================
# 7. 命令行测试
# =====================================================================
if __name__ == "__main__":
    import sys

    tests = sys.argv[1:] or [
        "我需要一台电磁阀，最大工作压力4.5MPa，Kv值2.8",
        "SHF 四通换向阀 最大工作压力4.2MPa 最大压差3.1",
        "电子膨胀阀 LPF 适用CO2冷媒",
        "给我一台干燥过滤器",
    ]
    for t in tests:
        parsed = parse_query(t)
        print("=" * 60)
        print("输入:", t)
        print("解析:", parsed)
        if parsed["device_type"]:
            table = DEVICE_TABLES[parsed["device_type"]]["table"]
            sql, params = build_sql(parsed["device_type"], parsed["conditions"], limit=5)
            print("SQL:", sql)
            print("params:", params)
        else:
            print("未识别设备类型")
