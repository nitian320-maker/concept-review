# Trae 交接文档

日期：2026-06-27  
项目目录：`C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用`

## 1. 项目一句话说明

这是一个基于 `Python + pywebview + 原生 HTML/CSS/JS` 的桌面概念学习应用，目标是把抽象概念做成“可复习、可追问、可深读、可串联”的学习体验。

当前已经不处于“从 0 到 1”的阶段，核心流程已跑通，后续更适合做比赛版整理、演示打磨和提交材料清理。

## 2. 当前已经完成的主要功能

- 间隔复习主流程可用，基于现有 SM-2 逻辑进行调度。
- 深度解读页已升级为结构化内容，不再只是单篇长文。
- 深度解读页已支持：
  - 前置概念
  - 文中术语点击解释
  - 最容易混淆
  - 接下来学什么
  - 局部概念关联视图
- 深度解读页版式已经改回单列正文阅读流：
  - 前置概念在正文最前
  - 混淆概念在正文后
  - 接下来学什么在最下面
- 行业黑话自动发现第一版已接入：
  - Brave Search 搜索摘要
  - DeepSeek 提取候选术语
  - 用户勾选后入库
- 分析页已具备“星图 / 银河”方向的可视化能力。
- 概念关联数据与深度解读 payload 已有后端测试覆盖。

## 3. 这轮最关键的实现点

### 后端

- `backend.py`
  - `discover_industry_terms(...)`
  - `import_discovered_terms(...)`
  - `get_deep_dive_payload(...)`
  - `get_star_map(...)`
  - `get_galaxy_state(...)`
  - `generate_relations(...)`
  - `get_collisions(...)`

### pywebview API 暴露层

- `main.py`
  - 已暴露 `get_deep_dive_payload`
  - 已暴露行业黑话发现与导入接口
  - 已暴露星图分析相关接口

### 前端

- `frontend/app.js`
  - 深度解读页渲染与概念跳转
  - 局部关联视图
  - 星图总览与银河进入逻辑
- `frontend/index.html`
  - 深度解读页容器结构
  - 分析页与星图区结构
- `frontend/style.css`
  - 深度解读阅读流排版
  - 关联区样式
  - 星图相关样式

### 测试

- `tests/test_deep_dive_relations.py`
  - 关系标准化
  - 深度解读 payload
  - 兼容旧数据
  - API 转发层

## 4. 建议 Trae 优先查看的文件

建议按下面顺序看：

1. `main.py`
2. `backend.py`
3. `frontend/app.js`
4. `frontend/index.html`
5. `frontend/style.css`
6. `tests/test_deep_dive_relations.py`

如果只想先理解“深度解读 + 概念关联”这条主链路，优先看：

- `backend.py` 中的 `get_deep_dive_payload`
- `main.py` 中的 `Api.get_deep_dive_payload`
- `frontend/app.js` 中的：
  - `openDeepDive`
  - `renderDeepDiveArticle`
  - `showLocalGraph`

如果要看“行业黑话自动发现”，优先看：

- `backend.py` 中的 `discover_industry_terms`
- `backend.py` 中的 `import_discovered_terms`
- `main.py` 对应 API 暴露

如果要看“星图/银河分析页”，优先看：

- `backend.py` 中的 `get_star_map` / `get_galaxy_state`
- `frontend/app.js` 中的 `renderStarMap` / `enterGalaxy`

## 5. 如何启动项目

在项目目录执行：

```powershell
cd C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用
pip install -r requirements.txt
python main.py
```

当前 `requirements.txt` 很轻，只包含：

```text
pywebview>=6.0
```

## 6. 已确认通过的检查

### 后端测试

```powershell
python -m unittest tests.test_deep_dive_relations -v
```

当前结果：`13/13 OK`

### 前端 JS 语法检查

```powershell
node --check .\frontend\app.js
```

当前结果：通过

## 7. 比赛提交前必须处理的风险点

### 1. `config.json` 不能直接带真实 key 提交

这个文件里目前很可能包含真实配置。

提交前至少要确认：

- 清空 `api_key`
- 清空 `brave_search_api_key`

建议改成：

```json
{
  "api_key": "",
  "brave_search_api_key": ""
}
```

### 2. `concepts.json` 与 `data` 目录要做演示化清理

这里可能包含：

- 真实概念库
- 复习记录
- 聊天历史
- AI 生成缓存

比赛版不要直接把个人使用痕迹原样带上去。建议二选一：

- 保留一份干净的演示数据
- 或只保留最小样例数据

### 3. 部分旧中文文档存在乱码历史

仓库里个别旧文档在终端里会显示乱码。代码本身当前不受影响，但如果 Trae 要做对外材料，建议直接新建 UTF-8 文档，不要沿用那些旧乱码文档继续改。

### 4. 最近更多做了自动化验证，人工走查还不够完整

我这边确认过：

- 后端测试通过
- `app.js` 语法检查通过

但最近几轮 UI 调整后，还没有做一整轮完整人工验收。Trae 接手后建议至少手动走查一遍：

- 深度解读三段式阅读流
- 术语弹层
- 概念跳转与返回
- 行业黑话发现弹窗
- 星图分析页入口与切换

## 8. 建议 Trae 接下来先做什么

### 第一优先级：整理比赛提交版

- 清理真实 key
- 清理个人数据
- 准备演示数据
- 补一份面向评审的 `README`
- 准备功能截图或录屏脚本

### 第二优先级：做一轮人工验收

- 深度解读链路完整走查
- 行业黑话发现链路走查
- 分析页星图走查

### 第三优先级：代码收口

- 清理 `frontend/app.js` 中少量历史残留注释
- 整理部分旧文档
- 视情况继续拆分前端逻辑，但这不是比赛提交前的最高优先级

## 9. 建议比赛提交材料至少包含

- 一份面向评审的 `README.md`
- 一份项目简介
- 一份功能清单
- 一份演示脚本或录屏说明
- 一份配置说明
- 一份提交前检查清单

## 10. 给 Trae 的一句话交接结论

这个项目现在最值得做的，不是继续猛加功能，而是把已有能力整理成一个“能演示、能提交、信息干净、评审能快速看懂”的比赛版本。
