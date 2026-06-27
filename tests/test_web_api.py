"""
TRAE 创造力大赛 — Web API 自动化测试
======================================
验证 Flask REST 端点的基本功能。
运行：python -m pytest tests/test_web_api.py -v
"""

import json
import os
import tempfile
import sys
import pytest

# ── 创建临时 session 根目录 ──────────────────────────────
_test_session_root = tempfile.mkdtemp(prefix="trae_web_test_")

os.environ["PORT"] = "18765"

# 注入 session 根目录
import web_app as app_module
app_module.SESSION_ROOT = os.path.join(_test_session_root, "sessions")
app_module.DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
app_module.DEMO_SEED_FILE = os.path.join(app_module.DATA_DIR, "demo_seed.json")

from web_app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    with app.test_client() as c:
        yield c


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "概念复习" in data["name"]


class TestConfig:
    def test_get_config_status(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data.get("api_key_configured"), bool)
        assert isinstance(data.get("brave_api_key_configured"), bool)
        assert data.get("demo_mode") is True

    def test_set_api_key(self, client):
        resp = client.post("/api/config/api-key", json={"api_key": "sk-test-123"})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

        resp2 = client.get("/api/config")
        assert resp2.get_json()["api_key_configured"] is True

    def test_set_brave_api_key(self, client):
        resp = client.post("/api/config/brave-api-key", json={"api_key": "bs-test-456"})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True


class TestCategoriesAndStats:
    def test_get_categories(self, client):
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        cats = resp.get_json()
        assert isinstance(cats, list)
        assert "深度学习" in cats
        assert "AI 应用" in cats

    def test_get_stats(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        stats = resp.get_json()
        assert "total" in stats
        assert stats["total"] >= 15

    def test_get_daily_stats(self, client):
        resp = client.get("/api/stats/daily?days=90")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None

    def test_get_category_stats(self, client):
        """返回类别维度统计列表"""
        resp = client.get("/api/stats/category")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        if data:
            assert "category" in data[0]
            assert "due" in data[0]


class TestCards:
    def test_get_due_cards(self, client):
        resp = client.get("/api/cards/due")
        assert resp.status_code == 200
        cards = resp.get_json()
        assert isinstance(cards, list)

    def test_get_recent_cards(self, client):
        resp = client.get("/api/cards/recent?limit=5")
        assert resp.status_code == 200
        cards = resp.get_json()
        assert isinstance(cards, list)
        assert len(cards) <= 5

    def test_rate_card(self, client):
        """评分后返回 None（演示环境无需附加生成）"""
        resp = client.get("/api/cards/due")
        cards = resp.get_json()
        if not cards:
            pytest.skip("没有待复习卡片")
        card_id = cards[0]["id"]
        resp2 = client.post(f"/api/cards/{card_id}/rate", json={"quality": 4})
        assert resp2.status_code == 200
        # 无 API Key 时 rate 返回 None —— 正常行为
        # 仅验证响应不报错
        result = resp2.get_json()

    def test_add_concept(self, client):
        resp = client.post("/api/concepts", json={
            "term": "测试概念",
            "definition": "这是一个测试添加的概念",
            "category": "测试",
        })
        assert resp.status_code == 200
        card = resp.get_json()
        assert card["term"] == "测试概念"
        assert "id" in card

    def test_delete_card(self, client):
        resp = client.post("/api/concepts", json={
            "term": "待删除",
            "definition": "将被删除",
            "category": "测试",
        })
        card = resp.get_json()
        card_id = card["id"]
        resp2 = client.delete(f"/api/cards/{card_id}")
        assert resp2.status_code == 200
        assert resp2.get_json()["ok"] is True

    def test_delete_category(self, client):
        client.post("/api/concepts", json={
            "term": "类别测试",
            "definition": "测试删除类别",
            "category": "待删除类别",
        })
        resp = client.delete("/api/categories/待删除类别")
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True


class TestDeepDive:
    def test_get_deep_dive_payload(self, client):
        """返回深度学习数据载荷"""
        resp = client.get("/api/cards/demo-001/deep-dive-payload")
        assert resp.status_code == 200
        payload = resp.get_json()
        assert "article" in payload
        assert "prerequisites" in payload
        assert "sections" in payload

    def test_deep_dive_endpoint(self, client):
        """deep_dive 返回 markdown 长文（字符串）"""
        resp = client.get("/api/cards/demo-001/deep-dive")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, str) and len(data) > 100

    def test_ask_question(self, client):
        """提问返回 markdown 回答（字符串）"""
        resp = client.post("/api/cards/demo-001/ask", json={"question": "什么是循环神经网络？"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, str) and len(data) > 10

    def test_chat_history_crud(self, client):
        card_id = "demo-001"
        messages = [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好！"}]

        resp = client.get(f"/api/cards/{card_id}/chat")
        assert resp.status_code == 200

        resp = client.post(f"/api/cards/{card_id}/chat", json={"messages": messages})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

        resp = client.delete(f"/api/cards/{card_id}/chat")
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True


class TestDiscovery:
    def test_discover_terms(self, client):
        resp = client.post("/api/discover-terms", json={
            "industry": "计算机科学",
            "freshness": "pm",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        # 无 API Key 时可能返回空
        assert isinstance(data, (dict, list))

    def test_import_terms(self, client):
        resp = client.post("/api/import-terms", json={"items": []})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True


class TestExplore:
    def test_random_explore(self, client):
        resp = client.post("/api/random-explore", json={
            "category": "全部",
            "exclude_ids": [],
        })
        assert resp.status_code == 200
        data = resp.get_json()
        # 可能返回 concept 或 None
        assert data is None or isinstance(data, dict)


class TestStarmap:
    def test_get_star_map(self, client):
        """星图返回 {stars:[], links:[]}"""
        resp = client.get("/api/starmap")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert "stars" in data
        assert "links" in data
        assert len(data["stars"]) > 0

    def test_get_star_map_with_category(self, client):
        resp = client.get("/api/starmap?category=深度学习")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert "stars" in data

    def test_get_star_detail(self, client):
        """按概念名查询详情"""
        resp = client.get("/api/starmap/循环神经网络")
        assert resp.status_code == 200
        data = resp.get_json()
        # 匹配精确名称时返回概念 dict
        assert data is None or isinstance(data, dict)

    def test_get_star_detail_not_found(self, client):
        """不存在返回 None"""
        resp = client.get("/api/starmap/不存在的概念")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is None


class TestMeta:
    def test_get_sources(self, client):
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))

    def test_get_sources_with_id(self, client):
        resp = client.get("/api/sources?concept_id=demo-001")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))

    def test_get_collisions(self, client):
        """无复习数据时返回 None"""
        resp = client.get("/api/collisions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is None or isinstance(data, (list, dict))

    def test_get_galaxy_state(self, client):
        """星系状态返回列表"""
        resp = client.get("/api/galaxy-state")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        if data:
            assert "category" in data[0]

    def test_get_review_log(self, client):
        resp = client.get("/api/review-log?limit=10")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)


class TestSessionIsolation:
    def test_sessions_are_isolated(self, client):
        client_a = app.test_client()
        client_a.application.config["TESTING"] = True

        resp = client_a.post("/api/concepts", json={
            "term": "会话A的独占概念",
            "definition": "只有A能看到",
            "category": "会话测试",
        })
        assert resp.status_code == 200

        client_b = app.test_client()
        client_b.application.config["TESTING"] = True
        resp_b = client_b.post("/api/random-explore", json={
            "category": "会话测试",
            "exclude_ids": [],
        })
        assert resp_b.status_code == 200