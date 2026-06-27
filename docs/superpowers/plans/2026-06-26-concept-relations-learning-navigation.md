# Concept Relations Learning Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build learning-oriented concept relations inside the deep-dive page, including prerequisite chips, inline term explainers, next-step/confusion recommendations, and a lightweight local relations view.

**Architecture:** Keep `related_concepts` as the single source of truth, add a backend normalization layer plus a structured deep-dive payload API, and render the new relation UI entirely inside the existing deep-dive overlay without changing the analytics star map’s role. The backend will separate article text generation from relation-navigation metadata so the frontend can render prerequisite cards, inline term popovers, bottom recommendations, and a local graph panel with graceful fallback for old data.

**Tech Stack:** Python 3, pywebview API bridge, vanilla JavaScript, existing single-page HTML/CSS, JSON file storage, `unittest` for backend tests.

---

## File Map

### Existing files to modify

- `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\backend.py`
  - Add relation normalization helpers.
  - Add structured deep-dive payload builder.
  - Keep `deep_dive()` article generation intact while exposing new metadata.
- `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\main.py`
  - Expose the new structured deep-dive API to `window.pywebview.api`.
- `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\frontend\index.html`
  - Add prerequisite area, bottom relation blocks, local graph drawer, and inline relation popover shell.
- `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\frontend\app.js`
  - Load structured payload.
  - Render relation UI.
  - Wire inline popover, local graph panel, and “return to previous concept” behavior.
- `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\frontend\style.css`
  - Style the new deep-dive relation surfaces in the current visual language.

### New files to create

- `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\tests\test_deep_dive_relations.py`
  - Backend unit tests for relation normalization, payload shaping, fallback behavior, and inline-term selection.

---

### Task 1: Add Backend Relation Normalization

**Files:**
- Modify: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\backend.py`
- Create: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\tests\test_deep_dive_relations.py`

- [ ] **Step 1: Write the failing backend normalization tests**

```python
import tempfile
import unittest

from backend import Backend


class RelationNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.backend = Backend(self.tmp.name)
        self.backend.concepts = [
            {
                "id": "deflation",
                "term": "通货紧缩",
                "definition": "整体物价持续下降",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
                "related_concepts": [
                    {"id": "demand", "relation": "prerequisite"},
                    {"id": "inflation", "relation": "similar"},
                    {"id": "liquidity_trap", "relation": "extends"},
                ],
            },
            {
                "id": "demand",
                "term": "总需求",
                "definition": "经济中总购买需求",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "inflation",
                "term": "通货膨胀",
                "definition": "整体物价持续上涨",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "liquidity_trap",
                "term": "流动性陷阱",
                "definition": "低利率下货币政策失效",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_normalize_relations_maps_legacy_similar_to_confusable(self):
        rows = self.backend._normalize_relations(self.backend.concepts[0])
        by_id = {row["id"]: row for row in rows}
        self.assertEqual(by_id["inflation"]["relation"], "confusable")

    def test_normalize_relations_fills_missing_reason_hint_strength(self):
        rows = self.backend._normalize_relations(self.backend.concepts[0])
        demand = next(row for row in rows if row["id"] == "demand")
        self.assertTrue(demand["reason"])
        self.assertTrue(demand["hint"])
        self.assertGreaterEqual(demand["strength"], 0)
        self.assertLessEqual(demand["strength"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run:

```powershell
python -m unittest tests.test_deep_dive_relations.RelationNormalizationTests -v
```

Expected:

```text
ERROR: 'Backend' object has no attribute '_normalize_relations'
```

- [ ] **Step 3: Implement minimal normalization helpers in `backend.py`**

```python
RELATION_ALIAS_MAP = {
    "similar": "confusable",
}

RELATION_LABELS = {
    "prerequisite": "前置",
    "confusable": "易混淆",
    "extends": "延伸",
    "contrast": "对比",
}


