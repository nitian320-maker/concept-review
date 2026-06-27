# 认知星图 — 工程实施计划书（交给 Trae）

> 这份是 **工程版**，配套 PM 写的产品版 `TRAE_IMPLEMENTATION_PLAN.md`。
> 产品版讲「做什么、为什么」；这份讲「代码改哪里、怎么改、按什么顺序」。
> Trae 直接照这份写代码即可，遇到与产品版冲突的地方，以本工程判断为准（已在文中标注理由）。

---

## 0. 现状速读（写代码前必看）

| 层 | 文件 | 你要知道的 |
|----|------|-----------|
| 数据 | `concepts.json` | `{"concepts":[...], "review_log":[...]}`。UTF-8 编码。每个概念字段见 §1。 |
| 后端 | `backend.py` | `Backend` 类，public 方法即业务逻辑。SM-2 算法在 `_apply_sm2`。存盘用 `_save()`（写 .tmp 再 os.replace，原子写，照用）。 |
| 桥接 | `main.py` | `Api` 类把 `Backend` 方法**逐个**代理给前端。**新增后端方法必须在这里加一行代理，否则前端调不到。** |
| 前端 | `frontend/app.js` | 单个 `ConceptReviewer` 类，所有状态和逻辑都在里面。调后端用 `await window.pywebview.api.xxx(...)`。 |
| 前端 | `frontend/index.html` | 单页。分析页已有子 tab 机制（热力图/分类掌握/时间线/历史卡牌）。 |
| 前端 | `frontend/style.css` | 用了 CSS 变量（`--text-secondary`、`--color-good` 等），新样式沿用变量体系。 |

**调用链规则（每个新功能都走这条链）**：
`Backend.新方法()` → `Api.新方法()`（一行代理）→ `app.js` 里 `window.pywebview.api.新方法()`。

---

## 1. 数据模型 —— 关键决策：星等级「算」出来，不「存」

PM 版让每个概念存 `star_level` 字段并在评分/问答后 `update_star_level()` 同步。

**工程上不要这么做。** 星等级是现有字段的纯函数，存它只会引入「字段和真实状态不同步」的 bug。直接算：

```python
def compute_star_level(card, today):
    """返回 (level, dimmed)。level: 0暗星 1亮星 2燃星 3超新星；dimmed: 是否在遗忘中。"""
    has_chat = bool(card.get("chat_history"))
    reviewed = card.get("repetitions", 0) > 0 or card.get("last_review")
    interval = card.get("interval", 0)

    if has_chat and reviewed:
        level = 3                       # 超新星：问答过 + 学过
    elif reviewed and interval >= 3:
        level = 2                       # 燃星：SM-2 间隔 ≥ 3 天
    elif reviewed:
        level = 1                       # 亮星：评分过至少一次
    else:
        level = 0                       # 暗星：还没学

    # 暗淡：到期未复习超过 3 天（只对已点亮的星生效）
    dimmed = False
    if level >= 1 and card.get("next_review"):
        overdue_days = (today - date.fromisoformat(card["next_review"])).days
        dimmed = overdue_days >= 3
    return level, dimmed
```

**好处**：零迁移、零同步、改规则只改一个函数。评分/问答后星等级自动就变了（因为底层 SM-2 字段变了），不需要任何额外调用。

### 真正需要新增的存储字段（只有两个）

给每个概念加：

```json
{
  "related_concepts": [{"id": "<concept_id>", "relation": "prerequisite|similar|extends"}],
  "sources": [{"name": "Wikipedia", "url": "https://...", "type": "wikipedia|academic|video"}]
}
```

- `related_concepts`：AI 生成的关联图，生成一次缓存。是星座连线的数据来源。
- `sources`：权威来源，可 AI 生成也可留空手填。

**成长日记不需要新字段**：第一次学习时间 = `created_at`，各次复习 = `review_log` 里按 `card_id` 过滤的记录（已有 `date` 和 `quality`），升级时间点可由 review_log 推算。日记是**读时拼装**，不存。

> ⚠️ 兼容性：老数据没有 `related_concepts`/`sources` 字段，所有读取一律用 `card.get("related_concepts", [])`，不要直接 `card[...]`。

---

## 2. 后端新增方法（backend.py）

> 每个方法写完，记得去 `main.py` 的 `Api` 类加一行同名代理。

### 2.1 `get_star_map(category="全部")` —— 星图主数据

返回所有概念的星等级 + 关联，供前端渲染。**不在这里算坐标**（坐标由前端布局算法生成，见 §4）。

