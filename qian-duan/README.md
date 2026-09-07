# 制冷设备流量选型系统 · 前端（Vue 3）

按质量流量窗口直接选型的单页应用。后端：项目根 `app.py`（8010）。

## 技术栈
- Vue 3（`<script setup>`）+ Vite 5 + Vue Router 4
- Element Plus（暗色冷色调，中文语言包）
- marked + DOMPurify（报告 Markdown 渲染）

## 目录结构
```
qian-duan/
├── vite.config.js      # 代理 /select /flow /parse-doc /health → 8010
└── src/
    ├── main.js         # 入口
    ├── App.vue         # 顶栏（健康标签）+ 路由出口
    ├── router/index.js # 唯一路由 /
    ├── views/FlowSelectView.vue  # 主页面：表单/对话 两种选型
    └── styles/index.css          # 全局（暗色 + markdown）
```

## 功能
- **表单模式**：8 个参数 → `POST /select/flow` → 达标排行（压降边界/允许质量流量/m_req 位置）
- **对话模式**：`POST /flow/chat`（多轮澄清 → 达标参数 → 报告，可导出 .md）