def _clamp_strength(value, fallback=0.5):
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return fallback


class Backend:
    ...

    def _normalize_relation_type(self, raw_relation: str) -> str:
        relation = (raw_relation or "").strip().lower()
        relation = RELATION_ALIAS_MAP.get(relation, relation)
        if relation in {"prerequisite", "confusable", "extends", "contrast"}:
            return relation
        return "extends"

    def _default_relation_reason(self, source_term: str, target_term: str, relation: str) -> str:
        templates = {
            "prerequisite": f"理解“{source_term}”之前，先补“{target_term}”会更顺。",
            "confusable": f"“{source_term}”和“{target_term}”很容易被混在一起。",
            "extends": f"学完“{source_term}”后，自然可以延伸到“{target_term}”。",
            "contrast": f"“{source_term}”和“{target_term}”经常一起出现，但需要对照着看。",
        }
        return templates[relation]

    def _default_relation_hint(self, relation: str) -> str:
        hints = {
            "prerequisite": "建议先补这个，再回来继续读。",
            "confusable": "重点看两者最关键的区别。",
            "extends": "如果你已经理解当前概念，可以继续学这个。",
            "contrast": "对照方向、机制或结果去理解差异。",
        }
        return hints[relation]

    def _normalize_relations(self, card: dict) -> list[dict]:
        valid_ids = {c["id"] for c in self.concepts}
        by_id = {c["id"]: c for c in self.concepts}
        rows = []
        seen = set()
        for raw in card.get("related_concepts", []):
            target_id = raw.get("id")
            if not target_id or target_id not in valid_ids or target_id == card["id"] or target_id in seen:
                continue
            seen.add(target_id)
            relation = self._normalize_relation_type(raw.get("relation"))
            target = by_id[target_id]
            rows.append({
                "id": target_id,
                "term": target["term"],
                "definition": target.get("definition", ""),
                "category": target.get("category", ""),
                "relation": relation,
                "relation_label": RELATION_LABELS[relation],
                "reason": raw.get("reason") or self._default_relation_reason(card["term"], target["term"], relation),
                "hint": raw.get("hint") or self._default_relation_hint(relation),
                "difference": raw.get("difference", ""),
                "strength": _clamp_strength(raw.get("strength"), 0.5),
            })
        return rows
```

- [ ] **Step 4: Run the normalization tests again**

Run:

```powershell
python -m unittest tests.test_deep_dive_relations.RelationNormalizationTests -v
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add backend.py tests/test_deep_dive_relations.py
git commit -m "feat: normalize concept relations for learning navigation"
```

---

### Task 2: Build Structured Deep-Dive Payload in Backend and API

**Files:**
- Modify: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\backend.py`
- Modify: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\main.py`
- Modify: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\tests\test_deep_dive_relations.py`

- [ ] **Step 1: Add failing payload tests**

