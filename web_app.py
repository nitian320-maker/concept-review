"""
TRAE AI 创造力大赛 — 概念复习 Web 版 Demo
===========================================
Flask 网页入口：替代 pywebview 桌面壳，暴露 REST API 给前端。

实现方案（最小改动）：
  - 复用 backend.py 全部业务逻辑
  - 匿名会话隔离（cookie 级 session_id）
  - 演示数据自动播种
  - 所有请求/响应日志留痕 Trae
"""

import json
import os
import uuid
import logging
import shutil
import sys

from flask import (
    Flask,
    jsonify,
    request,
    session,
    send_from_directory,
    make_response,
)

# ── 项目根 ──────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(APP_DIR, "frontend")
DATA_DIR = os.path.join(APP_DIR, "data")
DEMO_SEED_FILE = os.path.join(DATA_DIR, "demo_seed.json")
SESSION_ROOT = os.path.join(APP_DIR, "web_sessions")

# 日志留痕
logging.basicConfig(
    level=logging.INFO,
    format="[TRAE-WEB] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(APP_DIR, "trae_web_session.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ── Flask app ───────────────────────────────────────────
app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path="",
)
app.secret_key = os.urandom(32).hex()


# ── 会话管理 ─────────────────────────────────────────────
def _get_session_dir() -> str:
    """根据 flask session 获得每个匿名用户的隔离数据目录"""
    if "session_id" not in session:
        session["session_id"] = uuid.uuid4().hex[:16]
    sid = session["session_id"]
    sdir = os.path.join(SESSION_ROOT, sid)
    os.makedirs(sdir, exist_ok=True)
    return sdir


def _get_config_file(session_dir: str) -> str:
    return os.path.join(session_dir, "config.json")


