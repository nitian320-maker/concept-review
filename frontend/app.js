// ===== Concept Reviewer App =====

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

class ConceptReviewer {
    constructor() {
        this.cards = [];
        this.currentCard = null;
        this.currentCategory = "全部";
        this.isAnimating = false;
        this.chatHistory = [];
        this.activeDeepTab = "article";
        this.deepDiveCard = null;
        this.deepDivePayload = null;
        this.deepDiveReturnStack = [];
        this.deepDivePath = [];
        this.deepDiveLoadSeq = 0;
        this.quizQuestions = [];
        this.quizIndex = 0;
        this.quizAnswered = [false, false, false];
        this.quizDrafts = ["", "", ""];
        this.addMode = "manual";
        this.discoveredTerms = [];
        this.exploreCard = null;
        this.exploredIds = [];
        this.timelineFilter = null;
        this.starMapData = null;
        this.starPositions = {};
        this.selectedStarId = null;
        this.currentGalaxy = null;
        this._starmapBound = false;
    }

    async init() {
        await this.renderCategoryTabs();
        this.bindCardEvents();
        this.bindModalEvents();
        this.bindDeepDiveEvents();
        this.bindKeyboard();
        await this.refreshCards();
    }

    async renderCategoryTabs() {
        try {
            const categories = await api.get_categories();
            const tabsNav = document.getElementById("tabs-nav");
            const modeTabs = document.getElementById("mode-tabs");
            tabsNav.querySelectorAll(".tab-category-wrap").forEach(t => t.remove());
            const activeMode = this.currentCategory === "探索"
                ? "探索"
                : this.currentCategory === "分析"
                    ? "分析"
                    : "全部";
            modeTabs?.querySelectorAll(".tab").forEach((tab) => {
                tab.classList.toggle("active", tab.dataset.category === activeMode);
            });
            tabsNav.querySelector('.tab[data-category="全部"]').classList.toggle("active", this.currentCategory === "全部");
            const sep = tabsNav.querySelector(".tabs-sep");
            categories.forEach(cat => {
                const wrap = document.createElement("span");
                wrap.className = "tab-category-wrap";
                const btn = document.createElement("button");
                btn.className = "tab tab-category" + (cat === this.currentCategory ? " active" : "");
                btn.dataset.category = cat;
                btn.textContent = cat;
                const del = document.createElement("button");
                del.className = "tab-delete";
                del.dataset.category = cat;
                del.textContent = "\u00d7";
                del.title = "删除 " + cat;
                wrap.appendChild(btn);
                wrap.appendChild(del);
                sep.before(wrap);
            });
        } catch (err) {
            console.error("Failed to load categories:", err);
        }
    }

    // ---- Card Events ----