```python
class DeepDivePayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.backend = Backend(self.tmp.name)
        self.backend.concepts = [
            {
                "id": "deflation",
                "term": "通货紧缩",
                "definition": "整体物价持续下降",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
                "deep_article": (
                    "# 一句话讲清\n"
                    "通货紧缩是整体价格持续下降。\n\n"
                    "## 核心定义拆解\n"
                    "当**总需求**持续不足时，价格会往下走，并可能和**通货膨胀**形成对照。\n\n"
                    "## 底层机制\n"
                    "如果企业和消费者都观望，经济可能掉进**流动性陷阱**。"
                ),
                "deep_article_version": 2,
                "related_concepts": [
                    {"id": "demand", "relation": "prerequisite", "reason": "总需求不足会直接影响理解。"},
                    {"id": "inflation", "relation": "similar", "difference": "一个跌价，一个涨价。"},
                    {"id": "liquidity_trap", "relation": "extends"},
                ],
            },
            {
                "id": "demand",
                "term": "总需求",
                "definition": "经济中的总购买需求",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "inflation",
                "term": "通货膨胀",
                "definition": "整体物价持续上涨",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "liquidity_trap",
                "term": "流动性陷阱",
                "definition": "低利率下货币政策失效",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_deep_dive_payload_returns_prerequisites_and_sections(self):
        payload = self.backend.get_deep_dive_payload("deflation")
        self.assertEqual(payload["card"]["term"], "通货紧缩")
        self.assertEqual(len(payload["prerequisites"]), 1)
        self.assertIn("sections", payload)

    def test_get_deep_dive_payload_selects_inline_terms_from_article(self):
        payload = self.backend.get_deep_dive_payload("deflation")
        terms = [item["term"] for item in payload["inline_terms"]]
        self.assertIn("总需求", terms)
        self.assertIn("通货膨胀", terms)
        self.assertLessEqual(len(terms), 6)

    def test_get_deep_dive_payload_falls_back_when_no_relations_exist(self):
        self.backend.concepts[0]["related_concepts"] = []
        payload = self.backend.get_deep_dive_payload("deflation")
        self.assertEqual(payload["prerequisites"], [])
        self.assertEqual(payload["next_steps"], [])
        self.assertEqual(payload["confusions"], [])
```

- [ ] **Step 2: Run the payload tests to verify failure**

Run:

```powershell
python -m unittest tests.test_deep_dive_relations.DeepDivePayloadTests -v
```

Expected:

```text
ERROR: 'Backend' object has no attribute 'get_deep_dive_payload'
```

- [ ] **Step 3: Implement payload builders in `backend.py`**

```python
class Backend:
    ...

    def _split_markdown_sections(self, article: str) -> list[dict]:
        if not article:
            return []
        sections = []
        current = None
        for line in article.splitlines():
            if line.startswith("## "):
                if current:
                    sections.append(current)
                current = {"title": line[3:].strip(), "body": []}
            elif current:
                current["body"].append(line)
        if current:
            sections.append(current)
        for section in sections:
            section["content"] = "\n".join(section["body"]).strip()
            section.pop("body", None)
        return sections

    def _pick_inline_terms(self, article: str, relations: list[dict]) -> list[dict]:
        ranked = []
        priority = {"prerequisite": 0, "confusable": 1, "extends": 2}
        for row in relations:
            if row["relation"] not in priority:
                continue
            if row["term"] not in article:
                continue
            ranked.append((priority[row["relation"]], -row["strength"], row))
        ranked.sort()
        picked = []
        seen = set()
        for _, _, row in ranked:
            if row["term"] in seen:
                continue
            picked.append(row)
            seen.add(row["term"])
            if len(picked) >= 6:
                break
        return picked

    def _build_learning_navigation(self, card: dict, article: str) -> dict:
        rows = self._normalize_relations(card)
        prerequisites = [row for row in rows if row["relation"] == "prerequisite"][:2]
        confusions = [row for row in rows if row["relation"] in {"confusable", "contrast"}][:2]
        next_steps = [row for row in rows if row["relation"] == "extends"][:2]
        local_graph = (prerequisites + confusions + next_steps)[:7]
        return {
            "prerequisites": prerequisites,
            "confusions": confusions,
            "next_steps": next_steps,
            "inline_terms": self._pick_inline_terms(article, rows),
            "local_graph": {
                "center": {"id": card["id"], "term": card["term"]},
                "nodes": local_graph,
            },
        }

    def get_deep_dive_payload(self, card_id: str) -> dict:
        card = self._find_card(card_id)
        if not card:
            return {"error": "not_found"}
        article = self.deep_dive(card_id)
        nav = self._build_learning_navigation(card, article if not article.startswith("⚠️") else "")
        return {
            "card": {
                "id": card["id"],
                "term": card["term"],
                "definition": card.get("definition", ""),
                "category": card.get("category", ""),
            },
            "article": article,
            "sections": self._split_markdown_sections(article if not article.startswith("⚠️") else ""),
            **nav,
        }
```