```python
def get_star_map(self, category="全部"):
    today = date.today()
    pool = self.concepts if category == "全部" else [c for c in self.concepts if c["category"] == category]
    stars = []
    for c in pool:
        level, dimmed = compute_star_level(c, today)
        stars.append({
            "id": c["id"],
            "term": c["term"],
            "category": c["category"],
            "level": level,
            "dimmed": dimmed,
        })
    # 连线：只在双方都 level>=2 时显示（产品约束）；去重
    links = []
    pool_ids = {c["id"] for c in pool}
    seen = set()
    star_by_id = {s["id"]: s for s in stars}
    for c in pool:
        if star_by_id[c["id"]]["level"] < 2:
            continue
        for rel in c.get("related_concepts", []):
            tid = rel["id"]
            if tid in pool_ids and star_by_id.get(tid, {}).get("level", 0) >= 2:
                key = tuple(sorted([c["id"], tid]))
                if key not in seen:
                    seen.add(key)
                    same_cat = c["category"] == next(x["category"] for x in pool if x["id"] == tid)
                    links.append({"source": c["id"], "target": tid,
                                  "relation": rel["relation"], "cross_category": not same_cat})
    return {"stars": stars, "links": links}
```

### 2.2 `get_star_detail(concept_id)` —— 成长日记（读时拼装）

```python
def get_star_detail(self, concept_id):
    c = self._find_card(concept_id)
    if not c: return None
    today = date.today()
    level, dimmed = compute_star_level(c, today)
    # 时间线：从 created_at + review_log 拼
    events = [{"date": c["created_at"][:10], "type": "created", "label": "加入星图"}]
    for e in self.review_log:
        if e["card_id"] == concept_id:
            q = e["quality"]
            label = {1: "复习·忘了", 3: "复习·不太熟", 5: "复习·记住了"}.get(q, "复习")
            events.append({"date": e["date"], "type": "review", "label": label})
    if c.get("chat_history"):
        events.append({"date": None, "type": "chat", "label": "在自由问答里追问过"})
    # 升级提示
    next_hint = None
    if level == 1:
        next_hint = "再保持复习，间隔到 3 天就会升为燃星"
    elif level == 2:
        next_hint = "去自由问答里追问一次，就能升为超新星"
    return {
        "id": c["id"], "term": c["term"], "category": c["category"],
        "level": level, "dimmed": dimmed,
        "first_learned": c["created_at"][:10],
        "next_review": c.get("next_review"),
        "events": events, "next_hint": next_hint,
    }
```

### 2.3 `generate_relations(concept_id=None)` —— AI 生成关联图（一次性/增量）

为概念生成 `related_concepts`。这是连线的数据来源。建议**批量预生成一次**，之后新增概念时增量补。

```python
def generate_relations(self, concept_id=None):
    targets = [self._find_card(concept_id)] if concept_id else [c for c in self.concepts if not c.get("related_concepts")]
    for card in filter(None, targets):
        # 候选池：同类全部 + 其他类各取若干，避免 prompt 过长
        candidates = [{"id": c["id"], "term": c["term"], "category": c["category"]}
                      for c in self.concepts if c["id"] != card["id"]]
        prompt = (
            f"概念「{card['term']}」（{card['category']}）。下面是候选概念列表(JSON)：\n"
            f"{json.dumps(candidates, ensure_ascii=False)}\n\n"
            f"找出与它有真实关联的概念，最多 5 个。relation 取值：\n"
            f"prerequisite(前置依赖) / similar(同类相似) / extends(进阶延伸)。\n"
            f"只返回 JSON 数组，格式 [{{\"id\":\"...\",\"relation\":\"...\"}}]，不要其他文字。"
        )
        resp = self._call_deepseek([{"role": "user", "content": prompt}])
        try:
            rels = json.loads(resp[resp.index("["):resp.rindex("]")+1])
            valid_ids = {c["id"] for c in self.concepts}
            card["related_concepts"] = [r for r in rels if r.get("id") in valid_ids][:5]
        except Exception:
            card["related_concepts"] = []
    self._save()
    return True
```

> 连线上限：产品约束「最多 5 条」。这里在数据源头就限到每概念 ≤5，前端渲染时再按「当前选中星周边最近 5 条」过滤一次（§4）。双重保险，避免 Obsidian 式糊成一团。

### 2.4 `get_collisions()` —— AI 概念碰撞

