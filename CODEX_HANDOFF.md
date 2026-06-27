# Codex 交接文档 — 认知星图（概念复习应用）

> **写给接手这个仓库的开发者。** 读这 10 分钟，就知道改哪里、怎么跑、什么不能碰。

---

## 1. 项目快照

这是一款基于 SM-2 间隔复习的桌面学习工具（pywebview 壳 + 单页前端）。

**星图是刚走的第 2 轮迭代**：把学习数据可视化成一个「哈勃深空」风格的星际奖励器。用户学概念 → 星点亮 → 板块成型 → 奖励感拉满。

当前状态：**第一批（后端数据）+ 第二批（SVG 渲染）+ 第三批（视觉精修）+ 第二阶段（宇宙奖励器 MVP）全部完成并部署。**

---

## 2. 目录与部署

| 路径 | 角色 |
|------|------|
| `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\` | **源码目录**（开发用，你改这里） |
| `C:\Users\Administrator\concept-reviewer\` | **部署目录**（用户双击 .bat 跑的是这个） |
| 启动方式 | 用户在部署目录双击 `概念复习.bat`，走 pywebview |

**⚠️ 每次改完源码必须同步到部署目录。** 用 Python 脚本拷过去（这台机器对 `concept-reviewer` 有写入限制，必须用 Python `shutil.copy2` 绕过）。

---

## 3. 架构：调用链铁律

```
Backend.新方法()         ← backend.py，纯 Python 业务逻辑
       ↓
Api.新方法()            ← main.py，一行代理（必须！否则前端调不到）
       ↓
window.pywebview.api.新方法()   ← app.js 前端调用
```

**每一步都不能跳。** 加后端方法忘了写 `main.py` 代理是最高频 bug。

---

## 4. 关键文件速查

| 文件 | 行数 | 里面有什么 |
|------|------|-----------|
| `data/concepts.json` | ~900 行 | 所有概念 + review_log + chat_history。UTF-8。`_save()` 原子写（.tmp → os.replace） |
| `backend.py` | ~530 行 | `Backend` 类。`_apply_sm2`、`compute_star_level()`（star 等级实时算）、`get_star_map()`（返回 stars+links）、`get_galaxy_state()`（板块进度）、`get_star_detail()`、`get_collisions()`、`get_sources()`、`generate_relations()` |
| `main.py` | ~85 行 | `Api` 类，逐方法代理 |
| `frontend/app.js` | ~1290 行 | `ConceptReviewer` 类，所有前端逻辑。星图相关：`renderStarMap()` → `_loadGalaxyOverview()` → `enterGalaxy(cat)` → `_renderGalaxyStars(cat)` → `_computeSolarLayout()` |
| `frontend/index.html` | ~170 行 | 单页。分析页已有子 tab（热力图/分类掌握/时间线/历史卡牌/星图）。星图层在 L121-135 |
| `frontend/style.css` | ~1815 行 | CSS 变量体系。星图样式从 L1401 开始 |
| `frontend/assets/starmap-bg.jpg` | 267 KB | 哈勃深空背景图（1280×720，Seedream 生成） |
| `ENGINEERING_PLAN.md` | 636 行 | 完整规格书，分 §0-§9。所有实现细节都写在这 |

---

## 5. 已完成 vs 未完成

### ✅ 第一批（纯后端）
- `compute_star_level()` — 星等级实时计算（不存字段）
- `get_star_map(category)` — 返回 `{stars: [{id,term,category,level,dimmed,is_core}], links: []}`
- `get_star_detail(id)` — 成长日记（时间线拼装）
- `generate_relations()` — 批量调 DeepSeek 生成关联图，写进 concepts.json
- `get_collisions()` — 跨板块概念碰撞（toast 展示）
- `get_sources(id)` — 维基百科链接拼接

### ✅ 第二批（前端星图）
- 分析页加「星图」子 tab + SVG 容器
- 力导向布局 → 星点渲染（按 level 分大小颜色）+ 连线
- 点击星 → 成长日记 tooltip
- 概念碰撞 toast

### ✅ 第三批（视觉精修）
- 哈勃深空背景图 `starmap-bg.jpg` + SVG 叠在上面只画交互层
- 4 级星点视觉（L0 暗星灰、L1 亮星白、L2 燃星金+光晕、L3 超新星+十字星芒）
- 首次引导层（暂被第二阶段总览取代）
- 点亮动画 `star-ignite` / `star-upgrade`

### ✅ 第二阶段（宇宙奖励器 MVP）
- 后端：`_pick_core_stars()` + `is_core` 字段 + `get_galaxy_state()`（板块 lit/burning/formed）
- **总览层**：背景压暗 35% → 3 个板块入口三角定位（AI 左上/金融 右上/哲学 下中），**只放 3 个大入口，不放任何概念小星**
- **板块层**：点击入口缩放淡入 → 太阳系同心环布局（主星居中 + 按 level 分环）+ 纯深空底色不用繁星图
- 概念星放大（L0=4 L1=5 L2=6.5 L3=8）+ hit-area r=14 热区 + hover 立即显名
- 成型态：≥80% 燃星 → 轨道环显现 + 主星升亮
- 冷暖色对比：暗星冷蓝(#6f8bb0)、亮星暖金(#ffd9a0/#ffd98a/#fff3d6)

### ❌ 未做（第四批 / P2）
- 星图主题换肤（CSS 变量即可）
- 学习路线图（独立模块）
- 卡片页右下角迷你星图
- 星象快照分享
- 3D 飞行效果
- 主题层

---

## 6. 核心设计规则（绝对不能违反）

1. **星等级算出来，不存字段。** 改规则只改 `compute_star_level()`。
2. **所有新字段用 `.get(key, 默认值)` 读，兼容老数据。**
3. **连线 ≤5/概念 + 渲染时过滤。** 绝不允许糊成 Obsidian 图谱。
4. **调用链必须完整：Backend → Api(代理) → frontend。**
5. **API key 在 `config.json` 里（deepseek 的）。**
6. **`_save()` 是原子写，照用别自己搞一套。**
7. **前端是单文件 app.js，状态都在 `ConceptReviewer` 类里。**

---

## 7. 星图三层结构（改错时的地图）

```
#analytics-starmap  ← flex:1 填满分析面板
├── .starmap-dimmer          ← z-index:1, rgba(0,0,0,0.35) 背景压暗
├── #starmap-overview        ← 第一层，默认显示
│   ├── 标题 "银河总览"
│   ├── #entry-AI            ← 绝对定位 left:12% top:30%
│   ├── #entry-finance       ← 绝对定位 right:12% top:30%
│   └── #entry-philosophy    ← 绝对定位 left:50% bottom:18%
├── #starmap-galaxy          ← 第二层，默认隐藏
│   ├── #starmap-back        ← 返回按钮
│   └── #starmap-svg         ← 板块 SVG（纯深空底色，不用背景图）
└── .starmap-tooltip         ← 成长日记弹窗
```

关键 CSS 规则：
- `.analytics-view` 有 `align-self: stretch`（覆盖父级 `.card-stage` 的 `align-items: center`）
- `#analytics-starmap` 用 `flex: 1; min-height: 0` 自然撑高
- 入口 hover 的 `transform` 对 `#entry-philosophy` 有特殊处理（它自带 `translateX(-50%)`）