- [ ] **Step 4: Expose the new API in `main.py`**

```python
class Api:
    ...

    def get_deep_dive_payload(self, card_id: str) -> dict:
        return self.backend.get_deep_dive_payload(card_id)
```

- [ ] **Step 5: Run backend payload tests**

Run:

```powershell
python -m unittest tests.test_deep_dive_relations.DeepDivePayloadTests -v
```

Expected:

```text
OK
```

- [ ] **Step 6: Commit**

```bash
git add backend.py main.py tests/test_deep_dive_relations.py
git commit -m "feat: add structured deep dive payload api"
```

---

### Task 3: Add Deep-Dive Relation Markup and Styles

**Files:**
- Modify: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\frontend\index.html`
- Modify: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\frontend\style.css`

- [ ] **Step 1: Add the new HTML shells inside the article tab**

```html
<div class="deep-tab-content" id="tab-article">
  <div class="article-loading" id="article-loading">
    <div class="loading-spinner"></div>
    <p>正在生成深度解读...</p>
  </div>

  <div class="article-navigation" id="article-navigation" style="display:none;">
    <section class="article-prereq" id="article-prereq" style="display:none;">
      <div class="article-block-head">
        <h3>开始前先懂这 2 个</h3>
      </div>
      <div class="article-prereq-list" id="article-prereq-list"></div>
    </section>

    <div class="article-content markdown-body" id="article-content" style="display:none;"></div>

    <section class="article-relations" id="article-relations" style="display:none;">
      <div class="article-relations-grid">
        <div class="article-relation-group">
          <div class="article-block-head">
            <h3>接下来学什么</h3>
          </div>
          <div id="article-next-list"></div>
        </div>
        <div class="article-relation-group">
          <div class="article-block-head">
            <h3>最容易混淆</h3>
            <button class="article-link-btn" id="btn-open-local-graph" type="button">查看关联</button>
          </div>
          <div id="article-confusion-list"></div>
        </div>
      </div>
    </section>
  </div>

  <div class="term-popover" id="term-popover" style="display:none;"></div>
  <div class="local-graph-sheet" id="local-graph-sheet" style="display:none;"></div>
</div>
```

- [ ] **Step 2: Add styles for prerequisite cards, inline terms, relation lists, popover, and graph sheet**

```css
.article-navigation {
    display: flex;
    flex-direction: column;
    gap: 18px;
}

.article-prereq,
.article-relations,
.local-graph-sheet {
    border-radius: 24px;
    padding: 18px;
    background: rgba(255, 255, 255, 0.44);
    border: 1px solid rgba(255, 255, 255, 0.62);
}

.article-prereq-list,
.article-relations-grid {
    display: grid;
    gap: 12px;
}

.article-relations-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.relation-card,
.prereq-card {
    padding: 14px 16px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.7);
}

.inline-term {
    border-bottom: 1px dashed rgba(86, 105, 180, 0.8);
    background: rgba(219, 231, 255, 0.42);
    cursor: pointer;
}

.term-popover {
    position: absolute;
    z-index: 8;
    max-width: 320px;
    padding: 14px;
    border-radius: 18px;
    background: rgba(255, 252, 246, 0.96);
    box-shadow: var(--shadow-floating);
}

.local-graph-sheet.is-open {
    display: block;
}

@media (max-width: 760px) {
    .article-relations-grid {
        grid-template-columns: 1fr;
    }
}
```

- [ ] **Step 3: Sanity-check the page still loads with the new markup**

Run:

```powershell
python -m py_compile backend.py main.py
```

Expected:

```text
<no output>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/style.css
git commit -m "feat: add deep dive relation layout shells"
```

---

### Task 4: Render Relation Navigation in `app.js`