```python
def get_collisions(self):
    # 取最近学过的、跨板块的两个概念
    learned = [c for c in self.concepts if c.get("repetitions", 0) > 0]
    cats = {}
    for c in learned:
        cats.setdefault(c["category"], []).append(c)
    if len(cats) < 2: return None
    # 选两个不同板块各一个最近的
    import itertools
    cat_keys = list(cats.keys())
    a = max(cats[cat_keys[0]], key=lambda c: c.get("last_review") or "")
    b = max(cats[cat_keys[1]], key=lambda c: c.get("last_review") or "")
    cache_key = "_collision_" + "_".join(sorted([a["id"], b["id"]]))
    if self.config.get(cache_key):           # 7 天缓存，存 config
        return self.config[cache_key]
    prompt = (f"概念A「{a['term']}」和概念B「{b['term']}」分属不同领域。"
              f"用 50-100 字指出它们之间一个出人意料的深层共性或可类比之处。"
              f"先给一句话标题，再给解释。")
    text = self._call_deepseek([{"role": "user", "content": prompt}])
    result = {"a": a["term"], "b": b["term"], "text": text}
    if not text.startswith("⚠️"):
        self.config[cache_key] = result; self._save_config()
    return result
```

### 2.5 `get_sources(concept_id)` / 来源生成

来源可以让 AI 在 `deep_dive` 时顺带产出，或单独生成。MVP 阶段可先做**静态映射 + 占位**：维基百科链接可由 `term` 直接拼 `https://zh.wikipedia.org/wiki/{term}`，AI 综合标注写死文案。不阻塞主流程。

### 2.6 `main.py` 代理（一次性补齐）

```python
def get_star_map(self, category="全部"): return self.backend.get_star_map(category)
def get_star_detail(self, concept_id): return self.backend.get_star_detail(concept_id)
def generate_relations(self, concept_id=None): return self.backend.generate_relations(concept_id)
def get_collisions(self): return self.backend.get_collisions()
def get_sources(self, concept_id): return self.backend.get_sources(concept_id)
```

---

## 3. 前端结构改动（index.html / app.js / style.css）

### 3.1 星图挂在哪里

分析页已有子 tab（`asubtab`，热力图/分类掌握/时间线/历史卡牌）。**星图作为第 5 个子 tab 加进去**，复用现有切换逻辑，不另起页面。

`index.html` 在 `.analytics-subtabs` 里加一个按钮，在 analytics-content 区加一个容器：

```html
<button class="asubtab" data-view="starmap">🌌 星图</button>
...
<div class="analytics-content" id="analytics-starmap" style="display:none;">
  <svg id="starmap-svg" width="100%" height="520"></svg>
  <div class="starmap-tooltip" id="starmap-tooltip" style="display:none;"></div>
</div>
```

### 3.2 渲染用 SVG，不用 Canvas

概念总数 <200，SVG 完全够用，而且：点击命中检测免费（每颗星是个 `<circle>`，直接绑 click）、发光/连线用 CSS 滤镜和 `<line>`、动画用 CSS transition。Canvas 这些都得手写，没必要。

星的视觉按 level 映射 CSS class：

| level | class | 视觉 |
|-------|-------|------|
| 0 暗星 | `.star-l0` | 灰色描边空心，半透明 |
| 1 亮星 | `.star-l1` | 实心，淡发光（`filter: drop-shadow`）|
| 2 燃星 | `.star-l2` | 更大，暖色光晕，轻微 pulse 动画 |
| 3 超新星 | `.star-l3` | 最大，射线 + 光晕，缓慢闪烁 |
| dimmed | 叠加 `.star-dim` | 在上述基础上降透明度 + 去饱和，提示该复习 |

连线 `<line>`：同板块用板块主题色（AI=蓝 `#4a9eff` / 哲学=紫 `#a06bff` / 金融=金 `#ffc24a`），跨板块用银白渐变。`cross_category` 字段决定走哪种。

### 3.3 app.js 新增（挂在 ConceptReviewer 类里，沿用现有风格）

- `renderStarMap()`：`await window.pywebview.api.get_star_map(...)` → 跑布局（§4）→ 生成 SVG。子 tab 切到 starmap 时调用。
- `showStarDetail(id)`：点击星 → `get_star_detail(id)` → 在 tooltip/小卡里渲染成长日记 + 「复习这张卡片」按钮（按钮跳回卡片页该概念）。
- `checkCollision()`：合适时机调 `get_collisions()`，结果用顶部 toast（不弹窗、3 秒消失、可点开）。toast 是新的轻量 UI，加到 `index.html` 顶部。

> 复用现成：分析子 tab 切换、modal/overlay 显示隐藏、loading-spinner 都已有，直接套用 class。

---

## 4. 星图布局算法（前端，纯计算，无需 AI）

PM 版提「AI 自动排列星星位置」——**不要用 AI 算坐标**，不稳定、慢、还费 token。用确定性布局：

