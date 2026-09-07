# 制冷设备流量选型系统（equipment-agent）

基于 **质量流量窗口** 直接选型的制冷部件选型工具：输入运行工况与需求制冷量，用
[CoolProp](http://www.coolprop.org/) 计算需求质量流量 `m_req`，再对候选设备逐个判定其
能力区间是否覆盖需求，输出达标型号排行与选型报告。

> 覆盖**电磁阀 / 电子膨胀阀 / 四通换向阀 / 热力膨胀阀**等常见制冷部件：
> - 带 `Kv` 的流量型设备 → `m = Kv·√(Δp)·√(1000·ρ)` 质量流量窗口判定；
> - **四通换向阀** → 按「换向容量表」以换向容量判定（铜 SHF 15 系 + 不锈钢 SHF-G 7 系）；
> - **热力膨胀阀** → 按「制冷量扩展表」以阀口制冷量判定（RFKH R22 扩展表）。

---

## ✨ 功能特性

- **两种输入方式**：表单填写 / 自然语言对话（DeepSeek 大模型澄清缺失工况 → 自动选型 → 生成 Markdown 报告，可导出）。
- **多类型统一判定**：流量型（Kv 窗口）与容量型（四通 / 热力膨胀阀查表）在同一排行中比较。
- **单边/双边压降边界判定**：设备只给最大压降 → 只需 `m_req ≤ m_max`；只给最小压降 → 只需 `m_req ≥ m_min`；都给 → 窗口包含。
- **候选来源**：MySQL 设备表全量 + RAG 文档库检索（chroma + bge 中文嵌入）补充文档独有型号，DB 参数回填。
- **文档导入**：可直接导入 `.docx / .txt / .md` 需求文档作为输入。
- **深色冷调 Web 界面**：Vue3 + Element Plus + Vite。

## 🏗 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python · FastAPI · CoolProp · pydantic-settings · pymysql · langchain-openai |
| 前端 | Vue 3 · Vite · Element Plus · marked + DOMPurify |
| 数据 | MySQL（设备表）· ChromaDB + BGE(bge-large-zh-v1.5)（文档库，可选） |
| 模型 | DeepSeek（对话澄清 / 选型报告） |

## 📁 目录结构

```
equipment-agent/
├── .env.example            # 环境变量模板（复制为 .env 并填入 Key）
├── app.py                  # FastAPI 后端唯一入口（端口 8010）
├── config.py               # pydantic-settings 配置加载
├── db_query.py             # MySQL 设备表查询（8 张表，自然语言 → SQL）
├── flow_selection.py       # 质量流量选型核心（需求侧/设备侧公式、判定、排序）
├── flow_chat.py            # 对话式选型编排（LLM 澄清缺失参数 + 生成报告）
├── four_way_capacity.py    # 四通换向阀「换向容量表」判定
├── tev_capacity.py         # 热力膨胀阀「制冷量扩展表」判定
├── rag_candidates.py       # RAG 文档库候选（可选，需重建向量库）
├── data/
│   ├── shf_capacity_data.py    # SHF 铜/不锈钢四通容量表数据（被 import，保留）
│   └── tev_capacity_data.py    # RFKH 制冷量扩展表数据（被 import，保留）
├── tools/                  # 数据导入工具（PDF→md / OCR / 建 CSV 等，可选）
├── tests/                  # 数据验证脚本
├── 数据库信息(开发结束后删除)/  # 建表 SQL + 待导入 CSV（自行导入 MySQL）
├── 使用与开发报告/使用方法.md  # 详细使用手册
└── qian-duan/              # 前端（Vue3，端口 5173）
```

> **说明**：仓库未包含知识库大数据（`data/markdown|raw|text|images|chunks*`）与 `chroma_db/`
> 向量库、`.env` 密钥、`.venv`、前端 `node_modules`。运行 RAG 文档库候选需按
> `tools/` 脚本自行重建；不重建则仅用数据库候选，其余功能不受影响。

## 🚀 快速开始

### 1. 环境与依赖

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt          # 精简运行集

# 前端
cd qian-duan
npm install
cd ..
```

### 2. 配置 .env

```powershell
copy .env.example .env     # 然后编辑填入 Key
```

```ini
DEEPSEEK_API_KEY=sk-xxx                    # 对话澄清/报告必填
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
MYSQL_HOST=127.0.0.1                       # 设备表必填
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=...
MYSQL_DB=equipment
```

### 3. 准备数据库

1. 在 MySQL 执行 `数据库信息(开发结束后删除)/schema_all_tables.sql` 建表；
2. 把同目录 CSV 导入对应表（列名 = 表字段名）；
3. 四通换向阀等容量型表含 `series` 字段，热力膨胀阀含 `valve_orifice_no`。

### 4. 启动（两个服务）

```powershell
# ① 后端 8010（从项目根目录启动，保证 .env 相对路径生效）
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8010

# ② 前端 5173
cd qian-duan
npm run dev
```

浏览器打开 http://127.0.0.1:5173 。

## 🎯 使用流程

顶部「流量选型」页右上角切换输入方式：

- **A. 表单填写**：设备类型、制冷剂、冷凝温度、蒸发温度、过冷度、过热度、允许压降（可空）、需求制冷量 → 开始选型。
- **B. 对话输入**：如「R410A 制冷量 20kW」。大模型会反问缺失的工况（冷凝/蒸发温度、过冷/过热度、允许压降、需求制冷量），补齐后自动选型并输出报告（可「导出 Markdown」）。

结果区展示：**需求摘要**（m_req / Δh / ρ）→ **筛选**（全部/达标/未达标/跳过）→ **达标排行**（容量型与流量型统一排序）。

## 🔌 后端接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 / API Key 是否配置 |
| POST | `/select/flow` | 表单式选型。Body：`refrigerant / cond_temp / evap_temp / subcooling / superheat / delta_pressure / required_capacity / device_type` |
| POST | `/flow/chat` | 对话式选型。Body：`message / history / params`。返回 `clarify`（反问缺参）/ `done`（需求+达标+报告）/ `error` |
| POST | `/parse-doc` | 上传 `.docx/.txt/.md` 解析为文本 |

## 📐 选型模型

**需求侧**（CoolProp，与设备无关）：

$$m_{req} = \frac{Q_{req} \times 3.6 \times 10^6}{\Delta h}, \qquad
\Delta h = h(p_{evap}, t_e + SH) - h(t_c - SC,\ \text{过冷液})$$

**设备侧**（Kv 流量型）：

$$m = K_v \cdot \sqrt{\Delta p_{bar}} \cdot \sqrt{1000 \cdot \rho_{liq}}$$

- 给出**最大压降** → 只需 $m_{req} \le m_{max}$（上限取 $\min(设备max,\ 允许压降)$）
- 给出**最小压降** → 只需 $m_{req} \ge m_{min}$
- 两者都有 → 窗口 $[m_{min}, m_{max}]$ 需包含 $m_{req}$
- **无 `Kv` 的流量型设备 → 跳过**（无法用流量公式）；容量型设备（四通 / 热力膨胀阀）走各自查表分支。

排序：达标优先；达标组内 容量型（换向/阀口容量升序）在前、流量型（**Kv 升序**，最小可行阀最紧凑）在后。

## 📚 详细文档

- 完整使用手册见 [`使用与开发报告/使用方法.md`](使用与开发报告/使用方法.md)
- 前端说明见 [`qian-duan/README.md`](qian-duan/README.md)