**Files:**
- Modify: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\frontend\app.js`

- [ ] **Step 1: Replace article loading flow to consume the structured payload**

```javascript
async openDeepDive(card) {
    this.deepDiveCard = card;
    this.deepDiveReturnStack = this.deepDiveReturnStack || [];
    this.currentDeepDivePayload = null;
    this.hideTermPopover();
    this.hideLocalGraph();

    const overlay = document.getElementById("deep-dive-overlay");
    overlay.style.display = "";
    document.body.classList.add("deep-dive-open");
    document.getElementById("deep-dive-concept-title").textContent = card.term;

    this.switchDeepTab("article");
    this.resetDeepDiveArticleState();
    this.resetDeepDiveQuiz(card);
    await this.loadDeepDiveChat(card);

    try {
        const payload = await window.pywebview.api.get_deep_dive_payload(card.id);
        this.currentDeepDivePayload = payload;
        document.getElementById("article-loading").style.display = "none";
        document.getElementById("article-navigation").style.display = "";
        document.getElementById("article-content").style.display = "";
        this.renderDeepDiveArticle(payload);
    } catch (err) {
        document.getElementById("article-loading").innerHTML = `<p style="color:var(--color-forgot)">加载失败，请重试</p>`;
        console.error("Deep dive payload failed:", err);
    }
}
```

- [ ] **Step 2: Add article render helpers**

```javascript
renderDeepDiveArticle(payload) {
    const articleHtml = this.renderMarkdown(payload.article || "");
    document.getElementById("article-content").innerHTML = this.decorateInlineTerms(articleHtml, payload.inline_terms || []);
    this.renderPrerequisites(payload.prerequisites || []);
    this.renderRelationList("article-next-list", payload.next_steps || []);
    this.renderRelationList("article-confusion-list", payload.confusions || []);
    document.getElementById("article-relations").style.display =
        (payload.next_steps?.length || payload.confusions?.length) ? "" : "none";
    this.bindInlineTerms(payload.inline_terms || []);
}

renderPrerequisites(rows) {
    const wrap = document.getElementById("article-prereq");
    const list = document.getElementById("article-prereq-list");
    list.innerHTML = rows.map((row) => `
        <article class="prereq-card">
            <div class="relation-card-title">${this.escapeHtml(row.term)}</div>
            <div class="relation-card-copy">${this.escapeHtml(row.reason)}</div>
            <button class="article-link-btn" type="button" data-open-concept="${row.id}">先看 1 分钟</button>
        </article>
    `).join("");
    wrap.style.display = rows.length ? "" : "none";
    list.querySelectorAll("[data-open-concept]").forEach((btn) => {
        btn.addEventListener("click", () => this.openConceptFromRelation(btn.dataset.openConcept));
    });
}

renderRelationList(containerId, rows) {
    const el = document.getElementById(containerId);
    el.innerHTML = rows.map((row) => `
        <article class="relation-card">
            <div class="relation-card-title">${this.escapeHtml(row.term)}</div>
            <div class="relation-card-copy">${this.escapeHtml(row.reason)}</div>
            <button class="article-link-btn" type="button" data-open-concept="${row.id}">去看这个概念</button>
        </article>
    `).join("");
    el.querySelectorAll("[data-open-concept]").forEach((btn) => {
        btn.addEventListener("click", () => this.openConceptFromRelation(btn.dataset.openConcept));
    });
}
```

- [ ] **Step 3: Add inline-term popover and navigation helpers**

```javascript
decorateInlineTerms(html, rows) {
    let output = html;
    rows.forEach((row) => {
        const safeTerm = this.escapeHtml(row.term);
        output = output.replace(
            safeTerm,
            `<button class="inline-term" type="button" data-inline-term="${row.id}">${safeTerm}</button>`
        );
    });
    return output;
}

bindInlineTerms(rows) {
    const byId = Object.fromEntries(rows.map((row) => [row.id, row]));
    document.querySelectorAll("[data-inline-term]").forEach((btn) => {
        btn.addEventListener("click", (event) => {
            const row = byId[btn.dataset.inlineTerm];
            this.showTermPopover(event.currentTarget, row);
        });
    });
}