1. **按板块分星域**：画布横向切成几个区（AI 区 / 哲学区 / 金融区），每颗星先落到自己板块的区域内。
2. **区域内力导向（轻量）**：跑 ~100 次迭代的简化 force-directed —— 有 `related_concepts` 关联的星互相吸引，所有星互相排斥，让关联的聚在一起、整体不重叠。或更简单：板块内按 level 分层（暗星在外圈，超新星在中心）+ 圆周散布。
3. **坐标缓存**：第一次算完，把每颗星的 `{x, y}` 存到前端 localStorage（按 concept_id）。之后打开位置稳定，不会每次跳来跳去——**位置稳定对「这是我养出来的星空」的情感很关键**。新概念才算新坐标。
4. **连线过滤**：渲染时，除了后端已限的「双方 level≥2」，再按「离当前 hover/选中星最近的 5 条」显示，其余淡化或隐藏。没选中任何星时，只显示已点亮星座（3+ 互联星）的连线。

> 这一步是星图「好不好看、乱不乱」的命门。先做到「不重叠、关联的挨着、位置稳定」，视觉精修等 PM 的生图设计稿出来再调。

---

## 5. 实施顺序（Trae 按批次走，每批可独立验收）

### 第一批 —— 纯后端，立刻能做，零视觉依赖 ✅ 先做这批
1. `compute_star_level()` 辅助函数（§1）
2. `get_star_map()` + `get_star_detail()`（§2.1 / 2.2）+ main.py 代理
3. `generate_relations()`（§2.3）；写完跑一次批量生成，把 `related_concepts` 灌进 concepts.json
4. `get_collisions()`（§2.4）+ 代理
5. 权威来源：先做维基链接拼接 + 卡片翻转面/深度解读底部的来源标注（§2.5）

**第一批验收**：在 Python 里直接调 `Backend.get_star_map()`，能返回正确的 level 和 links；调 `get_star_detail()` 能拼出时间线。不依赖任何前端。

### 第二批 —— 前端功能，基础视觉
6. 分析页加「星图」子 tab + SVG 容器（§3.1）
7. 布局算法 + 基础渲染：能看到分板块的星点、按 level 区分大小颜色、连线（§3.2/§4）
8. 点击星 → 成长日记卡片（§3.3 `showStarDetail`）
9. 概念碰撞 toast（§3.3 `checkCollision`）

**第二批验收**：打开分析→星图，看到自己的星空，学过的亮、没学的暗，点星出日记。

### 第三批 —— 依赖 PM 的生图设计稿
10. 按设计稿精修视觉：背景、星星贴图/光效、连线柔和度、星座成型提示
11. 首次引导层（半透明预览星图 + 「开始探索」）
12. 升级/点亮动画打磨

### 第四批 —— 锦上添花
13. 星图主题个性化（换肤，改 CSS 变量即可）
14. 学习路线图（独立模块，可单独排期）
15. 卡片页右下角迷你星图

---

## 6. 设计约束（务必遵守，来自产品 + 工程）

- ⚠️ 星等级**算出来不存**（§1），改规则只改 `compute_star_level`。
- ⚠️ 所有新字段读取用 `.get(key, 默认值)`，兼容老数据，**不做破坏性迁移**。
- ⚠️ 连线双重限制：数据源 ≤5/概念 + 渲染时按邻近 5 条过滤。绝不允许糊成 Obsidian。
- ⚠️ 星坐标缓存到 localStorage，位置稳定。
- ⚠️ Level 0→1 门槛极低：评分过一次即亮。
- ⚠️ 暗淡窗口 = 到期后 3 天（不是 1 天）。
- ⚠️ 概念碰撞用 toast，不打断、不强制阅读。
- ⚠️ AI 生成内容标注来源 / 「AI 生成」。
- ⚠️ AI 调用都走现有 `_call_deepseek()`，结果带缓存（关联图存概念字段、碰撞存 config，均参照现有 `deep_article` 缓存模式）。
- ⚠️ 保持现有风格：单文件前端、`Api` 逐方法代理、中文 UI、`_save()` 原子写。

---

## 7. 与产品版计划书的差异说明（给 PM 看）

| 点 | 产品版 | 工程版 | 为什么改 |
|----|--------|--------|---------|
| 星等级存储 | 存 `star_level` 字段 + `update_star_level()` 同步 | 从 SM-2 字段实时计算，不存 | 消除状态不同步的整类 bug，零迁移 |
| 成长日记数据 | 新增 `star_events` 字段记录事件 | 从 `created_at` + `review_log` 读时拼装 | 数据已存在，不重复存 |
| 星星坐标 | AI 自动排列 | 前端确定性布局 + localStorage 缓存 | AI 算坐标不稳定/慢/费 token；缓存保证位置稳定 |
| 渲染技术 | Canvas 或 SVG | 明确用 SVG | 概念数少，SVG 点击命中和动画都免费 |

