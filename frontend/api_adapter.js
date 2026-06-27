/**
 * api_adapter.js — 统一 API 适配层
 * =================================
 * 在桌面版下代理到 window.pywebview.api，
 * 在网页版下使用 fetch 调用 Flask REST 端点。
 *
 * 用法：window.api.xxx(...) 替代 window.pywebview.api.xxx(...)
 * app.js 无需大改，只需做全局替换即可。
 */

(function () {
  "use strict";

  // ── 模式检测 ──────────────────────────────────────────
  const isPyWebView = typeof window.pywebview !== "undefined" && window.pywebview.api;

  // ── Web 模式下的 fetch 封装 ────────────────────────────
  async function _get(path) {
    const resp = await fetch(path);
    if (!resp.ok) throw new Error(`GET ${path} → ${resp.status}`);
    return resp.json();
  }

  async function _post(path, body) {
    const resp = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`POST ${path} → ${resp.status}`);
    return resp.json();
  }

  async function _delete(path) {
    const resp = await fetch(path, { method: "DELETE" });
    if (!resp.ok) throw new Error(`DELETE ${path} → ${resp.status}`);
    return resp.json();
  }

  // ── 统一 API 对象 ──────────────────────────────────────
  const api = {};

  // ── 配置 ──────────────────────────────────────────────
  api.get_config_status = function () {
    if (isPyWebView) return window.pywebview.api.get_config_status();
    return _get("/api/config");
  };

  api.set_api_key = function (key) {
    if (isPyWebView) return window.pywebview.api.set_api_key(key);
    return _post("/api/config/api-key", { api_key: key });
  };

  api.set_brave_search_api_key = function (key) {
    if (isPyWebView) return window.pywebview.api.set_brave_search_api_key(key);
    return _post("/api/config/brave-api-key", { api_key: key });
  };

  // ── 目录/统计 ─────────────────────────────────────────
  api.get_categories = function () {
    if (isPyWebView) return window.pywebview.api.get_categories();
    return _get("/api/categories");
  };

  api.get_stats = function () {
    if (isPyWebView) return window.pywebview.api.get_stats();
    return _get("/api/stats");
  };

  api.get_daily_stats = function (days) {
    if (isPyWebView) return window.pywebview.api.get_daily_stats(days);
    return _get(`/api/stats/daily?days=${days}`);
  };

  api.get_category_stats = function () {
    if (isPyWebView) return window.pywebview.api.get_category_stats();
    return _get("/api/stats/category");
  };

  api.get_review_log = function (limit) {
    if (isPyWebView) return window.pywebview.api.get_review_log(limit);
    return _get(`/api/review-log?limit=${limit}`);
  };

  // ── 卡片 ──────────────────────────────────────────────
  api.get_due_cards = function () {
    if (isPyWebView) return window.pywebview.api.get_due_cards();
    return _get("/api/cards/due");
  };

  api.get_recent_cards = function (limit) {
    if (isPyWebView) return window.pywebview.api.get_recent_cards(limit);
    return _get(`/api/cards/recent?limit=${limit}`);
  };

  api.rate_card = function (card_id, quality) {
    if (isPyWebView) return window.pywebview.api.rate_card(card_id, quality);
    return _post(`/api/cards/${encodeURIComponent(card_id)}/rate`, { quality: quality });
  };

  api.add_concept = function (term, definition, category) {
    if (isPyWebView) return window.pywebview.api.add_concept(term, definition, category);
    return _post("/api/concepts", { term: term, definition: definition, category: category });
  };

  api.delete_card = function (card_id) {
    if (isPyWebView) return window.pywebview.api.delete_card(card_id);
    return _delete(`/api/cards/${encodeURIComponent(card_id)}`);
  };

  api.delete_category = function (category_name) {
    if (isPyWebView) return window.pywebview.api.delete_category(category_name);
    return _delete(`/api/categories/${encodeURIComponent(category_name)}`);
  };

  // ── 深度学习 ──────────────────────────────────────────
  api.deep_dive = function (card_id) {
    if (isPyWebView) return window.pywebview.api.deep_dive(card_id);
    return _get(`/api/cards/${encodeURIComponent(card_id)}/deep-dive`);
  };

  api.get_deep_dive_payload = function (card_id) {
    if (isPyWebView) return window.pywebview.api.get_deep_dive_payload(card_id);
    return _get(`/api/cards/${encodeURIComponent(card_id)}/deep-dive-payload`);
  };

  api.ask_question = function (card_id, question) {
    if (isPyWebView) return window.pywebview.api.ask_question(card_id, question);
    return _post(`/api/cards/${encodeURIComponent(card_id)}/ask`, { question: question });
  };

  api.get_chat_history = function (card_id) {
    if (isPyWebView) return window.pywebview.api.get_chat_history(card_id);
    return _get(`/api/cards/${encodeURIComponent(card_id)}/chat`);
  };

  api.save_chat_history = function (card_id, messages) {
    if (isPyWebView) return window.pywebview.api.save_chat_history(card_id, messages);
    return _post(`/api/cards/${encodeURIComponent(card_id)}/chat`, { messages: messages });
  };

  api.clear_chat_history = function (card_id) {
    if (isPyWebView) return window.pywebview.api.clear_chat_history(card_id);
    return _delete(`/api/cards/${encodeURIComponent(card_id)}/chat`);
  };

  // ── 行业探索 ──────────────────────────────────────────
  api.discover_industry_terms = function (industry, freshness) {
    if (isPyWebView) return window.pywebview.api.discover_industry_terms(industry, freshness);
    return _post("/api/discover-terms", { industry: industry, freshness: freshness });
  };

  api.import_discovered_terms = function (items) {
    if (isPyWebView) return window.pywebview.api.import_discovered_terms(items);
    return _post("/api/import-terms", { items: items });
  };

  // ── 探索 ──────────────────────────────────────────────
  api.random_explore = function (category, exclude_ids) {
    if (isPyWebView) return window.pywebview.api.random_explore(category, exclude_ids);
    return _post("/api/random-explore", { category: category, exclude_ids: exclude_ids });
  };

  // ── 星图 ──────────────────────────────────────────────
  api.get_star_map = function (category) {
    if (isPyWebView) return window.pywebview.api.get_star_map(category);
    const qs = category ? `?category=${encodeURIComponent(category)}` : "";
    return _get(`/api/starmap${qs}`);
  };

  api.get_star_detail = function (concept_name) {
    if (isPyWebView) return window.pywebview.api.get_star_detail(concept_name);
    return _get(`/api/starmap/${encodeURIComponent(concept_name)}`);
  };

  // ── 碰撞/来源/星系 ────────────────────────────────────
  api.get_collisions = function () {
    if (isPyWebView) return window.pywebview.api.get_collisions();
    return _get("/api/collisions");
  };

  api.get_sources = function (concept_id) {
    if (isPyWebView) return window.pywebview.api.get_sources(concept_id);
    return _get(`/api/sources?concept_id=${encodeURIComponent(concept_id)}`);
  };

  api.get_galaxy_state = function () {
    if (isPyWebView) return window.pywebview.api.get_galaxy_state();
    return _get("/api/galaxy-state");
  };

  // ── 健康检查（仅 Web 模式） ────────────────────────────
  api.health = function () {
    if (isPyWebView) return Promise.resolve({ status: "ok" });
    return _get("/api/health");
  };

  // ── 暴露全局 ──────────────────────────────────────────
  window.api = api;
  window.__API_MODE__ = isPyWebView ? "pywebview" : "fetch";
})();