    bindCardEvents() {
        document.getElementById("mode-tabs").addEventListener("click", (e) => {
            const tab = e.target.closest(".tab");
            if (tab) this.onTabClick(tab);
        });

        document.getElementById("tabs-nav").addEventListener("click", (e) => {
            if (e.target.closest(".tab-delete")) {
                e.stopPropagation();
                const delBtn = e.target.closest(".tab-delete");
                this.onDeleteCategory(delBtn.dataset.category);
                return;
            }
            const tab = e.target.closest(".tab");
            if (tab) this.onTabClick(tab);
        });

        document.getElementById("flashcard").addEventListener("click", () => {
            if (!this.isAnimating && !this.isFlipped() && this.currentCard) {
                this.flip();
            }
        });

        document.querySelectorAll(".rate-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                if (this.isAnimating) return;
                if (!this.isFlipped()) return;
                this.onRate(parseInt(btn.dataset.quality));
            });
        });

        document.getElementById("btn-deep-dive").addEventListener("click", (e) => {
            e.stopPropagation();
            if (!this.currentCard) return;
            this.openDeepDive(this.currentCard);
        });

        document.getElementById("btn-refresh-explore").addEventListener("click", () => this.onRefreshExplore());
        document.getElementById("btn-explore-deep").addEventListener("click", () => this.onExploreDeepDive());
    }

    // ---- Modal Events ----

    bindModalEvents() {
        document.getElementById("btn-add").addEventListener("click", () => this.showModal());

        document.getElementById("modal-overlay").addEventListener("click", (e) => {
            if (e.target === e.currentTarget) this.hideModal();
        });
        document.getElementById("btn-cancel").addEventListener("click", () => this.hideModal());
        document.getElementById("btn-save").addEventListener("click", () => this.onSaveConcept());
        document.getElementById("btn-discover-search").addEventListener("click", () => this.onDiscoverIndustryTerms());
        document.getElementById("btn-import-discovered").addEventListener("click", () => this.onImportDiscoveredTerms());
        document.querySelectorAll(".add-mode-tab").forEach(tab => {
            tab.addEventListener("click", () => this.switchAddMode(tab.dataset.addMode));
        });

        document.getElementById("new-definition").addEventListener("keydown", (e) => {
            if (e.key === "Enter" && e.ctrlKey) this.onSaveConcept();
        });
        document.getElementById("discover-industry").addEventListener("keydown", (e) => {
            if (e.key === "Enter") this.onDiscoverIndustryTerms();
        });

        document.getElementById("btn-settings").addEventListener("click", () => this.showSettings());
        document.getElementById("settings-overlay").addEventListener("click", (e) => {
            if (e.target === e.currentTarget) this.hideSettings();
        });
        document.getElementById("btn-settings-cancel").addEventListener("click", () => this.hideSettings());
        document.getElementById("btn-settings-save").addEventListener("click", () => this.onSaveSettings());
    }

    // ---- Deep Dive Events ----

    bindDeepDiveEvents() {
        document.getElementById("deep-dive-close").addEventListener("click", () => this.closeDeepDive());
        document.getElementById("deep-dive-overlay").addEventListener("click", (e) => {
            if (e.target === e.currentTarget) this.closeDeepDive();
        });

        document.querySelectorAll(".deep-tab").forEach(tab => {
            tab.addEventListener("click", () => this.switchDeepTab(tab.dataset.tab));
        });

        // Quiz
        document.getElementById("quiz-prev").addEventListener("click", () => this.switchQuiz(-1));
        document.getElementById("quiz-next").addEventListener("click", () => this.switchQuiz(1));
        document.getElementById("quiz-reveal").addEventListener("click", () => this.revealQuizAnswer());
        document.getElementById("quiz-go-article").addEventListener("click", () => this.switchDeepTab("article"));
        document.getElementById("quiz-go-chat").addEventListener("click", () => this.switchDeepTab("chat"));
        document.getElementById("quiz-input").addEventListener("input", () => this.onQuizInput());

        document.getElementById("chat-send").addEventListener("click", () => this.sendChatMessage());
        document.getElementById("chat-input").addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                this.sendChatMessage();
            }
        });

        document.getElementById("chat-clear").addEventListener("click", () => this.clearChatHistory());

        document.querySelectorAll(".chat-chip").forEach((chip) => {
            chip.addEventListener("click", () => {
                const input = document.getElementById("chat-input");
                input.value = chip.textContent.trim();
                input.focus();
            });
        });

        document.getElementById("btn-open-local-graph").addEventListener("click", () => this.showLocalGraph());
        document.getElementById("tab-article").addEventListener("scroll", () => this.hideTermPopover());
        document.addEventListener("click", (e) => {
            if (document.getElementById("deep-dive-overlay").style.display === "none") return;
            if (e.target.closest(".inline-term") || e.target.closest("#term-popover")) return;
            this.hideTermPopover();
        });
        document.getElementById("deep-dive-concept-title").addEventListener("click", () => {
            if (this.deepDiveReturnStack.length) this.goBackDeepDiveConcept();
        });
    }

    // ---- Keyboard ----

    bindKeyboard() {
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                const overlay = document.getElementById("deep-dive-overlay");
                if (overlay.style.display !== "none") {
                    e.preventDefault();
                    this.closeDeepDive();
                    return;
                }
            }

            if (document.getElementById("modal-overlay").style.display !== "none") return;
            if (document.getElementById("deep-dive-overlay").style.display !== "none") return;
            if (document.getElementById("explore-view").style.display !== "none") return;
            if (document.getElementById("analytics-view").style.display !== "none") return;
            if (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA") return;

            if (this.isAnimating) return;

            if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                if (!this.isFlipped() && this.currentCard) this.flip();
            } else if (e.key === "1" && this.isFlipped()) {
                e.preventDefault();
                this.onRate(1);
            } else if (e.key === "2" && this.isFlipped()) {
                e.preventDefault();
                this.onRate(3);
            } else if (e.key === "3" && this.isFlipped()) {
                e.preventDefault();
                this.onRate(5);
            }
        });
    }

    // ---- API Helpers ----

    async refreshCards() {
        try {
            this.cards = await api.get_due_cards(this.currentCategory);
            this.updateStats();
            if (this.currentCard === null) this.showNext();
        } catch (err) {
            console.error("Failed to load cards:", err);
        }
    }

    async rateCardAPI(quality) {
        try {
            await api.rate_card(this.currentCard.id, quality);
        } catch (err) {
            console.error("Failed to rate card:", err);
        }
    }

    async updateStats() {
        try {
            const stats = await api.get_stats();
            const dueEl = document.getElementById("due-count");
            const totalEl = document.getElementById("total-count");
            if (dueEl) dueEl.textContent = stats.due_today;
            if (totalEl) totalEl.textContent = stats.total;
        } catch (err) {
            console.error("Failed to load stats:", err);
        }
    }

    // ---- Card Navigation ----

    showNext() {
        if (this.cards.length === 0) {
            this.showEmptyState();
            return;
        }

        this.currentCard = this.cards.shift();
        const card = document.getElementById("flashcard");
        const cardInner = document.getElementById("card-inner");

        cardInner.classList.remove("flipped");
        card.classList.remove("slide-out");

        document.getElementById("card-category").textContent = this.currentCard.category;
        document.getElementById("card-term").textContent = this.currentCard.term;
        document.getElementById("card-definition").textContent = this.currentCard.definition;

        document.getElementById("empty-state").style.display = "none";
        card.style.display = "";

        card.style.animation = "cardEnter 0.4s var(--ease-out) forwards";
        setTimeout(() => { card.style.animation = ""; }, 400);
    }

    showEmptyState() {
        this.currentCard = null;
        document.getElementById("flashcard").style.display = "none";
        document.getElementById("empty-state").style.display = "";
        if (this.currentCategory === "全部") {
            document.getElementById("empty-title").textContent = "今日复习已完成";
            document.getElementById("empty-desc").textContent = "干得漂亮，明天继续加油";
        } else {
            document.getElementById("empty-title").textContent = "该分类暂无待复习";
            document.getElementById("empty-desc").textContent = "切换分类或添加新概念吧";
        }
    }

    // ---- Card Interaction ----

    isFlipped() { return document.getElementById("card-inner").classList.contains("flipped"); }

    flip() { document.getElementById("card-inner").classList.add("flipped"); }

    async onRate(quality) {
        if (this.isAnimating) return;
        this.isAnimating = true;

        let oldLevel = 0;
        const ratedCardId = this.currentCard?.id;
        if (ratedCardId) {
            try {
                const sm = await api.get_star_map("全部");
                const oldStar = sm.stars.find(s => s.id === ratedCardId);
                if (oldStar) oldLevel = oldStar.level;
            } catch (e) {}
        }

        await this.rateCardAPI(quality);
        const card = document.getElementById("flashcard");
        card.classList.add("slide-out");
        await sleep(400);
        await this.updateStats();
        this.showNext();
        this.isAnimating = false;

        if (ratedCardId && quality === 5) {
            try {
                const sm = await api.get_star_map("全部");
                const newStar = sm.stars.find(s => s.id === ratedCardId);
                if (newStar && newStar.level > oldLevel) {
                    this._triggerStarIgnite(ratedCardId, newStar.level);
                }
            } catch (e) {}
        }
    }

    // ---- Category Tabs ----

    async onTabClick(tab) {
        const category = tab.dataset.category;
        if (category === this.currentCategory) return;

        this.currentCategory = category;
        document.getElementById("mode-tabs").querySelectorAll(".tab").forEach((t) => {
            t.classList.toggle("active", t.dataset.category === (category === "探索" || category === "分析" ? category : "全部"));
        });
        document.getElementById("tabs-nav").querySelectorAll(".tab").forEach((t) => {
            t.classList.toggle("active", t.dataset.category === category);
        });

        if (category === "探索") {
            this.showExploreView();
        } else if (category === "分析") {
            this.showAnalyticsView();
        } else {
            this.showCardView();
            this.currentCard = null;
            this.cards = [];
            document.getElementById("card-inner").classList.remove("flipped");
            document.getElementById("flashcard").classList.remove("slide-out");
            await this.refreshCards();
        }
    }

    async onDeleteCategory(category) {
        if (!confirm(`确定要删除「${category}」分组及其所有卡片吗？\n\n此操作不可撤销。`)) return;
        const count = await api.delete_category(category);
        if (count > 0) {
            if (this.currentCategory === category) {
                this.currentCategory = "全部";
            }
            await this.renderCategoryTabs();
            await this.refreshCards();
            await this.updateStats();
        }
    }

    // ---- Explore ----

    showExploreView() {
        this.exploredIds = [];
        document.getElementById("review-stage-panel").style.display = "none";
        document.getElementById("empty-state").style.display = "none";
        document.getElementById("analytics-view").style.display = "none";
        document.getElementById("explore-view").style.display = "";
        this.loadExplore();
    }

    showCardView() {
        document.getElementById("explore-view").style.display = "none";
        document.getElementById("analytics-view").style.display = "none";
        document.getElementById("review-stage-panel").style.display = "";
        document.getElementById("empty-state").style.display = "none";
    }

    showAnalyticsView() {
        document.getElementById("review-stage-panel").style.display = "none";
        document.getElementById("empty-state").style.display = "none";
        document.getElementById("explore-view").style.display = "none";
        document.getElementById("analytics-view").style.display = "";
        this.timelineFilter = null;
        if (!this._analyticsBound) {
            this._analyticsBound = true;
            document.querySelector(".analytics-subtabs").addEventListener("click", (e) => {
                const tab = e.target.closest(".asubtab");
                if (tab) this.switchAnalyticsTab(tab.dataset.view);
            });
        }
        this.switchAnalyticsTab("heatmap");
    }

    switchAnalyticsTab(view) {
        document.querySelectorAll(".asubtab").forEach(t => t.classList.toggle("active", t.dataset.view === view));
        document.getElementById("analytics-heatmap").style.display = view === "heatmap" ? "" : "none";
        document.getElementById("analytics-dashboard").style.display = view === "dashboard" ? "" : "none";
        document.getElementById("analytics-timeline").style.display = view === "timeline" ? "" : "none";
        document.getElementById("analytics-history").style.display = view === "history" ? "" : "none";
        document.getElementById("analytics-starmap").style.display = view === "starmap" ? "" : "none";

        if (view === "heatmap") this.loadHeatmap();
        else if (view === "dashboard") this.loadDashboard();
        else if (view === "timeline") this.loadTimeline();
        else if (view === "history") this.loadHistory();
        else if (view === "starmap") this.renderStarMap();
    }

    async loadExplore() {
        const reasonEl = document.getElementById("explore-reason");
        reasonEl.innerHTML = '<div class="loading-spinner"></div>';

        try {
            const card = await api.random_explore("全部", this.exploredIds);
            if (!card) {
                this.exploredIds = [];
                reasonEl.innerHTML = '<span style="color:var(--text-tertiary);">所有概念都看过了，再从头来一遍吧。</span>';
                setTimeout(() => this.loadExplore(), 1000);
                return;
            }
            this.exploreCard = card;
            this.exploredIds.push(card.id);

            document.getElementById("explore-category").textContent = card.category;
            document.getElementById("explore-term").textContent = card.term;
            document.getElementById("explore-definition").textContent = card.definition;

            const text = card.reason;
            if (text.startsWith("⚠️")) {
                reasonEl.innerHTML = `<span style="color:var(--color-forgot);">${this.escapeHtml(text)}</span>`;
            } else {
                reasonEl.textContent = text;
            }
        } catch (err) {
            reasonEl.innerHTML = '<span style="color:var(--color-forgot);">加载失败，请重试</span>';
            console.error("Explore failed:", err);
        }
    }

    async onRefreshExplore() {
        await this.loadExplore();
    }

    onExploreDeepDive() {
        if (this.exploreCard) {
            this.openDeepDive(this.exploreCard);
        }
    }

    // ---- Add Concept Modal ----

    showModal() {
        document.getElementById("modal-overlay").style.display = "";
        this.switchAddMode("manual");
        document.getElementById("new-term").focus();
    }

    hideModal() {
        document.getElementById("modal-overlay").style.display = "none";
        document.getElementById("new-term").value = "";
        document.getElementById("new-definition").value = "";
        document.getElementById("new-category").value = "";
        document.getElementById("discover-industry").value = "";
        document.getElementById("discover-status").textContent = "";
        document.getElementById("discover-results").innerHTML = "";
        this.discoveredTerms = [];
    }

    switchAddMode(mode) {
        this.addMode = mode === "discover" ? "discover" : "manual";
        document.querySelectorAll(".add-mode-tab").forEach(tab => {
            tab.classList.toggle("active", tab.dataset.addMode === this.addMode);
        });
        document.getElementById("add-manual-pane").style.display = this.addMode === "manual" ? "" : "none";
        document.getElementById("add-discover-pane").style.display = this.addMode === "discover" ? "" : "none";
        document.getElementById("btn-save").style.display = this.addMode === "manual" ? "" : "none";
        document.getElementById("btn-import-discovered").style.display = this.addMode === "discover" ? "" : "none";
        if (this.addMode === "discover") document.getElementById("discover-industry").focus();
    }

    async onSaveConcept() {
        const term = document.getElementById("new-term").value.trim();
        const definition = document.getElementById("new-definition").value.trim();
        const category = document.getElementById("new-category").value.trim() || "自定义";
        if (!term || !definition) {
            if (!term) document.getElementById("new-term").style.borderColor = "var(--color-forgot)";
            if (!definition) document.getElementById("new-definition").style.borderColor = "var(--color-forgot)";
            setTimeout(() => {
                document.getElementById("new-term").style.borderColor = "";
                document.getElementById("new-definition").style.borderColor = "";
            }, 1500);
            return;
        }
        try {
            await api.add_concept(term, definition, category);
        } catch (err) {
            console.error("Failed to add concept:", err);
            return;
        }
        this.hideModal();
        await this.renderCategoryTabs();
        if (this.currentCategory === "全部" || this.currentCategory === category) {
            await this.refreshCards();
        }
        await this.updateStats();
    }

    async onDiscoverIndustryTerms() {
        const industry = document.getElementById("discover-industry").value.trim();
        const freshness = document.getElementById("discover-freshness").value;
        const status = document.getElementById("discover-status");
        const results = document.getElementById("discover-results");
        if (!industry) {
            document.getElementById("discover-industry").style.borderColor = "var(--color-forgot)";
            setTimeout(() => { document.getElementById("discover-industry").style.borderColor = ""; }, 1500);
            return;
        }
        status.className = "discover-status is-loading";
        status.textContent = "正在搜索网页并提取候选词...";

        results.innerHTML = "";
        this.discoveredTerms = [];
        document.getElementById("btn-discover-search").disabled = true;
        try {
            const response = await api.discover_industry_terms(industry, freshness);
            document.getElementById("btn-discover-search").disabled = false;
            if (!response?.ok) {
                status.className = "discover-status is-error";
                status.textContent = response?.error || "搜索失败，请重试。";
                return;
            }
            this.discoveredTerms = response.items || [];
            if (!this.discoveredTerms.length) {
                status.className = "discover-status is-empty";
                status.textContent = "没有找到足够可靠的候选词，可以换个行业词或扩大时间范围。";
                return;
            }
            status.className = "discover-status is-success";
            status.textContent = `找到 ${this.discoveredTerms.length} 个候选词，来自 ${response.source_count || 0} 条搜索结果。`;
            this.renderDiscoverResults();
        } catch (err) {
            document.getElementById("btn-discover-search").disabled = false;
            status.className = "discover-status is-error";
            status.textContent = "搜索失败" + (window.__API_MODE__ === "web" && !window.__DEMO_HAS_API__ ? "，服务端 AI 功能未配置，不影响基础复习功能。" : "，请检查网络和 API Key。")
            console.error("Discover failed:", err);
        }
    }

    renderDiscoverResults() {
        const results = document.getElementById("discover-results");
        results.innerHTML = this.discoveredTerms.map((item, index) => `
            <label class="discover-card">
                <input type="checkbox" class="discover-check" data-index="${index}">
                <div class="discover-card-body">
                    <div class="discover-card-head">
                        <span class="discover-term">${this.escapeHtml(item.term)}</span>
                        <span class="discover-confidence">${Math.round((item.confidence || 0) * 100)}%</span>
                    </div>
                    <div class="discover-definition">${this.escapeHtml(item.definition)}</div>
                    <div class="discover-meta">
                        <span>${this.escapeHtml(item.category || item.discovered_from || "自定义")}</span>
                        <span>${(item.source_urls || []).length} 个来源</span>
                    </div>
                    ${item.why_relevant ? `<div class="discover-reason">${this.escapeHtml(item.why_relevant)}</div>` : ""}
                </div>
            </label>
        `).join("");
    }

    async onImportDiscoveredTerms() {
        const selected = [...document.querySelectorAll(".discover-check:checked")]
            .map(input => this.discoveredTerms[parseInt(input.dataset.index, 10)])
            .filter(Boolean);
        const status = document.getElementById("discover-status");
        if (!selected.length) {
            status.className = "discover-status is-error";
            status.textContent = "请先勾选要加入的概念。";
            return;
        }
        document.getElementById("btn-import-discovered").disabled = true;
        status.className = "discover-status is-loading";
        status.textContent = "正在加入概念库...";
        try {
            const result = await api.import_discovered_terms(selected);
            document.getElementById("btn-import-discovered").disabled = false;
            if (!result?.ok) {
                status.className = "discover-status is-error";
                status.textContent = result?.error || "导入失败，请重试。";
                return;
            }
            status.className = "discover-status is-success";
            status.textContent = `已加入 ${result.count || 0} 个概念。`;
            const importedTerms = new Set((result.imported || []).map(item => item.term));
            this.discoveredTerms = this.discoveredTerms.filter(item => !importedTerms.has(item.term));
            this.renderDiscoverResults();
            await this.renderCategoryTabs();
            await this.updateStats();
            if (this.currentCategory === "全部") {
                this.currentCard = null;
                await this.refreshCards();
            }
        } catch (err) {
            document.getElementById("btn-import-discovered").disabled = false;
            status.className = "discover-status is-error";
            status.textContent = "导入失败，请重试。";
            console.error("Import discovered failed:", err);
        }
    }

    // ---- Settings ----

    async showSettings() {
        const overlay = document.getElementById("settings-overlay");
        const isWeb = window.__API_MODE__ === "fetch";
        try {
            const status = await api.get_config_status();
            if (isWeb && status.demo_mode) {
                document.getElementById("api-key-input").style.display = "none";
                document.getElementById("brave-key-input").style.display = "none";
                const apiStatusSpan = document.getElementById("api-key-status");
                const braveStatusSpan = document.getElementById("brave-key-status");
                apiStatusSpan.style.display = "";
                braveStatusSpan.style.display = "";
                apiStatusSpan.innerHTML = status.has_api_key
                    ? "\u2705 \u5df2\u914d\u7f6e\uff08\u670d\u52a1\u7aef\uff09"
                    : "\u23f8\ufe0f \u6f14\u793a\u6a21\u5f0f\uff0cAI \u529f\u80fd\u4ee5\u9884\u7f6e\u5185\u5bb9\u4e3a\u51c6";
                apiStatusSpan.style.color = status.has_api_key ? "var(--color-ok)" : "var(--color-forgot)";
                braveStatusSpan.innerHTML = status.has_brave_api_key_configured
                    ? "\u2705 \u5df2\u914d\u7f6e\uff08\u670d\u52a1\u7aef\uff09"
                    : "\u23f8\ufe0f \u6f14\u793a\u6a21\u5f0f\uff0c\u68c0\u7d22\u529f\u80fd\u672a\u542f\u7528";
                braveStatusSpan.style.color = status.has_brave_api_key_configured ? "var(--color-ok)" : "var(--color-forgot)";
                const title = overlay.querySelector(".modal-title");
                const copy = overlay.querySelector(".modal-copy");
                if (title) title.textContent = "\u6bd4\u8d5b\u6f14\u793a\u6a21\u5f0f";
                if (copy) copy.textContent = "\u672c\u9879\u76ee\u4e3a TRAE AI \u521b\u9020\u529b\u5927\u8d5b\u53c2\u8d5b\u4f5c\u54c1\uff0c\u65e0\u9700\u914d\u7f6e API Key \u5373\u53ef\u4f53\u9a8c\u5168\u90e8\u529f\u80fd\u3002";
                const saveBtn = document.getElementById("btn-settings-save");
                const cancelBtn = document.getElementById("btn-settings-cancel");
                if (saveBtn) saveBtn.style.display = "none";
                if (cancelBtn) cancelBtn.textContent = "\u5173\u95ed";
                overlay.style.display = "";
                return;
            }
        } catch (err) {}
        document.getElementById("api-key-input").style.display = "";
        document.getElementById("brave-key-input").style.display = "";
        document.getElementById("api-key-input").value = "";
        document.getElementById("brave-key-input").value = "";
        document.getElementById("api-key-status").style.display = "none";
        document.getElementById("brave-key-status").style.display = "none";
        const saveBtn = document.getElementById("btn-settings-save");
        const cancelBtn = document.getElementById("btn-settings-cancel");
        if (saveBtn) saveBtn.style.display = "";
        if (cancelBtn) cancelBtn.textContent = "\u53d6\u6d88";
        try {
            const status = await api.get_config_status();
            if (status.has_api_key) {
                document.getElementById("api-key-input").placeholder = "\u5df2\u914d\u7f6e\uff08\u8f93\u5165\u65b0 Key \u53ef\u66ff\u6362\uff09";
                document.getElementById("api-key-status").style.display = "";
            }
            if (status.has_brave_search_api_key) {
                document.getElementById("brave-key-input").placeholder = "\u5df2\u914d\u7f6e\uff08\u8f93\u5165\u65b0 Key \u53ef\u66ff\u6362\uff09";
                document.getElementById("brave-key-status").style.display = "";
            }
        } catch (err) {}
        overlay.style.display = "";
        document.getElementById("api-key-input").focus();
    }

    hideSettings() {
        document.getElementById("settings-overlay").style.display = "none";
    }

    async onSaveSettings() {
        const key = document.getElementById("api-key-input").value.trim();
        const braveKey = document.getElementById("brave-key-input").value.trim();
        if (!key && !braveKey) {
            document.getElementById("api-key-input").style.borderColor = "var(--color-forgot)";
            document.getElementById("brave-key-input").style.borderColor = "var(--color-forgot)";
            setTimeout(() => {
                document.getElementById("api-key-input").style.borderColor = "";
                document.getElementById("brave-key-input").style.borderColor = "";
            }, 1500);
            return;
        }
        if (key) {
            await api.set_api_key(key);
            document.getElementById("api-key-status").style.display = "";
            document.getElementById("api-key-input").value = "";
            document.getElementById("api-key-input").placeholder = "\u5df2\u4fdd\u5b58 \u2713";
        }
        if (braveKey) {
            await api.set_brave_search_api_key(braveKey);
            document.getElementById("brave-key-status").style.display = "";
            document.getElementById("brave-key-input").value = "";
            document.getElementById("brave-key-input").placeholder = "\u5df2\u4fdd\u5b58 \u2713";
        }
        setTimeout(() => this.hideSettings(), 800);
    }

    // ========================================
    //  Deep Dive Panel
    // ========================================

    async openDeepDive(card, options = {}) {
        const { fromRelation = false, restoreScrollTop = 0 } = options;
        const loadSeq = ++this.deepDiveLoadSeq;
        this.deepDiveCard = card;
        this.deepDivePayload = null;

        if (!fromRelation) {
            this.deepDiveReturnStack = [];
            this.deepDivePath = [card.term || card.id || "当前概念"];
        } else if (this.deepDivePath.length) {
            this.deepDivePath[this.deepDivePath.length - 1] = card.term || card.id || "当前概念";
        } else {
            this.deepDivePath = [card.term || card.id || "当前概念"];
        }
        this.syncDeepDivePathUI();
        this.hideTermPopover();
        this.hideLocalGraph();

        const overlay = document.getElementById("deep-dive-overlay");
        overlay.style.display = "";
        document.body.classList.add("deep-dive-open");

        this.switchDeepTab("article");
        this.resetDeepDiveQuiz(card);
        this.resetDeepDiveArticleState();
        await this.loadDeepDiveChat(card);

        try {
            const payload = await api.get_deep_dive_payload(card.id);
            if (loadSeq !== this.deepDiveLoadSeq) return;
            if (payload?.error === "not_found") throw new Error("not_found");

            this.deepDivePayload = payload;
            this.deepDiveCard = payload.card || card;
            if (this.deepDivePath.length) {
                this.deepDivePath[this.deepDivePath.length - 1] = this.deepDiveCard.term || card.term || card.id;
            } else {
                this.deepDivePath = [this.deepDiveCard.term || card.term || card.id];
            }
            this.syncDeepDivePathUI();
            this.resetDeepDiveQuiz(this.deepDiveCard);
            this.renderDeepDiveArticle(payload);

            if (restoreScrollTop > 0) {
                document.getElementById("tab-article").scrollTop = restoreScrollTop;
            }
        } catch (err) {
            if (loadSeq !== this.deepDiveLoadSeq) return;
            document.getElementById("article-loading").innerHTML = `<p style="color:var(--color-forgot)">加载失败` + (window.__API_MODE__ === "web" && !window.__DEMO_HAS_API__ ? "，服务端 AI 功能未配置" : "，请重试") + `</p>`;
            console.error("Deep dive payload failed:", err);
        }
        return;
    }

    closeDeepDive() {
        this.deepDiveLoadSeq += 1;
        document.getElementById("deep-dive-overlay").style.display = "none";
        document.body.classList.remove("deep-dive-open");
        this.deepDivePayload = null;
        this.deepDiveReturnStack = [];
        this.deepDivePath = [];
        this.hideTermPopover();
        this.hideLocalGraph();
        this.resetDeepDiveArticleState();
    }

    switchDeepTab(tab) {
        this.activeDeepTab = tab;
        document.querySelectorAll(".deep-tab").forEach(t => {
            t.classList.toggle("active", t.dataset.tab === tab);
        });
        document.getElementById("tab-article").style.display = tab === "article" ? "" : "none";
        document.getElementById("tab-quiz").style.display = tab === "quiz" ? "" : "none";
        document.getElementById("tab-chat").style.display = tab === "chat" ? "" : "none";
        if (tab === "quiz") this.syncQuizView();
    }

    resetDeepDiveQuiz(card) {
        this.quizIndex = 0;
        this.quizAnswered = [false, false, false];
        this.quizDrafts = ["", "", ""];
        this.quizQuestions = this.buildQuizQuestions(card);
        this.renderQuiz();
    }

    async loadDeepDiveChat(card) {
        const chatMessages = document.getElementById("chat-messages");
        chatMessages.innerHTML = `<div class="chat-msg chat-msg-system">
            围绕「<span id="chat-concept-name">${this.escapeHtml(card.term || card.id || "当前概念")}</span>」自由提问，我会尽力解答。        </div>`;
        document.getElementById("chat-input").value = "";
        this.chatHistory = [];

        try {
            const history = await api.get_chat_history(card.id);
            this.chatHistory = history || [];
            for (const msg of this.chatHistory) {
                this.addChatMessage(msg.role, msg.content);
            }
        } catch (err) {
            this.chatHistory = [];
            console.error("Failed to load chat history:", err);
        }
    }

    resetDeepDiveArticleState() {
        const loading = document.getElementById("article-loading");
        loading.style.display = "";
        loading.innerHTML = `
            <div class="loading-spinner"></div>
            <p>正在生成深度解读...</p>
        `;
        document.getElementById("article-navigation").style.display = "none";
        document.getElementById("article-prereq").style.display = "none";
        document.getElementById("article-relations").style.display = "none";
        document.getElementById("article-content").style.display = "none";
        document.getElementById("article-content").innerHTML = "";
        document.getElementById("article-prereq-list").innerHTML = "";
        document.getElementById("article-next-list").innerHTML = "";
        document.getElementById("article-confusion-list").innerHTML = "";
    }

    renderDeepDiveArticle(payload) {
        const articleHtml = this.renderMarkdown(payload?.article || "");
        const decoratedHtml = this.decorateInlineTerms(articleHtml, payload?.inline_terms || []);
        const hasRelations = Boolean((payload?.next_steps || []).length || (payload?.confusions || []).length);
        const hasGraph = Boolean(payload?.local_graph?.nodes?.length);

        document.getElementById("article-loading").style.display = "none";
        document.getElementById("article-navigation").style.display = "";
        document.getElementById("article-content").style.display = "";
        document.getElementById("article-content").innerHTML = decoratedHtml;
        document.getElementById("article-relations").style.display = hasRelations ? "" : "none";
        document.getElementById("btn-open-local-graph").style.display = hasGraph ? "" : "none";

        this.renderPrerequisites(payload?.prerequisites || []);
        this.renderRelationList("article-next-list", payload?.next_steps || [], "next");
        this.renderRelationList("article-confusion-list", payload?.confusions || [], "confusion");
        this.bindInlineTerms(payload?.inline_terms || []);
    }

    renderPrerequisites(rows) {
        const wrap = document.getElementById("article-prereq");
        const list = document.getElementById("article-prereq-list");
        if (!rows.length) {
            wrap.style.display = "none";
            list.innerHTML = "";
            return;
        }

        list.innerHTML = rows.map((row, index) => `
            <article class="article-prereq-item">
                <div class="article-prereq-index">${index + 1}</div>
                <div>
                    <h4 class="article-prereq-title">${this.escapeHtml(row.term)}</h4>
                    <p class="article-prereq-copy">${this.escapeHtml(row.reason || row.definition || "")}</p>
                    <button class="btn-ghost" type="button" data-open-concept="${this.escapeHtml(row.id)}">先看这个</button>
                </div>
            </article>
        `).join("");
        wrap.style.display = "";
        this.bindConceptOpeners(list, rows);
    }

    renderRelationList(containerId, rows, variant = "next") {
        const el = document.getElementById(containerId);
        const itemClass = variant === "confusion" ? "article-confusion-item" : "article-relation-item";
        const copyClass = variant === "confusion" ? "article-confusion-copy" : "article-relation-copy";
        if (!rows.length) {
            el.innerHTML = "";
            return;
        }

        el.innerHTML = rows.map((row) => `
            <article class="${itemClass}">
                <div class="article-relation-badge">${this.escapeHtml(row.relation_label || "")}</div>
                <h4 class="article-relation-title">${this.escapeHtml(row.term)}</h4>
                <p class="${copyClass}">${this.escapeHtml(row.reason || row.definition || "")}</p>
                <button class="btn-ghost" type="button" data-open-concept="${this.escapeHtml(row.id)}">去看这个概念</button>
            </article>
        `).join("");
        this.bindConceptOpeners(el, rows);
    }

    bindConceptOpeners(root, rows) {
        const byId = Object.fromEntries(rows.map((row) => [row.id, row]));
        root.querySelectorAll("[data-open-concept]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const row = byId[btn.dataset.openConcept];
                this.openConceptFromRelation(row || { id: btn.dataset.openConcept });
            });
        });
    }

    decorateInlineTerms(html, rows) {
        if (!html || !rows.length) return html;

        const wrapper = document.createElement("div");
        wrapper.innerHTML = html;
        const sortedRows = [...rows].sort((a, b) => (b.term || "").length - (a.term || "").length);
        const walker = document.createTreeWalker(wrapper, NodeFilter.SHOW_TEXT, null);
        const textNodes = [];

        while (walker.nextNode()) {
            const node = walker.currentNode;
            const parentTag = node.parentElement?.tagName;
            if (!node.nodeValue?.trim()) continue;
            if (["BUTTON", "CODE", "PRE", "SCRIPT", "STYLE"].includes(parentTag)) continue;
            textNodes.push(node);
        }

        textNodes.forEach((node) => {
            const text = node.nodeValue;
            let cursor = 0;
            let fragment = null;

            while (cursor < text.length) {
                let matchedRow = null;
                let matchedIndex = text.length;

                for (const row of sortedRows) {
                    const term = row.term || "";
                    if (!term) continue;
                    const index = text.indexOf(term, cursor);
                    if (index !== -1 && index < matchedIndex) {
                        matchedIndex = index;
                        matchedRow = row;
                    }
                }

                if (!matchedRow) break;
                if (!fragment) fragment = document.createDocumentFragment();
                if (matchedIndex > cursor) {
                    fragment.appendChild(document.createTextNode(text.slice(cursor, matchedIndex)));
                }

                const button = document.createElement("button");
                button.type = "button";
                button.className = "inline-term article-inline-term";
                button.dataset.inlineTerm = matchedRow.id;
                button.textContent = matchedRow.term;
                fragment.appendChild(button);

                cursor = matchedIndex + matchedRow.term.length;
            }

            if (!fragment) return;
            if (cursor < text.length) {
                fragment.appendChild(document.createTextNode(text.slice(cursor)));
            }
            node.parentNode.replaceChild(fragment, node);
        });

        return wrapper.innerHTML;
    }

    bindInlineTerms(rows) {
        const byId = Object.fromEntries(rows.map((row) => [row.id, row]));
        document.querySelectorAll("[data-inline-term]").forEach((btn) => {
            btn.addEventListener("click", (event) => {
                event.stopPropagation();
                const row = byId[btn.dataset.inlineTerm];
                if (row) this.showTermPopover(event.currentTarget, row);
            });
        });
    }

    showTermPopover(anchor, row) {
        const popover = document.getElementById("term-popover");
        const host = document.getElementById("tab-article");
        const safeHint = row.hint
            ? `<p class="article-relation-copy"><strong>提示：</strong>${this.escapeHtml(row.hint)}</p>`
            : "";
        const safeDifference = row.difference
            ? `<p class="article-relation-copy"><strong>关键区别：</strong>${this.escapeHtml(row.difference)}</p>`
            : "";

        popover.innerHTML = `
            <div class="article-kicker">${this.escapeHtml(row.relation_label || "关联概念")}</div>
            <h4 class="article-section-title">${this.escapeHtml(row.term)}</h4>
            <p class="article-relation-copy">${this.escapeHtml(row.definition || "")}</p>
            <p class="article-relation-copy">${this.escapeHtml(row.reason || "")}</p>
            ${safeHint}
            ${safeDifference}
            <button class="btn-ghost" id="term-popover-open" type="button">去看这个概念</button>
        `;

        popover.setAttribute("aria-hidden", "false");
        popover.style.left = "0px";
        popover.style.top = "0px";

        const anchorRect = anchor.getBoundingClientRect();
        const hostRect = host.getBoundingClientRect();
        const popoverWidth = Math.min(320, Math.max(220, host.clientWidth - 24));
        const rawLeft = anchorRect.left - hostRect.left + host.scrollLeft;
        const maxLeft = Math.max(12, host.clientWidth - popoverWidth - 12);
        const left = Math.max(12, Math.min(rawLeft, maxLeft));
        const top = anchorRect.bottom - hostRect.top + host.scrollTop + 10;

        popover.style.left = `${left}px`;
        popover.style.top = `${top}px`;
        document.getElementById("term-popover-open").onclick = () => this.openConceptFromRelation(row);
    }

    hideTermPopover() {
        const popover = document.getElementById("term-popover");
        popover.setAttribute("aria-hidden", "true");
        popover.innerHTML = "";
    }

    showLocalGraph() {
        const sheet = document.getElementById("local-graph-sheet");
        const nodes = this.deepDivePayload?.local_graph?.nodes || [];
        if (!nodes.length) {
            this.hideLocalGraph();
            return;
        }

        sheet.innerHTML = `
            <div class="article-section-head article-section-head-between">
                <div>
                    <div class="article-kicker">当前局部关联</div>
                    <h3 class="article-section-title">围绕这个概念继续串起来学</h3>
                </div>
                <button class="btn-ghost" id="btn-close-local-graph" type="button">收起</button>
            </div>
            <div class="article-relation-list" id="local-graph-list">
                ${nodes.map((row) => `
                    <article class="article-relation-item">
                        <div class="article-relation-badge">${this.escapeHtml(row.relation_label || "")}</div>
                        <h4 class="article-relation-title">${this.escapeHtml(row.term)}</h4>
                        <p class="article-relation-copy">${this.escapeHtml(row.reason || row.definition || "")}</p>
                        <button class="btn-ghost" type="button" data-open-concept="${this.escapeHtml(row.id)}">去看这个概念</button>
                    </article>
                `).join("")}
            </div>
        `;
        sheet.setAttribute("aria-hidden", "false");
        document.getElementById("btn-close-local-graph").addEventListener("click", () => this.hideLocalGraph());
        this.bindConceptOpeners(document.getElementById("local-graph-list"), nodes);
    }

    hideLocalGraph() {
        const sheet = document.getElementById("local-graph-sheet");
        sheet.setAttribute("aria-hidden", "true");
        sheet.innerHTML = "";
    }

    openConceptFromRelation(row) {
        if (!row?.id) return;
        const articlePane = document.getElementById("tab-article");
        if (this.deepDiveCard) {
            this.deepDiveReturnStack.push({
                card: this.deepDiveCard,
                scrollTop: articlePane?.scrollTop || 0,
            });
        }

        this.deepDivePath.push(row.term || row.id);
        this.hideTermPopover();
        this.hideLocalGraph();
        this.openDeepDive(this.resolveConceptCard(row), { fromRelation: true });
    }

    goBackDeepDiveConcept() {
        const previous = this.deepDiveReturnStack.pop();
        if (!previous) return;
        if (this.deepDivePath.length > 1) {
            this.deepDivePath.pop();
        }
        this.hideTermPopover();
        this.hideLocalGraph();
        this.openDeepDive(previous.card, {
            fromRelation: true,
            restoreScrollTop: previous.scrollTop || 0,
        });
    }

    resolveConceptCard(row) {
        const pools = [
            this.deepDivePayload?.card,
            ...(this.cards || []),
            this.currentCard,
            this.exploreCard,
            this.deepDiveCard,
        ].filter(Boolean);
        const found = pools.find((item) => item.id === row.id);
        if (found) return found;
        return {
            id: row.id,
            term: row.term || row.id,
            definition: row.definition || "",
            category: row.category || "",
        };
    }

    syncDeepDivePathUI() {
        const title = document.getElementById("deep-dive-concept-title");
        const currentLabel = this.deepDiveCard?.term || this.deepDivePath[this.deepDivePath.length - 1] || "当前概念";
        title.textContent = currentLabel;
        if (this.deepDivePath.length > 1) {
            title.title = `当前路径：${this.deepDivePath.join(" → ")}\n点击返回上一个概念`;
            title.style.cursor = "pointer";
        } else {
            title.title = currentLabel;
            title.style.cursor = "";
        }
    }

    buildQuizQuestions(card) {
        const term = card?.term || "这个概念";
        const safeTerm = this.escapeHtml(term);
        const definition = this.escapeHtml(card?.definition || "它的定义");
        return [
            {
                prompt: `1. 用你自己的话说清楚：什么是「${term}」？`,
                tip: "尽量不用原文照抄，先讲你真正理解的意思。",
                answer: `参考答案：\n\n- 先用一句白话解释「${safeTerm}」\n- 再补上它最关键的特征\n- 你也可以把这个概念和日常场景联系起来\n\n卡片原始定义：\n> ${definition}`
            },
            {
                prompt: `2. 「${term}」最容易和什么混淆？它们差在哪？`,
                tip: "先想一个最像的概念，再说出 1 个关键区别。",
                answer: "参考答案：\n\n- 先写出最容易混淆的相邻概念\n- 再说它们在定义、场景或结果上的一个核心差别\n- 如果说得出来一个「不是它」的例子，就说明你理解得更深了"
            },
            {
                prompt: `3. 给一个具体场景：什么时候你会用到「${term}」？`,
                tip: "把概念放进真实生活、工作或学习场景里。",
                answer: "参考答案：\n\n- 描述一个真实场景\n- 说明这个概念在那个场景里怎么起作用\n- 最后用一句话总结：为什么这个概念有用？"
            }
        ];
    }

    renderQuiz() {
        const questions = this.quizQuestions;
        const current = questions[this.quizIndex];
        if (!current) return;
        document.getElementById("quiz-title").textContent = this.deepDiveCard?.term || "自测";
        document.getElementById("quiz-progress").textContent = `${this.quizIndex + 1} / ${questions.length}`;
        document.getElementById("quiz-question-index").textContent = `问题 ${this.quizIndex + 1}`;
        document.getElementById("quiz-question").textContent = current.prompt;
        document.getElementById("quiz-question-tip").textContent = current.tip;
        document.getElementById("quiz-input").value = this.quizDrafts[this.quizIndex] || "";
        document.getElementById("quiz-answer-panel").style.display = "none";
        document.getElementById("quiz-reveal").textContent = this.quizAnswered[this.quizIndex] ? "重新查看答案" : "查看答案";
        document.getElementById("quiz-prev").disabled = this.quizIndex === 0;
        document.getElementById("quiz-next").disabled = this.quizIndex === questions.length - 1;
        document.getElementById("quiz-reveal").disabled = false;
    }

    syncQuizView() {
        const current = this.quizQuestions[this.quizIndex];
        if (!current) return;
        document.getElementById("quiz-title").textContent = this.deepDiveCard?.term || "自测";
        document.getElementById("quiz-progress").textContent = `${this.quizIndex + 1} / ${this.quizQuestions.length}`;
        document.getElementById("quiz-question-index").textContent = `问题 ${this.quizIndex + 1}`;
        document.getElementById("quiz-question").textContent = current.prompt;
        document.getElementById("quiz-question-tip").textContent = current.tip;
        document.getElementById("quiz-reveal").textContent = this.quizAnswered[this.quizIndex] ? "重新查看答案" : "查看答案";
        document.getElementById("quiz-prev").disabled = this.quizIndex === 0;
        document.getElementById("quiz-next").disabled = this.quizIndex === this.quizQuestions.length - 1;
    }

    onQuizInput() {
        const text = document.getElementById("quiz-input").value.trim();
        this.quizDrafts[this.quizIndex] = text;
        if (document.getElementById("quiz-answer-panel").style.display !== "none") {
            document.getElementById("quiz-user-answer").textContent = text || "";
        }
    }

    revealQuizAnswer() {
        const answer = document.getElementById("quiz-input").value.trim();
        document.getElementById("quiz-answer-panel").style.display = "";
        document.getElementById("quiz-user-answer").textContent = answer || "";
        document.getElementById("quiz-answer-content").innerHTML = this.renderMarkdown(this.quizQuestions[this.quizIndex].answer);
        this.quizAnswered[this.quizIndex] = true;
        document.getElementById("quiz-reveal").textContent = "重新查看答案";
    }

    switchQuiz(delta) {
        const next = this.quizIndex + delta;
        if (next < 0 || next >= this.quizQuestions.length) return;
        this.quizIndex = next;
        this.renderQuiz();
    }

    // ---- Simple Markdown Renderer ----

    renderMarkdown(text) {
        if (text.startsWith("⚠️")) {
            return `<div style="color:var(--color-forgot);text-align:center;padding:40px 0;">${this.escapeHtml(text)}</div>`;
        }

        let html = text.replace(/^---\s*/gm, "").trim();
        const firstHeadingIndex = html.indexOf("## ");
        if (firstHeadingIndex > 0) {
            html = html.slice(firstHeadingIndex);
        }

        // Headings
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');

        // Bold and italic
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Blockquote
        html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
        html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

        // Unordered lists
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)\n(?!<li>)/g, '$1</ul>');
        // Wrap list items in <ul>
        html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, (match) => {
            if (!match.includes('</ul>')) return '<ul>' + match + '</ul>';
            return match;
        });

        // Paragraphs: wrap lines not already wrapped in tags
        const lines = html.split('\n');
        const result = [];
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) { result.push(''); continue; }
            if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<li') ||
                trimmed.startsWith('</ul') || trimmed.startsWith('<blockquote') || trimmed.startsWith('<div')) {
                result.push(line);
                continue;
            }
            result.push('<p>' + line + '</p>');
        }
        return result.join('\n');
    }

    // ---- Chat ----

    async sendChatMessage() {
        const input = document.getElementById("chat-input");
        const question = input.value.trim();
        if (!question) return;

        const sendBtn = document.getElementById("chat-send");
        input.disabled = true;
        sendBtn.disabled = true;

        // Add user message
        this.addChatMessage("user", question);
        input.value = "";

        // Show typing indicator
        const typingId = this.addTypingIndicator();

        try {
            const answer = await api.ask_question(
                this.deepDiveCard ? this.deepDiveCard.id : "",
                question,
                this.chatHistory
            );

            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            // Add to history
            this.chatHistory.push(
                { role: "user", content: question },
                { role: "assistant", content: answer }
            );

            // Persist to backend
            this.saveChatHistory();

            // Add AI response
            this.addChatMessage("ai", answer);
        } catch (err) {
            this.removeTypingIndicator(typingId);
            this.addChatMessage("ai", "抱歉，请求失败" + (window.__API_MODE__ === "web" && !window.__DEMO_HAS_API__ ? "，服务端 AI 功能未配置" : "，请重试") + "。");
            console.error("Chat failed:", err);
        }

        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }

    addChatMessage(role, content) {
        const container = document.getElementById("chat-messages");
        const div = document.createElement("div");
        div.className = `chat-msg chat-msg-${role}`;
        if (role === "ai") {
            div.innerHTML = this.renderChatContent(content);
        } else {
            div.textContent = content;
        }
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div.id;
    }

    renderChatContent(text) {
        return this.renderMarkdown(text);
    }

    addTypingIndicator() {
        const id = "typing-" + Date.now();
        const container = document.getElementById("chat-messages");
        const div = document.createElement("div");
        div.className = "chat-typing-indicator";
        div.id = id;
        div.innerHTML = "<span></span><span></span><span></span>";
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    async saveChatHistory() {
        if (!this.deepDiveCard) return;
        try {
            await api.save_chat_history(this.deepDiveCard.id, this.chatHistory);
        } catch (err) {
            console.error("Failed to save chat history:", err);
        }
    }

    async clearChatHistory() {
        if (!this.deepDiveCard) return;
        try {
            await api.clear_chat_history(this.deepDiveCard.id);
        } catch (err) {
            console.error("Failed to clear chat history:", err);
        }
        this.chatHistory = [];
        const container = document.getElementById("chat-messages");
        container.innerHTML = `<div class="chat-msg chat-msg-system">
            围绕「<span id="chat-concept-name">${this.escapeHtml(this.deepDiveCard.term)}</span>」自由提问，我会尽力解答。
        </div>`;
    }

    // ---- Analytics ----

    async loadHeatmap() {
        const grid = document.getElementById("heatmap-grid");
        grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-tertiary);">加载中...</div>';
        try {
            const stats = await api.get_daily_stats(90);
            const today = new Date(); today.setHours(0, 0, 0, 0);
            const end = new Date(today);
            if (end.getDay() !== 0) end.setDate(end.getDate() + (7 - end.getDay()));
            const start = new Date(end);
            start.setDate(start.getDate() - 12 * 7 + 1);
            const dow = start.getDay();
            if (dow !== 1) start.setDate(start.getDate() + (dow === 0 ? -6 : 1 - dow));

            const weeks = [];
            const cur = new Date(start);
            while (cur <= end) {
                const week = [];
                for (let d = 0; d < 7; d++) {
                    const key = cur.toISOString().slice(0, 10);
                    week.push({ date: key, count: stats[key] || 0, inRange: cur <= today });
                    cur.setDate(cur.getDate() + 1);
                }
                weeks.push(week);
            }

            const dowLabels = ["一", "二", "三", "四", "五", "六", "日"];
            let html = '<div class="heatmap-months">';
            html += '<span style="width:13px;flex-shrink:0;margin-right:3px;"></span>';

            let lastMonth = "";
            const monthSpans = [];
            for (let wi = 0; wi < weeks.length; wi++) {
                const midDay = weeks[wi][3].date;
                const dt = new Date(midDay + "T00:00:00");
                const m = dt.getMonth() + 1;
                if (m !== lastMonth) {
                    monthSpans.push({ month: dt.getFullYear() + "年" + m + "月", start: wi });
                    lastMonth = m;
                }
            }
            const cellW = 16;
            for (let i = 0; i < monthSpans.length; i++) {
                const span = monthSpans[i];
                const endCol = i + 1 < monthSpans.length ? monthSpans[i + 1].start : weeks.length;
                const width = (endCol - span.start) * cellW - 3;
                html += `<span class="heatmap-month" style="width:${width}px">${span.month}</span>`;
            }
            html += '</div>';

            for (let dow = 0; dow < 7; dow++) {
                html += '<div class="heatmap-row">';
                html += `<span class="heatmap-dow">${dowLabels[dow]}</span>`;
                for (const week of weeks) {
                    const day = week[dow];
                    if (!day.inRange) {
                        html += '<span class="heatmap-day" style="visibility:hidden"></span>';
                    } else {
                        let level = 0;
                        if (day.count > 0) level = 1;
                        if (day.count >= 3) level = 2;
                        if (day.count >= 6) level = 3;
                        if (day.count >= 10) level = 4;
                        const clickable = day.count > 0 ? ' heatmap-day-clickable' : '';
                        html += `<span class="heatmap-day l${level}${clickable}" data-date="${day.date}" title="${day.date}: ${day.count} 次复习${day.count > 0 ? '，点击查看详情' : ''}"></span>`;
                    }
                }
                html += '</div>';
            }

            grid.innerHTML = html || '<div style="text-align:center;padding:40px;color:var(--text-tertiary);">暂无学习数据，开始复习吧。</div>';

            grid.querySelectorAll(".heatmap-day-clickable").forEach(cell => {
                cell.addEventListener("click", () => {
                    this.timelineFilter = cell.dataset.date;
                    this.switchAnalyticsTab("timeline");
                });
            });
        } catch (err) {
            grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--color-forgot);">加载失败</div>';
            console.error("Heatmap failed:", err);
        }
    }

    async loadDashboard() {
        const container = document.getElementById("dash-cards");
        container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-tertiary);">加载中...</div>';
        try {
            const stats = await api.get_category_stats();
            if (!stats.length) {
                container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-tertiary);">暂无数据</div>';
                return;
            }
            const icons = {
                "AI": `
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <rect x="6" y="6" width="12" height="12" rx="3" stroke="currentColor" stroke-width="1.8"/>
                        <path d="M9.5 12h5M12 9.5v5M8 3.5v2M16 3.5v2M8 18.5v2M16 18.5v2M3.5 8h2M18.5 8h2M3.5 16h2M18.5 16h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                `,
                "金融": `
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="M4 19.5h16M7 16V9M12 16V5M17 16v-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                        <path d="M15.5 7.5 19 4m0 0h-3m3 0v3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                `,
                "哲学": `
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="M6 20h12M8 20v-2.5c0-1 .8-1.8 1.8-1.8h4.4c1 0 1.8.8 1.8 1.8V20M9 8.5c0-2.2 1.8-4 4-4s4 1.8 4 4c0 1.5-.8 2.8-2 3.5v1.2c0 .4-.3.8-.8.8h-4.4c-.4 0-.8-.3-.8-.8V12c-1.2-.7-2-2-2-3.5Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                `
            };
            const iconClass = (cat) => {
                if (cat === "AI") return "ai";
                if (cat === "金融") return "finance";
                return "philosophy";
            };
            let html = "";
            for (const s of stats) {
                const mastered = s.total - s.due;
                const pct = s.total > 0 ? Math.round((mastered / s.total) * 100) : 0;
                html += `<div class="dash-card">
                    <div class="dash-card-icon ${iconClass(s.category)}">${icons[s.category] || `
                        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <path d="M6.5 5.5h9a2 2 0 0 1 2 2v11H8.8a2.3 2.3 0 0 0-2.3 2.3V7.5a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
                            <path d="M8.5 8.5h6M8.5 12h6M8.5 15.5H13" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
                        </svg>
                    `}</div>
                    <div class="dash-card-body">
                        <div class="dash-card-category">${this.escapeHtml(s.category)}</div>
                        <div class="dash-card-meta">
                            <span class="dash-stat">总计 <strong>${s.total}</strong> 张</span>
                            <span class="dash-stat">待复习 <strong>${s.due}</strong></span>
                            <span class="dash-stat">今日已复习 <strong>${s.reviewed_today}</strong></span>
                            <span class="dash-stat">平均掌握度 <strong>${s.avg_ease.toFixed(1)}</strong></span>
                        </div>
                    </div>
                    <div class="dash-card-bar-wrap">
                        <div class="dash-card-bar-label">已掌握 ${pct}%</div>
                        <div class="dash-card-bar"><div class="dash-card-bar-fill" style="width:${pct}%"></div></div>
                    </div>
                </div>`;
            }
            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--color-forgot);">加载失败</div>';
            console.error("Dashboard failed:", err);
        }
    }

    async loadTimeline() {
        const container = document.getElementById("timeline-list");
        container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-tertiary);">加载中...</div>';
        try {
            const log = await api.get_review_log(200);
            let filtered = log;
            if (this.timelineFilter) {
                filtered = log.filter(e => e.date === this.timelineFilter);
            }
            if (!filtered.length) {
                const msg = this.timelineFilter
                    ? `${this.timelineFilter} 当天没有学习记录`
                    : "还没有学习记录";
                container.innerHTML = `<div class="timeline-empty">${msg}<br><br>${
                    this.timelineFilter ? '<button class="timeline-clear-filter" id="timeline-clear-filter">返回全部时间线</button>' : "开始复习第一张卡片吧。"
                }</div>`;
                if (this.timelineFilter) {
                    document.getElementById("timeline-clear-filter").addEventListener("click", () => {
                        this.timelineFilter = null;
                        this.loadTimeline();
                    });
                }
                return;
            }
            let html = "";
            if (this.timelineFilter) {
                html += `<div class="timeline-filter-bar">
                    ${this.timelineFilter} · ${filtered.length} 次复习                    <button class="timeline-clear-filter" id="timeline-clear-filter">返回全部</button>
                </div>`;
            }
            let lastDate = "";
            const qLabel = { 1: "忘了", 3: "不太熟", 5: "记住了" };
            for (const entry of filtered) {
                if (entry.date !== lastDate) {
                    if (!this.timelineFilter) {
                        html += `<div class="timeline-date-header">${entry.date}</div>`;
                    }
                    lastDate = entry.date;
                }
                const q = entry.quality;
                html += `<div class="timeline-item">
                    <span class="timeline-quality q${q}">${qLabel[q] || q}</span>
                    <span class="timeline-term">${this.escapeHtml(entry.term)}</span>
                    <span class="timeline-cat">${this.escapeHtml(entry.category)}</span>
                </div>`;
            }
            container.innerHTML = html;
            if (this.timelineFilter) {
                document.getElementById("timeline-clear-filter").addEventListener("click", () => {
                    this.timelineFilter = null;
                    this.loadTimeline();
                });
            }
        } catch (err) {
            container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--color-forgot);">加载失败</div>';
            console.error("Timeline failed:", err);
        }
    }

    async loadHistory() {
        const grid = document.getElementById("history-grid");
        grid.innerHTML = '<div class="history-empty">加载中...</div>';
        try {
            const cards = await api.get_recent_cards(30);
            if (!cards.length) {
                grid.innerHTML = '<div class="history-empty">还没有学习记录<br><br>开始复习第一张卡片吧。</div>';
                return;
            }
            const qLabel = { 1: "忘了", 3: "不太熟", 5: "记住了" };
            let html = "";
            for (const c of cards) {
                const q = c.last_quality;
                html += `<div class="history-card" data-card-id="${c.id}">
                    <button class="history-card-del" data-card-id="${c.id}" title="删除卡片">×</button>
                    <div class="history-card-term">${this.escapeHtml(c.term)}</div>
                    <div class="history-card-meta">
                        <span class="history-card-cat">${this.escapeHtml(c.category)}</span>
                        <span class="history-card-date">${c.last_review}</span>
                        <span class="history-card-quality q${q}" title="${qLabel[q]}">${qLabel[q] ? qLabel[q][0] : q}</span>
                    </div>
                </div>`;
            }
            grid.innerHTML = html;

            grid.querySelectorAll(".history-card").forEach(card => {
                card.addEventListener("click", (e) => {
                    if (e.target.closest(".history-card-del")) return;
                    const cid = card.dataset.cardId;
                    const found = cards.find(c => c.id === cid);
                    if (found) {
                        document.getElementById("analytics-view").style.display = "none";
                        this.deepDiveCard = { id: found.id, term: found.term, definition: found.definition, category: found.category };
                        this.openDeepDive(this.deepDiveCard);
                    }
                });
            });

            grid.querySelectorAll(".history-card-del").forEach(btn => {
                btn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    const cid = btn.dataset.cardId;
                    const card = cards.find(c => c.id === cid);
                    if (!card) return;
                    if (!confirm(`确定要删除「${card.term}」吗？\n\n此操作不可撤销。`)) return;
                    await api.delete_card(cid);
                    await this.renderCategoryTabs();
                    await this.updateStats();
                    this.loadHistory();
                });
            });
        } catch (err) {
            grid.innerHTML = '<div class="history-empty" style="color:var(--color-forgot);">加载失败</div>';
            console.error("History cards failed:", err);
        }
    }

    escapeHtml(text) {
        const d = document.createElement("div");
        d.textContent = text;
        return d.innerHTML;
    }

    // ========================================
    //  Star Map
    // ========================================

    async renderStarMap() {
        const overview = document.getElementById("starmap-overview");
        const galaxy = document.getElementById("starmap-galaxy");
        const tooltip = document.getElementById("starmap-tooltip");
        if (!overview || !galaxy) return;
        if (!this._starmapBound) this._bindStarMapEvents();

        this.currentGalaxy = null;
        overview.style.display = "";
        overview.style.opacity = "1";
        overview.style.transform = "scale(1)";
        galaxy.style.display = "none";
        galaxy.classList.remove("entering", "galaxy-formed");
        if (tooltip) tooltip.style.display = "none";
        await this._loadGalaxyOverview();
    }

    _bindStarMapEvents() {
        this._starmapBound = true;
        document.querySelectorAll(".galaxy-entry").forEach((entry) => {
            entry.addEventListener("click", () => this.enterGalaxy(entry.dataset.cat));
        });
        const backBtn = document.getElementById("starmap-back");
        if (backBtn) {
            backBtn.addEventListener("click", () => this._returnToOverview());
        }
    }

    async _loadGalaxyOverview() {
        let state;
        try { state = await api.get_galaxy_state(); }
        catch (e) { return; }
        if (!state || !state.length) return;

        for (const g of state) {
            if (g.category === "思辨") continue;
            const entryId = "entry-" + (g.category === "金融" ? "finance" : g.category === "哲学" ? "philosophy" : "AI");
            const el = document.getElementById(entryId);
            if (!el) continue;
            const progEl = document.getElementById(entryId + "-progress");
            if (progEl) progEl.textContent = `${g.lit}/${g.total} 点亮`;
            el.classList.remove("progress-mid", "progress-high", "formed");
            if (g.formed) el.classList.add("formed");
            else if (g.progress >= 0.3) el.classList.add("progress-high");
            else if (g.progress > 0) el.classList.add("progress-mid");
        }
    }

    async enterGalaxy(cat) {
        if (this.currentGalaxy === cat) return;
        const overview = document.getElementById("starmap-overview");
        const galaxy = document.getElementById("starmap-galaxy");
        const tooltip = document.getElementById("starmap-tooltip");
        if (!overview || !galaxy) return;
        this.currentGalaxy = cat;
        if (tooltip) tooltip.style.display = "none";

        overview.style.opacity = "0";
        overview.style.transform = "scale(0.95)";

        galaxy.style.display = "";
        galaxy.classList.remove("entering");
        void galaxy.offsetWidth;
        galaxy.classList.add("entering");

        await this._renderGalaxyStars(cat);

        setTimeout(() => { overview.style.display = "none"; }, 300);
    }

    _returnToOverview() {
        const overview = document.getElementById("starmap-overview");
        const galaxy = document.getElementById("starmap-galaxy");
        const tooltip = document.getElementById("starmap-tooltip");
        if (!overview || !galaxy) return;
        this.currentGalaxy = null;
        galaxy.style.display = "none";
        galaxy.classList.remove("entering", "galaxy-formed");
        overview.style.display = "";
        overview.style.opacity = "1";
        overview.style.transform = "scale(1)";
        if (tooltip) tooltip.style.display = "none";
    }

    async _renderGalaxyStars(cat) {
        const svg = document.getElementById("starmap-svg");
        const container = document.getElementById("starmap-galaxy");
        if (!svg || !container) return;

        let sm;
        try {
            sm = await api.get_star_map(cat);
        } catch (err) {
            svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#6b7280" font-size="14">加载失败</text>';
            return;
        }

        let galaxyState = null;
        try {
            const gs = await api.get_galaxy_state();
            galaxyState = gs.find(g => g.category === cat);
        } catch (e) {}

        const { stars, links } = sm;
        const width = container.clientWidth || 750;
        const height = container.clientHeight || 520;
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.innerHTML = "";
        const NS = "http://www.w3.org/2000/svg";

        this._computeSolarLayout(stars, width, height);

        if (galaxyState?.formed) {
            container.classList.add("galaxy-formed");
            const ringGroup = document.createElementNS(NS, "g");
            const cx = width / 2, cy = height / 2;
            [70, 130, 195, 255].forEach(r => {
                const circ = document.createElementNS(NS, "circle");
                circ.setAttribute("cx", cx); circ.setAttribute("cy", cy);
                circ.setAttribute("r", r); circ.setAttribute("class", "orbit-ring");
                ringGroup.appendChild(circ);
            });
            svg.appendChild(ringGroup);
        } else {
            container.classList.remove("galaxy-formed");
        }

        if (!stars.some((star) => star.is_core)) {
            const placeholder = document.createElementNS(NS, "circle");
            placeholder.setAttribute("cx", width / 2);
            placeholder.setAttribute("cy", height / 2);
            placeholder.setAttribute("r", 10);
            placeholder.setAttribute("fill", "none");
            placeholder.setAttribute("stroke", "rgba(168,200,255,0.25)");
            placeholder.setAttribute("stroke-width", "1");
            placeholder.setAttribute("stroke-dasharray", "3 4");
            placeholder.setAttribute("opacity", "0.55");
            svg.appendChild(placeholder);
        }

        const linkGroup = document.createElementNS(NS, "g");
        for (const link of links) {
            const s = this.starPositions[link.source], t = this.starPositions[link.target];
            if (!s || !t) continue;
            const line = document.createElementNS(NS, "line");
            line.setAttribute("x1", s.x); line.setAttribute("y1", s.y);
            line.setAttribute("x2", t.x); line.setAttribute("y2", t.y);
            let cls = "starmap-link";
            if (link.cross_category) cls += " cross";
            else if (cat === "AI") cls += " cat-ai";
            else if (cat === "哲学") cls += " cat-philosophy";
            else if (cat === "金融") cls += " cat-finance";
            line.setAttribute("class", cls);
            linkGroup.appendChild(line);
        }
        svg.appendChild(linkGroup);

        const starGroup = document.createElementNS(NS, "g");
        const R = { 0: 4, 1: 5, 2: 6.5, 3: 8 };
        for (const star of stars) {
            const pos = this.starPositions[star.id];
            if (!pos) continue;
            const g = document.createElementNS(NS, "g");
            g.setAttribute("class", "star-node");
            g.setAttribute("transform", `translate(${pos.x}, ${pos.y})`);
            g.setAttribute("data-sid", star.id);

            const hit = document.createElementNS(NS, "circle");
            hit.setAttribute("r", 14);
            hit.setAttribute("class", "star-hit");
            hit.addEventListener("click", () => this.showStarDetail(star.id));
            hit.addEventListener("mouseenter", () => g.classList.add("is-hovered"));
            hit.addEventListener("mouseleave", () => g.classList.remove("is-hovered"));
            g.appendChild(hit);

            const r = R[star.level] || 4;
            const circle = document.createElementNS(NS, "circle");
            circle.setAttribute("r", r);
            circle.setAttribute("data-sid", star.id);
            circle.setAttribute("data-level", star.level);
            let cls = `star-circle star-l${star.level}`;
            if (star.is_core) cls += " is-core";
            if (star.dimmed) cls += " star-dim";
            circle.setAttribute("class", cls);
            g.appendChild(circle);

            if (star.level === 3) {
                const sb = document.createElementNS(NS, "g");
                sb.setAttribute("class", "star-starburst");
                [[-12,0,12,0],[0,-12,0,12],[-8,-8,8,8],[-8,8,8,-8]].forEach(([x1,y1,x2,y2]) => {
                    const ln = document.createElementNS(NS, "line");
                    ln.setAttribute("x1", x1); ln.setAttribute("y1", y1);
                    ln.setAttribute("x2", x2); ln.setAttribute("y2", y2);
                    sb.appendChild(ln);
                });
                g.appendChild(sb);
            }

            const label = document.createElementNS(NS, "text");
            label.setAttribute("y", r + 13);
            label.setAttribute("class", "star-label");
            label.textContent = star.term;
            g.appendChild(label);
            starGroup.appendChild(g);
        }
        svg.appendChild(starGroup);
    }

    _computeSolarLayout(stars, width, height) {
        const cx = width / 2, cy = height / 2;
        const core = stars.find(s => s.is_core);
        const rest = stars.filter(s => !s.is_core);
        const storageKey = `starPos_${this.currentGalaxy || "overview"}`;
        const cached = this._readStarLayoutCache(storageKey);
        const pos = {};
        if (core) pos[core.id] = { x: cx, y: cy };

        const ringR = { 3: 70, 2: 130, 1: 195, 0: 255 };
        const byRing = { 3: [], 2: [], 1: [], 0: [] };
        rest.forEach(s => byRing[s.level].push(s));
        for (const lv of [3, 2, 1, 0]) {
            const arr = byRing[lv], n = arr.length;
            arr.sort((a, b) => a.term.localeCompare(b.term, "zh-Hans-CN"));
            arr.forEach((s, i) => {
                const cachedPos = cached[s.id];
                if (cachedPos) {
                    pos[s.id] = cachedPos;
                    return;
                }
                const ang = (i / Math.max(n, 1)) * Math.PI * 2 + lv * 0.68;
                pos[s.id] = { x: Math.round(cx + ringR[lv] * Math.cos(ang)),
                              y: Math.round(cy + ringR[lv] * Math.sin(ang)) };
            });
        }
        this.starPositions = pos;
        this._writeStarLayoutCache(storageKey, pos);
    }

    _readStarLayoutCache(storageKey) {
        try {
            const raw = localStorage.getItem(storageKey);
            return raw ? JSON.parse(raw) : {};
        } catch (err) {
            return {};
        }
    }

    _writeStarLayoutCache(storageKey, positions) {
        try {
            localStorage.setItem(storageKey, JSON.stringify(positions));
        } catch (err) {}
    }

    async showStarDetail(conceptId) {
        this.selectedStarId = conceptId;
        const tooltip = document.getElementById("starmap-tooltip");
        if (!tooltip) return;

        let detail;
        try {
            detail = await api.get_star_detail(conceptId);
        } catch (err) {
            console.error("Failed to load star detail:", err);
            return;
        }
        if (!detail) return;

        const levelNames = { 0: "暗星", 1: "亮星", 2: "燃星", 3: "超新星" };
        const levelName = levelNames[detail.level] || "?";

        let eventsHtml = "";
        for (const ev of detail.events) {
            const dateStr = ev.date || "-";
            eventsHtml += `<div class="star-event"><span class="star-event-date">${dateStr}</span><span class="star-event-label">${this.escapeHtml(ev.label)}</span></div>`;
        }

        tooltip.innerHTML = `
            <button class="tooltip-close" id="star-tooltip-close">&times;</button>
            <div class="star-title">${this.escapeHtml(detail.term)}</div>
            <div class="star-cat">${this.escapeHtml(detail.category)}</div>
            <div class="star-level l${detail.level}">${levelName}${detail.dimmed ? " · 暗淡" : ""}</div>
            ${detail.next_hint ? `<div class="star-hint">${detail.next_hint}</div>` : ""}
            <div class="star-events">${eventsHtml}</div>
            <button class="btn-review-star" id="btn-review-star">复习这张卡片</button>
        `;
        tooltip.style.display = "";

        document.getElementById("star-tooltip-close").addEventListener("click", () => {
            tooltip.style.display = "none";
            this.selectedStarId = null;
        });
        document.getElementById("btn-review-star").addEventListener("click", () => {
            const targetTab = document.querySelector(`.tab[data-category="${detail.category}"]`)
                || document.querySelector('.tab[data-category="全部"]');
            if (targetTab) this.onTabClick(targetTab);
            tooltip.style.display = "none";
        });
    }

    // ---- Star Animation ----

    _triggerStarIgnite(conceptId, newLevel) {
        const svg = document.getElementById("starmap-svg");
        if (!svg) return;
        const circle = svg.querySelector(`circle.star-circle[data-sid="${conceptId}"]`);
        if (!circle) return;

        const isFirstLight = newLevel === 1;
        const animClass = isFirstLight ? "star-ignite" : "star-upgrade";

        circle.classList.add(animClass);
        circle.addEventListener("animationend", () => {
            circle.classList.remove("star-ignite", "star-upgrade");
        }, { once: true });
    }

    // ---- Collision Toast ----

    async checkCollision() {
        try {
            const result = await api.get_collisions();
            if (!result) return;
            this._showToast(`概念碰撞：${result.a} × ${result.b} - ${result.text.substring(0, 60)}...`);
        } catch (err) {
            console.error("Collision check failed:", err);
        }
    }

    _showToast(message) {
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.className = "toast-container";
            document.body.appendChild(container);
        }
        const div = document.createElement("div");
        div.className = "toast-msg";
        div.textContent = message;
        container.appendChild(div);
        setTimeout(() => div.remove(), 5200);
    }
}

// ===== Bootstrap =====

(async function waitForApi() {
    let attempts = 0;
    while (!window.api) {
        if (attempts++ > 50) {
            console.error("API not available after 5s (mode=" + window.__API_MODE__ + ")");
            document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#999;">应用加载失败，请刷新重试</div>';
            return;
        }
        await new Promise(r => setTimeout(r, 100));
    }

    const app = new ConceptReviewer();
    await app.init();
})();