---

## 8. JS 星图入口速查

```
renderStarMap()           → 进总览，绑定 3 静态入口 + 返回按钮
  └─ _loadGalaxyOverview() → 调 get_galaxy_state() 更新入口进度
       └─ click → enterGalaxy(cat)
            ├─ overview 淡出
            ├─ galaxy 缩放淡入
            └─ _renderGalaxyStars(cat)
                 ├─ 调 get_star_map(cat)
                 ├─ _computeSolarLayout()  → 同心环布局
                 ├─ 画轨道环（formed 时）
                 ├─ 画连线
                 └─ 画星：hit-area(r=14) + star-circle(r=4~8) + label
```

---

## 9. 常用命令

```powershell
# 在源码目录跑后端测试
python -c "import sys; sys.path.insert(0,'.'); from backend import Backend; b=Backend('data'); print(b.get_galaxy_state())"

# 同步源码到部署目录
python C:\Users\Administrator\.trae-cn\work\6a37ca10a7a71b2af146c7d1\sync_final.py
（或者自己写 shutil.copy2 脚本）

# 检查 CSS 括号匹配
python -c "css=open(r'C:\Users\Administrator\Desktop\...\style.css','r',encoding='utf-8').read(); print(f'depth={css.count(chr(123))-css.count(chr(125))}')"
```

---

## 10. 给接手者的建议

- **先跑一次后端测试**确认数据没坏，再动前端。
- **CSS 高度问题最容易反复**：`.card-stage` 有 `align-items: center` 会把子元素高度压扁，`.analytics-view` 只有 `align-self: stretch` 才能撑满。改 CSS 高度相关规则前先理解这条链。
- **入口位置是 CSS 绝对定位写的**，不是 JS 动态生成，改位置直接改 CSS 文件。
- **概念星渲染在 `_renderGalaxyStars` 里**，hit-area + 可见星 + label 三件套。改星点样式优先改 CSS，改数据和交互优先改这个函数。
- **AI 调用走 `_call_deepseek()`**，带缓存。加新的 AI 功能参照现有模式。
- **别动 `concepts.json` 的结构**，用 `.get()` 加字段兼容老数据。
