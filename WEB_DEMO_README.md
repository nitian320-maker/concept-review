# 概念复习 — TRAE AI 创造力大赛 Web Demo

## 作品简介

概念复习是一款沉浸式知识管理工具，帮助学习者通过**间隔重复**（Spaced Repetition）和**知识图谱**（Star Map）高效复习、巩固概念。原为桌面应用（pywebview），本版本为参赛改造的**网页版 Demo**。

**适用赛道：** 学习工作（通用赛道）+ AI 应用

## 核心功能

| 功能 | 说明 |
|------|------|
| 间隔复习 | 基于 SM-2 算法安排复习计划，智能调度 |
| 星图 | 知识图谱可视化，展示概念间的关联网络 |
| 深度学习 | 对选定概念生成详细文章，支持追问 |
| 探索发现 | 随机抽取概念，发现知识盲区 |
| 统计分析 | 复习情况、分类统计、每日动态 |
| 知识碰撞 | 关联概念横向对比，加深理解 |

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动网页服务
python web_app.py

# 3. 打开浏览器访问
# http://localhost:8765
```

**首次启动无需配置任何 API Key**，Demo 模式下自动加载 15 个 AI/深度学习概念的演示数据。

## 文件结构

```
概念复习应用/
├── web_app.py          # Flask 网页入口（WEB 版核心）
├── web_sessions/       # 匿名用户会话数据（自动生成）
├── backend.py          # 后端业务逻辑（复用现存）
├── frontend/
│   ├── index_web.html  # Web 版入口页
│   ├── index.html      # 桌面版入口（保留）
│   ├── api_adapter.js  # 统一 API 适配器（新增）
│   ├── app.js          # 前端应用逻辑（pywebview 替换）
│   ├── style.css       # 样式
│   └── ...             # 其他前端资源
├── data/
│   └── demo_seed.json  # 比赛演示数据（15 个概念）
├── tests/
│   ├── test_web_api.py           # Web API 自动化测试
│   └── test_deep_dive_relations.py
├── trae_web_session.log          # Trae 开发日志留痕
├── requirements.txt
└── TRAE_WEB_DEMO_IMPLEMENTATION_PLAN_2026-06-27.md
```

## 技术架构

```
用户浏览器 (index_web.html)
    ↕ fetch API
Flask REST API (web_app.py)
    ↕ 匿名会话隔离
Backend 业务逻辑 (backend.py)
    ↕ JSON 文件存储
data/ (session 级隔离)
```

- **无数据库依赖**，直接使用 JSON 文件存储，零配置启动
- **匿名会话隔离**，每位用户自动分配独立数据目录
- **桌面+网页双模式**，api_adapter.js 自动检测运行环境

## 技术亮点

1. **最小改动**：保留全部后端逻辑和前端 UI，仅替换 pywebview 调用层
2. **无 API Key 即可体验**：Demo 模式预置数据，不依赖大模型也能完整使用
3. **增量迁移**：桌面版和网页版共用 95% 代码，双向兼容
4. **全程 Trae 开发**：所有代码由 Trae IDE 生成、调试、迭代

## 大赛提交说明

- **报名帖**：在 TRAE 官方社区大赛报名专区发布，标签选择「学习工作」
- **演示数据**：`data/demo_seed.json` 包含 15 个 AI/深度学习概念
- **运行链接**：启动后 http://localhost:8765 即可体验
- **项目展示**：更多信息见大赛社区帖子

## 许可证

本项目仅为 TRAE AI 创造力大赛参赛作品。