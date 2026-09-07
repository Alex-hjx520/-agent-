# tests —— equipment-agent 测试与验证脚本

本目录包含项目的测试与验证脚本。

## 脚本一览

| 脚本 | 说明 | 依赖 |
|---|---|---|
| `test_unit.py` | 纯函数单元测试（回答格式 / JSON 解析 / 文档清洗） | 无网络、无 API Key |
| `verify_chunks.py` | 验证 `data/chunks.json` 切分结果 | 需先运行 `chunk_docs.py` |
| `verify_vectorstore.py` | 验证 `chroma_db` 向量库与检索 | 需已构建向量库，会加载嵌入模型（较慢） |

## 运行方式

```cmd
:: 1) 单元测试（最快，推荐每次改动后跑）
python tests/test_unit.py
:: 或用 pytest
python -m pytest tests/ -v

:: 2) 验证切分结果
python tests/verify_chunks.py

:: 3) 验证向量库检索（会加载 bge-large-zh-v1.5 模型）
python tests/verify_vectorstore.py --query "耐高温泵" --k 5
```

## 完整回归流程

```cmd
:: 数据 → 切分 → 向量库 → 服务，每步都有验证
python ingest.py
python chunk_docs.py
python tests/verify_chunks.py
python build_vectorstore.py
python tests/verify_vectorstore.py --query "耐高温泵"
python tests/test_unit.py
```

## 说明

- 测试脚本通过 `sys.path` 引用项目根目录模块，可从任意目录运行
- 需要真实网络/API Key 的端到端选型测试未纳入（避免依赖外部服务），
  可手动运行 `python rag_engine.py` 或调用 `/chat` 接口验证
- `verify_vectorstore.py` 会触发 `select_equipment` 相同的阈值逻辑，
  提示低于阈值的文档将走联网搜索兜底