功能范围、视觉方向、产品逻辑完全遵照产品版，工程版只优化了**实现方式**。

---

## 8. 第三批视觉规格（已定稿 —— 视觉基准锁定）

> 视觉基准图已确认:**哈勃深空摄影风格的「知识星图」**(扣子用 Seedance 生成的第一张)。
> 特征:近黑/深蓝黑宇宙背景、横跨画面的银河光带、尘埃裂纹与雾状星云、绝大多数是细小克制的星点、极少数亮星突出、前景一颗半透明蓝色星球。**不是赛博霓虹风。**

### 8.1 关键工程决策:背景用图，SVG 只画交互层

银河带、星云、尘埃这种真实摄影质感**不要试图用 CSS/SVG 重画**——画不出来，还会变成廉价科幻插画。正确做法分两层:

1. **背景层**:把基准图存为 `frontend/assets/starmap-bg.jpg`(goforit 会把第一张原图存进来)，作为星图画布的 `background-image`，`background-size: cover`。这层负责「真实宇宙」的高级感。
2. **交互层**:SVG 叠在背景之上，**只画概念星点 + 连线 + 选中高亮**。背景透出来当星空，SVG 的星点是「被点亮的知识」。

> SVG 只管几十个可交互节点，性能和命中检测都简单，视觉质感全靠那张摄影图兜底。这是这批最重要的一条，别去用代码画银河。

### 8.2 配色规格（从基准图提取，写进 CSS 变量）

```css
--sky-bg-deep:    #050810;   /* 最深处背景，SVG 兜底色 */
--star-white:     #ffffff;   /* 主星白 */
--star-blue:      #a8c8ff;   /* 淡蓝星 */
--star-gold:      #ffd98a;   /* 金黄亮星 */
--link-ai:        rgba(74,158,255,0.35);  /* AI 板块连线 蓝 */
--link-phil:      rgba(160,107,255,0.35); /* 哲学 紫 */
--link-fin:       rgba(255,194,74,0.35);  /* 金融 金 */
--link-cross:     rgba(220,228,240,0.30); /* 跨板块 银白 */
```

### 8.3 任务 10 — 星点视觉精修（对应 level，服从真实星空观感）

| level | 视觉 | 实现 |
|-------|------|------|
| 0 暗星 | 细小灰点，几乎融入背景 | `r=2`，fill `#3a4252`，opacity 0.5，无光效 |
| 1 亮星 | 小白点 + 极淡星芒 | `r=3`，fill 白，`drop-shadow(0 0 3px)` |
| 2 燃星 | 较亮暖白，明显光晕 + 轻 pulse | `r=4.5`，fill 金，`drop-shadow(0 0 8px)`，2.5s pulse |
| 3 超新星 | 最亮主星，十字星芒 + 大光晕 + 缓慢闪烁 | `r=6`，fill 白，星芒用交叉细线，`drop-shadow(0 0 14px)`，4s 闪烁 |
| dimmed | 上述基础上去饱和降透明 | 叠加 `filter: grayscale(0.6); opacity:0.45` |

连线:`<line>` 用 §8.2 板块色，`cross_category` 走 `--link-cross`；`stroke-width:0.8`，默认 opacity 0.25，选中星周边连线提到 0.6。

### 8.4 任务 11 — 首次引导层

- 第一次进星图，盖一层 `.starmap-intro`:**直接用基准图全幅显示**(那张点亮后的完美星空)，底部文案:
  > 「这是一片等待你点亮的星空。每学会一个概念，一颗星就会亮起。」
- 「开始探索」按钮 → 淡出引导层，显示用户**真实的**(大部分还是暗星的)星空。
- 标记 `localStorage.starmap_intro_seen = true`，之后不再显示。

### 8.5 任务 12 — 点亮/升级动画

- 评分「记住了」使一颗星首次点亮(0→1)时，该星播一次「亮起」动画(`@keyframes star-ignite`:r 从 0 弹到目标值 + 光晕扩散一次)。
- 升级(1→2、2→3)时，光晕扩一圈 + 短暂增亮。
- 动画**只在本次操作刚改变的那颗星上播一次**，不要全图重播，避免每次打开都闪。

### 8.6 第三批验收