showTermPopover(anchor, row) {
    const pop = document.getElementById("term-popover");
    pop.innerHTML = `
        <div class="term-popover-title">${this.escapeHtml(row.term)}</div>
        <div class="term-popover-definition">${this.escapeHtml(row.definition)}</div>
        <div class="term-popover-reason">${this.escapeHtml(row.reason)}</div>
        ${row.relation === "prerequisite" ? `<div class="term-popover-hint">建议：先补这个，再回来</div>` : ""}
        ${row.difference ? `<div class="term-popover-diff">关键区别：${this.escapeHtml(row.difference)}</div>` : ""}
        <button class="article-link-btn" id="term-popover-open" type="button">去看这个概念</button>
    `;
    const rect = anchor.getBoundingClientRect();
    pop.style.left = `${rect.left + window.scrollX}px`;
    pop.style.top = `${rect.bottom + window.scrollY + 8}px`;
    pop.style.display = "";
    document.getElementById("term-popover-open").onclick = () => this.openConceptFromRelation(row.id);
}
```

- [ ] **Step 4: Add local graph sheet and return-stack behavior**

```javascript
showLocalGraph() {
    const sheet = document.getElementById("local-graph-sheet");
    const payload = this.currentDeepDivePayload;
    const nodes = payload?.local_graph?.nodes || [];
    sheet.innerHTML = `
        <div class="article-block-head">
            <h3>当前关联</h3>
            <button class="article-link-btn" id="btn-close-local-graph" type="button">收起</button>
        </div>
        <div class="local-graph-list">
            ${nodes.map((row) => `
                <article class="relation-card">
                    <div class="relation-badge">${this.escapeHtml(row.relation_label)}</div>
                    <div class="relation-card-title">${this.escapeHtml(row.term)}</div>
                    <div class="relation-card-copy">${this.escapeHtml(row.reason)}</div>
                    <button class="article-link-btn" type="button" data-open-concept="${row.id}">去看这个概念</button>
                </article>
            `).join("")}
        </div>
    `;
    sheet.style.display = "";
    sheet.classList.add("is-open");
    document.getElementById("btn-close-local-graph").onclick = () => this.hideLocalGraph();
    sheet.querySelectorAll("[data-open-concept]").forEach((btn) => {
        btn.addEventListener("click", () => this.openConceptFromRelation(btn.dataset.openConcept));
    });
}

openConceptFromRelation(conceptId) {
    const found = [...this.cards, this.currentCard, this.exploreCard, this.deepDiveCard]
        .filter(Boolean)
        .find((item) => item.id === conceptId);
    if (this.deepDiveCard) {
        this.deepDiveReturnStack.push({
            id: this.deepDiveCard.id,
            scrollTop: document.querySelector(".deep-dive-body")?.scrollTop || 0,
        });
    }
    if (found) {
        this.openDeepDive(found);
        return;
    }
    this.openDeepDive({ id: conceptId, term: conceptId, definition: "", category: "" });
}
```

- [ ] **Step 5: Wire the new buttons and reset helpers**

```javascript
bindDeepDiveEvents() {
    ...
    document.getElementById("btn-open-local-graph").addEventListener("click", () => this.showLocalGraph());
    document.addEventListener("click", (e) => {
        const pop = document.getElementById("term-popover");
        if (pop.style.display === "none") return;
        if (!e.target.closest(".inline-term") && !e.target.closest("#term-popover")) {
            this.hideTermPopover();
        }
    });
}

resetDeepDiveArticleState() {
    document.getElementById("article-loading").style.display = "";
    document.getElementById("article-navigation").style.display = "none";
    document.getElementById("article-content").style.display = "none";
    document.getElementById("article-content").innerHTML = "";
    document.getElementById("article-prereq-list").innerHTML = "";
    document.getElementById("article-next-list").innerHTML = "";
    document.getElementById("article-confusion-list").innerHTML = "";
}

