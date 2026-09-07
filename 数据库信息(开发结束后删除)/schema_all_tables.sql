-- equipment-agent 设备选型 8 张表建表 SQL
-- 用途：数据库直查模式（不用大模型时按条件查设备型号）
-- 执行：登录 MySQL 后 source 本文件；或逐段执行
-- 数据：把 数据库信息(开发结束后删除)/ 下的 CSV 手动导入对应表

-- 1. 四通换向阀
CREATE TABLE IF NOT EXISTS four_way_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（如SHF/SHF-G）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '适用介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '适用介质温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '适用环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '适用环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最大工作压力 (MPa)',
    pipe_size VARCHAR(20) COMMENT '配管尺寸（ODF）',
    max_op_pressure_diff DECIMAL(10,2) COMMENT '最大动作压差 (MPa)',
    min_op_pressure_diff DECIMAL(10,2) COMMENT '最小动作压差 (MPa)',
    frequency_type VARCHAR(20) COMMENT '定频/变频专用标识（定频/变频/通用）',
    certification VARCHAR(200) COMMENT '认证（UL/CQC/VDE等）',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='四通换向阀固定选型参数';

-- 2. 电子膨胀阀
CREATE TABLE IF NOT EXISTS electronic_expansion_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（VPF/DPF/LPF/PEV）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '介质温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    max_working_pressure_diff DECIMAL(10,2) COMMENT '最大工作压差 (MPa)',
    kv_value DECIMAL(10,2) COMMENT 'Kv值（流量系数）',
    pipe_size VARCHAR(20) COMMENT '接管尺寸（ODF）',
    full_open_pulses INT COMMENT '全开脉冲数/步数',
    body_shape VARCHAR(30) COMMENT '阀体形状（直通/L型等）',
    has_sight_glass TINYINT(1) DEFAULT 0 COMMENT '是否有视液镜（0否/1是）',
    oil_system_compatibility VARCHAR(30) COMMENT '适用有油/无油系统',
    certification VARCHAR(200) COMMENT '认证',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电子膨胀阀固定选型参数';

-- 3. 热力膨胀阀
CREATE TABLE IF NOT EXISTS thermostatic_expansion_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（RFKH/RFGB/RFGC/RFGD）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    evaporating_temp_min DECIMAL(10,2) COMMENT '蒸发温度下限 (℃)',
    evaporating_temp_max DECIMAL(10,2) COMMENT '蒸发温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    balance_type VARCHAR(20) COMMENT '平衡方式（内平衡/外平衡）',
    inlet_pipe_size VARCHAR(20) COMMENT '进口接管尺寸',
    outlet_pipe_size VARCHAR(20) COMMENT '出口接管尺寸',
    external_balance_pipe_size VARCHAR(20) COMMENT '外平衡管尺寸',
    has_mop TINYINT(1) DEFAULT 0 COMMENT '是否有MOP功能',
    mop_setting VARCHAR(50) COMMENT 'MOP设定值（如压力值）',
    capillary_length VARCHAR(20) COMMENT '毛细管长度',
    valve_orifice_no VARCHAR(30) COMMENT '阀口编号/阀芯型号',
    bulb_charge_type VARCHAR(50) COMMENT '感温包充注类型',
    certification VARCHAR(200) COMMENT '认证',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='热力膨胀阀固定选型参数';

-- 4. 电磁阀
CREATE TABLE IF NOT EXISTS solenoid_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（MDF/FDF/LDF/KDF）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '介质温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    kv_value DECIMAL(10,2) COMMENT 'Kv值（流量系数）',
    max_op_pressure_diff_gas DECIMAL(10,2) COMMENT '最大工作压差（气态）(MPa)',
    max_op_pressure_diff_ac DECIMAL(10,2) COMMENT '最大工作压差（AC）(MPa)',
    max_op_pressure_diff_dc DECIMAL(10,2) COMMENT '最大工作压差（DC）(MPa)',
    min_op_pressure_diff DECIMAL(10,2) COMMENT '最小动作压力差 (MPa)',
    actuation_type VARCHAR(20) COMMENT '动作方式（直动式/先导式）',
    valve_type VARCHAR(20) COMMENT '阀体类型（常闭/常开）',
    pipe_size VARCHAR(20) COMMENT '接管尺寸（螺纹/焊接/ODF）',
    coil_model VARCHAR(50) COMMENT '适用线圈型号',
    certification VARCHAR(200) COMMENT '认证',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电磁阀固定选型参数';