1. 画布背景是那张真实摄影星空，不是纯色/代码画的渐变。
2. 星点叠在背景上，按 level 区分大小/颜色/光效；暗星几乎隐入背景、超新星明显突出。
3. 首次进入显示引导层 + 文案 + 「开始探索」，点击后进真实星空，刷新不再弹。
4. 评分点亮一颗星时，该星播一次亮起动画。
5. 连线柔和、按板块配色、不糊成一团(§4 邻近 5 条过滤生效)。

---

# 第二阶段：宇宙星图 MVP（奖励器版）—— 给 Trae 的执行指令

> 这是和产品经理对齐后的最终口径，**第一、二、三批已完成的星图在此基础上升级**，不是重写。
> 核心定位：**星图是「学习成果的奖励器」，不是知识结构导航图。**
> 一句话口径：**第一版按「分类→概念」两层实现，先做概念点亮 + 板块成型，不做主题层。**

## 9.0 这一版做什么 / 不做什么（先读这条，避免跑偏）

**做（6 条验收）**：
1. 进星图 tab 先看到**银河总览**（3 个可点击的板块入口：AI / 金融 / 哲学）
2. 点一个入口 → **缩放淡入**进该板块的「星系层」
3. 板块内所有概念**先以暗星轮廓存在**（太阳系式布局，全暗也能看出形状）
4. 学习后（评分）对应概念**自动点亮**（暗星→亮星）
5. 板块内 **≥80% 概念达到燃星(level≥2)** → 板块进入**成型态**
6. 用户能明显感到「这是我点亮出来的」

**不做（明确砍掉，别浪费时间）**：
- ❌ 主题层（concept/skill/主题三层）——数据里没有，不做
- ❌ 真 3D 宇宙飞行——总览到板块只做「缩放+淡入」
- ❌ 星象快照分享——P2，这版不做
- ❌ 复杂完成态特效——成型态只做 2 个主表达（见 §9.3）

## 9.1 三个已拍板的规则（直接照做，别再问）

| 规则 | 定值 | 实现位置 |
|------|------|---------|
| 板块完成阈值 | 该板块 **≥80% 概念 level≥2(燃星)** | 后端 `get_galaxy_state()` |
| 中心主星选谁 | **level 最高，平手取 interval 最大**（记得最牢的） | 后端，每板块算一个 |
| 三层导航在哪 | 全在**星图 tab 内部**切换，不新开页面 | 前端 |

---

## 9.2 后端改动（backend.py）

### 改 1：`get_star_map()` 每颗星补两个字段

现有 `get_star_map` 返回的每个 star 加上：
- `is_core`: bool —— 是否该板块的中心主星
- 已有的 `level / dimmed / category` 保留

主星判定（每个 category 算一次）：
```python
def _pick_core_stars(self, stars):
    """每个 category 选 level 最高、平手取 interval 最大的概念为主星。"""
    by_cat = {}
    for s in stars:
        by_cat.setdefault(s["category"], []).append(s)
    core_ids = set()
    for cat, group in by_cat.items():
        # 只在有点亮的星里选主星；全暗则该板块暂无主星
        lit = [s for s in group if s["level"] >= 1]
        if not lit:
            continue
        # level 高优先，平手 interval 大优先
        best = max(lit, key=lambda s: (s["level"], self._interval_of(s["id"])))
        core_ids.add(best["id"])
    return core_ids
```
（`_interval_of` 用 `_find_card(id)["interval"]`；在组装 stars 时给命中的 star 打 `is_core=True`）

### 改 2：新增 `get_galaxy_state()` —— 板块成型状态

```python
def get_galaxy_state(self):
    """返回每个板块的完成度和是否成型。供总览层 + 成型态判断用。"""
    today = date.today()
    by_cat = {}
    for c in self.concepts:
        level, _ = compute_star_level(c, today)
        s = by_cat.setdefault(c["category"], {"total": 0, "burning": 0, "lit": 0})
        s["total"] += 1
        if level >= 1: s["lit"] += 1
        if level >= 2: s["burning"] += 1
    result = []
    for cat, s in by_cat.items():
        ratio = s["burning"] / s["total"] if s["total"] else 0
        result.append({
            "category": cat,
            "total": s["total"],
            "lit": s["lit"],            # 已点亮数（总览层显示进度用）
            "burning": s["burning"],
            "progress": round(ratio, 2),
            "formed": ratio >= 0.8,     # ≥80% 燃星 = 成型态
        })
    return result
```

### main.py 代理加一行
```python
def get_galaxy_state(self): return self.backend.get_galaxy_state()
```

---

## 9.3 前端改动（index.html / app.js / style.css）