hideTermPopover() {
    document.getElementById("term-popover").style.display = "none";
}

hideLocalGraph() {
    const sheet = document.getElementById("local-graph-sheet");
    sheet.style.display = "none";
    sheet.classList.remove("is-open");
    sheet.innerHTML = "";
}
```

- [ ] **Step 6: Run a smoke check for syntax**

Run:

```powershell
@'
from pathlib import Path
text = Path("frontend/app.js").read_text(encoding="utf-8")
print("get_deep_dive_payload" in text)
print("renderDeepDiveArticle" in text)
print("showLocalGraph" in text)
'@ | python -
```

Expected:

```text
True
True
True
```

- [ ] **Step 7: Commit**

```bash
git add frontend/app.js
git commit -m "feat: render deep dive learning navigation"
```

---

### Task 5: Regression Tests and Manual Verification

**Files:**
- Modify: `C:\Users\Administrator\Desktop\概念复习_参赛资料\概念复习应用\tests\test_deep_dive_relations.py`

- [ ] **Step 1: Add one regression test for empty old-format relations**

```python
class DeepDiveRegressionTests(unittest.TestCase):
    def test_old_relation_rows_do_not_break_payload(self):
        tmp = tempfile.TemporaryDirectory()
        backend = Backend(tmp.name)
        backend.concepts = [
            {
                "id": "a",
                "term": "A",
                "definition": "A definition",
                "category": "测试",
                "created_at": "2026-06-20T10:00:00",
                "deep_article": "## 核心定义拆解\nA 和 B 有关联。",
                "deep_article_version": 2,
                "related_concepts": [{"id": "b", "relation": "similar"}],
            },
            {
                "id": "b",
                "term": "B",
                "definition": "B definition",
                "category": "测试",
                "created_at": "2026-06-20T10:00:00",
            },
        ]
        payload = backend.get_deep_dive_payload("a")
        self.assertEqual(payload["confusions"][0]["relation"], "confusable")
        tmp.cleanup()
```

- [ ] **Step 2: Run the full backend test file**

Run:

```powershell
python -m unittest tests.test_deep_dive_relations -v
```

Expected:

```text
OK
```

- [ ] **Step 3: Manual UI verification checklist**

Run the app:

```powershell
python main.py
```

Verify in the UI:

```text
1. 打开任意有关系的概念，顶部出现“开始前先懂这 2 个”。
2. 文章中少量术语带轻量交互样式，点击可弹出解释卡。
3. 底部出现“接下来学什么”和“最容易混淆”。
4. 点击“查看关联”只出现当前概念的局部关联，不是全局大图。
5. 没有关联的概念不会出现空白模块。
6. 自测与自由问答仍然正常切换。
7. 分析页星图仍能打开，不受影响。
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_deep_dive_relations.py
git commit -m "test: cover deep dive relation navigation regressions"
```

---

## Self-Review

### Spec coverage

- 顶部前置概念：Task 2 payload + Task 3 markup + Task 4 render
- 文中关键词点按：Task 2 inline-term selection + Task 4 popover/render
- 底部下一步 / 易混淆：Task 2 payload + Task 4 relation lists
- 局部关系图：Task 2 local graph data + Task 4 graph sheet
- 保持星图不变：Task 2/4 only add new deep-dive path, no analytics rewiring
- 旧数据兼容：Task 1 + Task 5 regression

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Every code-changing step includes explicit code.
- Every verification step includes an exact command and expected result.

### Type consistency

- Backend API name: `get_deep_dive_payload`
- Frontend payload property names: `prerequisites`, `inline_terms`, `next_steps`, `confusions`, `local_graph`
- Relation type mapping is consistent: legacy `similar` becomes `confusable`