def _ensure_demo_seed(session_dir: str):
    """首次访问时自动播种演示数据"""
    concepts_file = os.path.join(session_dir, "concepts.json")
    review_log_file = os.path.join(session_dir, "review_log.json")
    config_file = _get_config_file(session_dir)

    # config 模板
    if not os.path.exists(config_file):
        default_config = {
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "brave_search_api_key": os.environ.get("BRAVE_SEARCH_API_KEY", ""),
            "demo_mode": True,
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

    # 演示数据
    if not os.path.exists(concepts_file) and os.path.exists(DEMO_SEED_FILE):
        shutil.copy2(DEMO_SEED_FILE, concepts_file)
        logger.info("已播种演示数据到 session %s", session.get("session_id"))
    if not os.path.exists(review_log_file):
        with open(review_log_file, "w", encoding="utf-8") as f:
            json.dump([], f)


def _get_backend():
    """延迟加载 Backend 实例（每次请求创建，数据文件从 session 目录读取）"""
    from backend import Backend

    sdir = _get_session_dir()
    _ensure_demo_seed(sdir)
    return Backend(data_dir=sdir, config_file=_get_config_file(sdir))


# ── API 路由 ─────────────────────────────────────────────


@app.route("/api/config", methods=["GET"])
def api_get_config_status():
    bk = _get_backend()
    api_configured = bool(bk.get_api_key())
    brave_configured = bool(bk.get_brave_search_api_key())
    return jsonify({
        "api_key_configured": api_configured,
        "brave_api_key_configured": brave_configured,
        "has_api_key": api_configured,
        "has_brave_search_api_key": brave_configured,
        "demo_mode": bk.config.get("demo_mode", False),
    })


@app.route("/api/config/api-key", methods=["POST"])
def api_set_api_key():
    data = request.get_json(force=True)
    key = data.get("api_key", "")
    bk = _get_backend()
    bk.set_api_key(key)
    return jsonify({"ok": True})


@app.route("/api/config/brave-api-key", methods=["POST"])
def api_set_brave_key():
    data = request.get_json(force=True)
    key = data.get("api_key", "")
    bk = _get_backend()
    bk.set_brave_search_api_key(key)
    return jsonify({"ok": True})


@app.route("/api/categories", methods=["GET"])
def api_get_categories():
    bk = _get_backend()
    return jsonify(bk.get_categories())


@app.route("/api/stats", methods=["GET"])
def api_get_stats():
    bk = _get_backend()
    return jsonify(bk.get_stats())


@app.route("/api/cards/due", methods=["GET"])
def api_get_due_cards():
    bk = _get_backend()
    return jsonify(bk.get_due_cards())


@app.route("/api/cards/recent", methods=["GET"])
def api_get_recent_cards():
    limit = int(request.args.get("limit", 30))
    bk = _get_backend()
    return jsonify(bk.get_recent_cards(limit))


@app.route("/api/cards/<card_id>/rate", methods=["POST"])
def api_rate_card(card_id: str):
    data = request.get_json(force=True)
    quality = data.get("quality", 3)
    bk = _get_backend()
    result = bk.rate_card(card_id, quality)
    return jsonify(result)


@app.route("/api/concepts", methods=["POST"])
def api_add_concept():
    data = request.get_json(force=True)
    bk = _get_backend()
    result = bk.add_concept(
        data.get("term", ""),
        data.get("definition", ""),
        data.get("category", "未分类"),
    )
    return jsonify(result)


@app.route("/api/cards/<card_id>/deep-dive", methods=["GET"])
def api_deep_dive(card_id: str):
    bk = _get_backend()
    return jsonify(bk.deep_dive(card_id))


@app.route("/api/cards/<card_id>/deep-dive-payload", methods=["GET"])
def api_get_deep_dive_payload(card_id: str):
    bk = _get_backend()
    return jsonify(bk.get_deep_dive_payload(card_id))


@app.route("/api/cards/<card_id>/ask", methods=["POST"])
def api_ask_question(card_id: str):
    data = request.get_json(force=True)
    question = data.get("question", "")
    bk = _get_backend()
    return jsonify(bk.ask_question(card_id, question))


@app.route("/api/cards/<card_id>/chat", methods=["GET"])
def api_get_chat_history(card_id: str):
    bk = _get_backend()
    return jsonify(bk.get_chat_history(card_id))


@app.route("/api/cards/<card_id>/chat", methods=["POST"])
def api_save_chat_history(card_id: str):
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    bk = _get_backend()
    bk.save_chat_history(card_id, messages)
    return jsonify({"ok": True})


@app.route("/api/cards/<card_id>/chat", methods=["DELETE"])
def api_clear_chat_history(card_id: str):
    bk = _get_backend()
    bk.clear_chat_history(card_id)
    return jsonify({"ok": True})


@app.route("/api/cards/<card_id>", methods=["DELETE"])
def api_delete_card(card_id: str):
    bk = _get_backend()
    bk.delete_card(card_id)
    return jsonify({"ok": True})


@app.route("/api/categories/<path:category_name>", methods=["DELETE"])
def api_delete_category(category_name: str):
    bk = _get_backend()
    bk.delete_category(category_name)
    return jsonify({"ok": True})


@app.route("/api/discover-terms", methods=["POST"])
def api_discover_terms():
    data = request.get_json(force=True)
    bk = _get_backend()
    return jsonify(bk.discover_industry_terms(
        data.get("industry", ""),
        data.get("freshness", "pm"),
    ))


@app.route("/api/import-terms", methods=["POST"])
def api_import_terms():
    data = request.get_json(force=True)
    bk = _get_backend()
    bk.import_discovered_terms(data.get("items", []))
    return jsonify({"ok": True})


@app.route("/api/random-explore", methods=["POST"])
def api_random_explore():
    data = request.get_json(force=True) or {}
    bk = _get_backend()
    return jsonify(bk.random_explore(
        data.get("category", "全部"),
        data.get("exclude_ids"),
    ))


@app.route("/api/stats/daily", methods=["GET"])
def api_get_daily_stats():
    days = int(request.args.get("days", 90))
    bk = _get_backend()
    return jsonify(bk.get_daily_stats(days))


@app.route("/api/stats/category", methods=["GET"])
def api_get_category_stats():
    bk = _get_backend()
    return jsonify(bk.get_category_stats())


@app.route("/api/review-log", methods=["GET"])
def api_get_review_log():
    limit = int(request.args.get("limit", 50))
    bk = _get_backend()
    return jsonify(bk.get_review_log(limit))


@app.route("/api/starmap", methods=["GET"])
def api_get_star_map():
    category = request.args.get("category", "全部")
    bk = _get_backend()
    return jsonify(bk.get_star_map(category))


@app.route("/api/starmap/<concept_name>", methods=["GET"])
def api_get_star_detail(concept_name: str):
    bk = _get_backend()
    return jsonify(bk.get_star_detail(concept_name))


@app.route("/api/collisions", methods=["GET"])
def api_get_collisions():
    bk = _get_backend()
    return jsonify(bk.get_collisions())


@app.route("/api/sources", methods=["GET"])
def api_get_sources():
    concept_id = request.args.get("concept_id", "")
    bk = _get_backend()
    return jsonify(bk.get_sources(concept_id))


@app.route("/api/galaxy-state", methods=["GET"])
def api_get_galaxy_state():
    bk = _get_backend()
    return jsonify(bk.get_galaxy_state())


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok", "name": "概念复习 Web Demo", "version": "1.0.0"})


# ── 前端 SPA fallback ──────────────────────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str):
    if path and os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index_web.html")


# ── 启动 ─────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("概念复习 Web Demo 启动中 ...")
    logger.info("前端目录: %s", FRONTEND_DIR)
    logger.info("会话根目录: %s", SESSION_ROOT)
    logger.info("演示数据: %s", DEMO_SEED_FILE)
    logger.info("=" * 60)

    port = int(os.environ.get("PORT", 8765))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)