### ⭐ 颗粒度对齐定稿（最重要，先读，解决「找不到点」）

goforit 反馈：当前版本「点和星看得乱，找不到能点的」。根因：几十颗真·概念星叠在繁星背景上，真假混一起。**最终拍板的颗粒度规则如下，Trae 必须严格照做：**

1. **总览层颗粒度「粗」——只有 3 个板块入口，不放任何概念点。**
   第一眼看到的就是 3 个聚拢的发光星系区(AI/金融/哲学)，间隔拉开。不可能找不到点，因为总共就 3 个大目标。
2. **概念星只在「板块层」出现**——点进某个板块后，才显示该板块的几十颗概念星。
3. **背景图(img_1 那张深空)只当氛围底，必须压暗 35%**，绝不能和前景功能元素抢眼。功能元素(入口、概念星)一律**代码另画，浮在背景之上**。
4. **概念星要明显「跳出来」**：最小 `r=4` 起(不是 2)，亮星带光晕，hover 放大+显名，**点击热区 ≥16px**(在 circle 外套一个透明的大 hit-area circle 绑 click)。宁可少而清楚，不要多而乱。

> 一句话：背景负责「漂亮」，前景负责「这是我能点的」。总览只 3 个入口，概念星进板块才出现且必须够大够亮。

### 改 3：星图 tab 内部加「总览层」（第一层，新增）

现在星图 tab 进去直接就是 SVG 星图。改成进去先是**总览层**。在 `#analytics-starmap` 里加两个互斥的子容器：

```html
<div id="analytics-starmap" style="display:none;">
  <!-- 第一层：银河总览（默认显示，只有 3 个入口）-->
  <div id="starmap-overview">
    <div class="galaxy-entry" data-cat="AI">…</div>
    <div class="galaxy-entry" data-cat="金融">…</div>
    <div class="galaxy-entry" data-cat="哲学">…</div>
  </div>
  <!-- 第二层：板块星系（现有 SVG 星图，默认隐藏）-->
  <div id="starmap-galaxy" style="display:none;">
    <button id="starmap-back">← 返回银河</button>
    <svg id="starmap-svg"></svg>
  </div>
  <div id="starmap-tooltip" style="display:none;"></div>
</div>
```

**总览层每个入口**：用 `get_galaxy_state()` 数据渲染。**入口位置由代码固定，不依赖背景图里画死的星团位置**(图里的星团对不上我们的数据)。
- 背景铺 `starmap-bg.jpg`(img_1 那张深空)，**上面盖一层 `rgba(0,0,0,0.35)` 遮罩压暗**，让背景退成氛围底，3 个入口才跳得出来
- 3 个入口用**代码绝对定位**成稳定三角分布(如左上、右上、下中)，间隔拉开，每个入口是一个发光圆区 + 板块名 label + 进度文字
- 每个入口显示：板块名 + 进度（`已点亮 lit/total`）+ 光晕，光晕亮度按 `progress` 增强
- `formed:true` 的入口：明显更亮 + 一圈完整光环（暗示「这个星系我养成了」）
- hover 入口：放大 + 提示「进入 XX 星系」；点击 → `enterGalaxy(cat)`：`#starmap-overview` 淡出、`#starmap-galaxy` 淡入 + 缩放进入（`transform: scale(0.85→1)` + `opacity 0→1`，300ms）

> 关键：总览层**只有这 3 个入口能点**，没有任何概念小星。这是解决「找不到点」的核心——目标只有 3 个，不可能找不到。

### 改 4：板块层只画该板块的星（复用现有 renderStarMap）

`renderStarMap()` 现在调 `get_star_map("全部")` 画所有星。改成 `enterGalaxy(cat)` 调 `get_star_map(cat)` 只画该板块。现有渲染逻辑（连线、tooltip、点亮动画）**复用**。返回按钮 `#starmap-back` → 回总览层。

**板块层背景**：用**纯深空底色**(`--sky-bg-deep` 深蓝黑 + 少量代码画的静态远景碎星)，**不要用 img_1 那张繁星图**——否则概念星又会淹没在背景繁星里。板块层要干净，让几十颗概念星是画面里唯一的主角。

**概念星必须「跳出来」(解决找不到点)**：
- 半径最小 `r=4` 起(L0=4, L1=5, L2=6.5, L3=8)，比之前整体放大
- 每颗星外套一个**透明大 hit-area**(`r=14` 的透明 circle，绑 click)，点击热区 ≥16px 直径，好点中
- hover：星放大 + 立即显示概念名 label(不用等)
- 亮星(L≥1)带明显光晕；暗星(L0)冷蓝微光但轮廓清晰可见