-- 5. 干燥过滤器
CREATE TABLE IF NOT EXISTS filter_drier (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（DTG/STG/HTG）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '介质温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    connection_type VARCHAR(30) COMMENT '接口尺寸/类型（螺纹/焊接）',
    filter_element_type VARCHAR(50) COMMENT '滤芯类型（100%3A / 80%3A+20%活性铝）',
    nominal_volume VARCHAR(20) COMMENT '名义容积',
    oil_compatibility VARCHAR(50) COMMENT '冷冻油兼容性（矿物油/POE/PAG）',
    installation_position VARCHAR(30) COMMENT '安装位置（液管路/气管路）',
    certification VARCHAR(200) COMMENT '认证',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='干燥过滤器固定选型参数';

-- 6. 压力调节阀
CREATE TABLE IF NOT EXISTS pressure_regulating_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（LTF冷凝压力 / CTF蒸发压力 / XTF吸气压力 / YTF卸荷阀 / PYF喷液阀）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '介质温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    kv_value DECIMAL(10,2) COMMENT 'Kv值（仅XTF系列有）',
    pressure_adjust_range VARCHAR(50) COMMENT '压力调节范围',
    factory_set_pressure DECIMAL(10,2) COMMENT '出厂设定压力 (MPa)',
    pipe_size VARCHAR(20) COMMENT '接管尺寸（ODF）',
    water_flow_capacity VARCHAR(50) COMMENT '水流容量（LTF/CTF）',
    bore_size VARCHAR(20) COMMENT '口径（YTF）',
    opening_temperature DECIMAL(10,2) COMMENT '开阀温度（PYF）(℃)',
    valve_structure VARCHAR(30) COMMENT '阀体结构（直角/水平）',
    certification VARCHAR(200) COMMENT '认证',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='压力调节阀固定选型参数';

-- 7. 单向阀
CREATE TABLE IF NOT EXISTS check_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（YCVS活塞式 / CCV膜片式 / YCV浮子式）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '介质温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    kv_value DECIMAL(10,2) COMMENT 'Kv值',
    min_opening_pressure_diff_gas DECIMAL(10,2) COMMENT '最小开阀压差（气体）(MPa)',
    pipe_size VARCHAR(20) COMMENT '接管尺寸（ODF）',
    body_type VARCHAR(30) COMMENT '阀体类型（直通型/L型/紫铜/不锈钢）',
    installation_orientation VARCHAR(30) COMMENT '安装方向（浮子式需竖直且箭头朝上）',
    certification VARCHAR(200) COMMENT '认证',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单向阀固定选型参数';

-- 8. 球阀
CREATE TABLE IF NOT EXISTS ball_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（SBV / GBV / GBVW）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '介质温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    kv_value DECIMAL(10,2) COMMENT 'Kv值（SBV/GBV系列有）',
    pipe_size VARCHAR(20) COMMENT '配管尺寸（ODF）',
    full_or_reduced_bore VARCHAR(20) COMMENT '全通径/缩径',
    has_charging_connector TINYINT(1) DEFAULT 0 COMMENT '是否带充注接头',
    body_material VARCHAR(30) COMMENT '阀体材料（不锈钢/黄铜）',
    applicable_medium VARCHAR(50) COMMENT '适用介质（水/乙二醇）',
    certification VARCHAR(200) COMMENT '认证',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='球阀固定选型参数';

--9.电子截断阀
-- 9. 电子截断阀（如 DBF12 系列）- 电子参数合并为 JSON
CREATE TABLE IF NOT EXISTS electronic_cutoff_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（如DBF12）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '介质温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    kv_value DECIMAL(10,2) COMMENT 'Kv值（流量系数）(m³/h)',
    max_working_pressure_diff DECIMAL(10,2) COMMENT '最大工作压差 (MPa)',
    reverse_opening_pressure_diff DECIMAL(10,2) COMMENT '逆向开阀压差 (MPa)',
    body_shape VARCHAR(30) COMMENT '阀体形状',
    pipe_inlet_size VARCHAR(20) COMMENT '进口接管尺寸',
    pipe_outlet_size VARCHAR(20) COMMENT '出口接管尺寸',
    certification VARCHAR(200) COMMENT '认证',
    electrical_params JSON COMMENT '电子参数（驱动电压/脉冲数/线圈电阻/电流等）',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电子截断阀固定选型参数';

-- 10. 电动球阀（如 EBV 系列）
CREATE TABLE IF NOT EXISTS electric_ball_valve (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    model VARCHAR(50) NOT NULL COMMENT '产品型号',
    series VARCHAR(20) COMMENT '系列（如EBV）',
    refrigerant_compatibility VARCHAR(100) COMMENT '制冷剂兼容性',
    medium_temp_min DECIMAL(10,2) COMMENT '介质温度下限 (℃)',
    medium_temp_max DECIMAL(10,2) COMMENT '介质温度上限 (℃)',
    ambient_temp_min DECIMAL(10,2) COMMENT '环境温度下限 (℃)',
    ambient_temp_max DECIMAL(10,2) COMMENT '环境温度上限 (℃)',
    max_working_pressure DECIMAL(10,2) COMMENT '最高工作压力 (MPa)',
    cv_value DECIMAL(10,2) COMMENT 'Cv值（流量系数）(m³/h)',
    max_op_pressure_diff_h_l DECIMAL(10,2) COMMENT '最大动作压差 H→L (MPa)',
    max_op_pressure_diff_l_h DECIMAL(10,2) COMMENT '最大动作压差 L→H (MPa)',
    pipe_size VARCHAR(20) COMMENT '接管尺寸（ODF）(inch)',
    body_material VARCHAR(30) COMMENT '阀体材料',
    application_type VARCHAR(50) COMMENT '应用类型（适用无油系统等）',
    full_or_reduced_bore VARCHAR(20) COMMENT '全通径/缩径',
    has_charging_connector TINYINT(1) DEFAULT 0 COMMENT '是否带充注接头',
    certification VARCHAR(200) COMMENT '认证',
    electrical_params JSON COMMENT '电子参数（驱动方式/励磁速度/脉冲数/线圈参数等）',
    remark TEXT COMMENT '备注',
    UNIQUE KEY uk_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电动球阀固定选型参数';