```js
// 每颗星：先放透明 hit-area，再放可见 circle
const hit = document.createElementNS(SVG_NS, "circle");
hit.setAttribute("r", 14);
hit.setAttribute("fill", "transparent");
hit.style.cursor = "pointer";
hit.addEventListener("click", () => this.showStarDetail(star.id));
g.appendChild(hit);
// 然后是可见的 circle（r 按 level，见上）
```

### 改 5：太阳系式布局（替换现有 `_computeStarLayout` 里的散布逻辑）

现在是力导向散布。板块层改成**同心轨道**，这样全暗也看得出「一个待点亮的太阳系」：
- **中心**：`is_core` 的主星放正中心（没主星时，中心留一个暗核占位）
- **轨道环**：其余星按 level 分层 —— level 高的靠内环，level 0 暗星在最外环
- 每环上的星沿圆周**均匀分布**，环半径随层级递增
- 坐标仍缓存 localStorage（key 改成 `starPos_<cat>`，每板块一套），保证位置稳定

```js
_computeSolarLayout(stars, width, height) {
    const cx = width / 2, cy = height / 2;
    const core = stars.find(s => s.is_core);
    const rest = stars.filter(s => !s.is_core);
    const pos = {};
    if (core) pos[core.id] = { x: cx, y: cy };
    // 按 level 分环：level 3→r1, 2→r2, 1→r3, 0→r4（外）
    const ringR = { 3: 70, 2: 130, 1: 195, 0: 255 };
    const byRing = { 3: [], 2: [], 1: [], 0: [] };
    rest.forEach(s => byRing[s.level].push(s));
    for (const lv of [3, 2, 1, 0]) {
        const arr = byRing[lv], n = arr.length;
        arr.forEach((s, i) => {
            const ang = (i / Math.max(n, 1)) * Math.PI * 2 + lv;  // +lv 错开各环角度
            pos[s.id] = { x: cx + ringR[lv] * Math.cos(ang), y: cy + ringR[lv] * Math.sin(ang) };
        });
    }
    this.starPositions = pos;
}
```

### 改 6：成型态（板块 ≥80% 燃星时）

`enterGalaxy(cat)` 渲染后，若该板块 `get_galaxy_state` 里 `formed:true`，给 `#starmap-galaxy` 加 class `.galaxy-formed`。成型态只做**两个主表达**（别堆特效）：
1. **轨道闭合**：画出连接同环星点的淡色圆环轨道线（平时不画，成型才显现）
2. **核心主星升亮**：主星额外加大光晕 + 一次「升起」动画

```css
.galaxy-formed .orbit-ring { opacity: 0.25; }   /* 平时 0 */
.galaxy-formed .star-circle.is-core { filter: drop-shadow(0 0 24px var(--star-gold)); }
```

### 改 7：冷暖色对比（goforit 明确要的）

调整 §8.2 配色，强化「暗星冷、亮星暖」：
```css
.star-l0 { fill: #6f8bb0; opacity: 0.35; }  /* 暗星：冷蓝白微光（不是灰）*/
.star-l1 { fill: #ffd9a0; }                  /* 亮星起就转暖 */
.star-l2 { fill: var(--star-gold); }         /* 暖金 */
.star-l3 { fill: #fff3d6; filter: drop-shadow(0 0 14px #ffcf6e); } /* 暖白金 */
```

---

## 9.4 第二阶段验收（6 条，对应 9.0）

1. 进星图 tab → 先见银河总览，3 个板块入口，按学习进度发光
2. 点入口 → 缩放淡入进该板块，有返回按钮
3. 板块内呈太阳系轮廓：主星居中、其余按掌握度分环，全暗也成形
4. 去复习评分一个该板块概念 → 回星图，那颗星已点亮（暖色）
5. 某板块 ≥80% 概念到燃星 → 该板块显现轨道环 + 主星升亮（成型态）
6. 暗星冷蓝、亮星暖金，对比明显

## 9.5 实施顺序（Trae 按此走）

1. 后端 `get_star_map` 加 `is_core` + `_pick_core_stars`；新增 `get_galaxy_state` + main.py 代理（纯后端，先测）
2. 前端总览层 HTML/CSS + `get_galaxy_state` 渲染 3 入口
3. `enterGalaxy(cat)` / 返回 / 缩放淡入过渡
4. 太阳系布局 `_computeSolarLayout` 替换散布
5. 成型态 `.galaxy-formed`（轨道环 + 主星升亮）
6. 冷暖色微调
7. 跑一遍 9.4 六条验收



