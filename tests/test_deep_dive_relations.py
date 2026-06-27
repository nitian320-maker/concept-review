import tempfile
import types
import sys
import unittest

from backend import Backend

sys.modules.setdefault("webview", types.SimpleNamespace())

from main import Api


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
                    {"id": "demand", "relation": "prerequisite", "strength": -0.2},
                    {"id": "deflation", "relation": "extends"},
                    {"id": "inflation", "relation": "similar", "strength": 1.8},
                    {"id": "liquidity_trap", "relation": "extends"},
                    {"id": "policy", "relation": "mystery"},
                    {"id": "missing", "relation": "extends"},
                    {"id": "demand", "relation": "contrast"},
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
            {
                "id": "policy",
                "term": "政策",
                "definition": "对全局经济进行调节的手段",
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
        self.assertEqual(by_id["inflation"]["strength"], 1.0)

    def test_normalize_relations_falls_back_unknown_relation_to_extends(self):
        rows = self.backend._normalize_relations(self.backend.concepts[0])
        policy = next(row for row in rows if row["id"] == "policy")
        self.assertEqual(policy["relation"], "extends")
        self.assertEqual(policy["relation_label"], "相关扩展")

    def test_normalize_relations_fills_missing_reason_hint_strength(self):
        rows = self.backend._normalize_relations(self.backend.concepts[0])
        demand = next(row for row in rows if row["id"] == "demand")
        self.assertTrue(demand["reason"])
        self.assertTrue(demand["hint"])

    def test_normalize_relations_skips_invalid_self_and_duplicate_ids(self):
        rows = self.backend._normalize_relations(self.backend.concepts[0])
        ids = [row["id"] for row in rows]
        self.assertEqual(ids, ["demand", "inflation", "liquidity_trap", "policy"])
        self.assertNotIn("deflation", ids)
        self.assertNotIn("missing", ids)
        self.assertEqual(next(row for row in rows if row["id"] == "demand")["strength"], 0.0)

    def test_normalize_relations_prefers_higher_priority_duplicate_relation(self):
        self.backend.concepts[0]["related_concepts"] = [
            {"id": "demand", "relation": "extends", "strength": 1.0},
            {"id": "demand", "relation": "contrast", "strength": 0.9},
            {"id": "demand", "relation": "prerequisite", "strength": 0.1},
        ]
        rows = self.backend._normalize_relations(self.backend.concepts[0])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "demand")
        self.assertEqual(rows[0]["relation"], "prerequisite")

    def test_normalize_relations_uses_strength_tiebreak_for_duplicate_relation(self):
        self.backend.concepts[0]["related_concepts"] = [
            {"id": "demand", "relation": "extends", "strength": 0.2},
            {"id": "demand", "relation": "extends", "strength": 0.8},
        ]
        rows = self.backend._normalize_relations(self.backend.concepts[0])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["strength"], 0.8)


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
                    "通货紧缩是整体物价持续下降，并压制消费和投资。\n\n"
                    "## 核心定义拆解\n"
                    "当总需求不足时，物价会下行，企业利润受压。\n\n"
                    "## 底层机制\n"
                    "总需求走弱会让企业降价，若公众预期通货膨胀继续回落，消费会推迟。"
                    "在流动性陷阱里，货币政策刺激也可能失灵。\n\n"
                    "## 相邻概念对比\n"
                    "它和通货膨胀方向相反，但都与宏观需求和预期有关。"
                ),
                "deep_article_version": 2,
                "related_concepts": [
                    {"id": "demand", "relation": "prerequisite"},
                    {"id": "credit", "relation": "prerequisite"},
                    {"id": "inflation", "relation": "similar"},
                    {"id": "liquidity_trap", "relation": "extends"},
                    {"id": "debt", "relation": "extends"},
                    {"id": "expectation", "relation": "prerequisite"},
                    {"id": "output_gap", "relation": "extends"},
                    {"id": "stagflation", "relation": "contrast"},
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
                "id": "credit",
                "term": "信用收缩",
                "definition": "融资能力下降导致支出收缩",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "inflation",
                "term": "通货膨胀",
                "definition": "整体物价持续上升",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "liquidity_trap",
                "term": "流动性陷阱",
                "definition": "低利率下货币政策传导失灵",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "debt",
                "term": "债务通缩",
                "definition": "债务负担因价格下降而加重",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "expectation",
                "term": "通缩预期",
                "definition": "公众预期未来价格继续下降",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "output_gap",
                "term": "产出缺口",
                "definition": "实际产出低于潜在产出",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "stagflation",
                "term": "滞胀",
                "definition": "经济停滞与高通胀并存",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
            },
            {
                "id": "isolated",
                "term": "孤立概念",
                "definition": "没有任何关联概念",
                "category": "金融",
                "created_at": "2026-06-20T10:00:00",
                "deep_article": "# 一句话讲清\n孤立概念只用来测试空关系。",
                "deep_article_version": 2,
                "related_concepts": [],
            },
            {
                "id": "api",
                "term": "API",
                "definition": "接口",
                "category": "技术",
                "created_at": "2026-06-20T10:00:00",
            },
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_deep_dive_payload_returns_card_prerequisites_and_sections(self):
        payload = self.backend.get_deep_dive_payload("deflation")
        self.assertEqual(payload["card"]["id"], "deflation")
        self.assertEqual(payload["card"]["term"], "通货紧缩")
        self.assertEqual(payload["card"]["definition"], "整体物价持续下降")
        self.assertEqual(payload["card"]["category"], "金融")
        self.assertIn("article", payload)
        self.assertTrue(payload["article"].startswith("# 一句话讲清"))
        self.assertIn("sections", payload)
        self.assertGreaterEqual(len(payload["sections"]), 3)
        self.assertEqual(payload["sections"][0]["title"], "一句话讲清")
        self.assertIn("prerequisites", payload)
        self.assertEqual([row["id"] for row in payload["prerequisites"]], ["demand", "credit"])
        self.assertEqual(payload["local_graph"]["center"]["id"], "deflation")
        self.assertLessEqual(len(payload["local_graph"]["nodes"]), 7)

    def test_inline_terms_are_selected_from_article_text_and_capped(self):
        payload = self.backend.get_deep_dive_payload("deflation")
        inline_terms = payload["inline_terms"]
        self.assertLessEqual(len(inline_terms), 6)
        self.assertEqual([row["term"] for row in inline_terms], ["总需求", "通货膨胀", "流动性陷阱"])
        for row in inline_terms:
            self.assertIn(row["term"], payload["article"])
            self.assertIn(row["relation"], {"prerequisite", "confusable", "extends"})

    def test_payload_returns_empty_navigation_lists_when_no_relations_exist(self):
        payload = self.backend.get_deep_dive_payload("isolated")
        self.assertEqual(payload["prerequisites"], [])
        self.assertEqual(payload["next_steps"], [])
        self.assertEqual(payload["confusions"], [])
        self.assertEqual(payload["inline_terms"], [])
        self.assertEqual(payload["local_graph"]["nodes"], [])

    def test_get_deep_dive_payload_returns_not_found_error_for_missing_card(self):
        self.assertEqual(self.backend.get_deep_dive_payload("missing-id"), {"error": "not_found"})

    def test_warning_article_uses_empty_article_text_for_derived_fields(self):
        self.backend.concepts[0]["deep_article"] = "stale article"
        self.backend.concepts[0]["deep_article_version"] = 0
        self.backend._call_deepseek = lambda messages, stream=False: "⚠️ API unavailable"

        payload = self.backend.get_deep_dive_payload("deflation")

        self.assertEqual(payload["article"], "⚠️ API unavailable")
        self.assertEqual(payload["sections"], [])
        self.assertEqual(payload["inline_terms"], [])
        self.assertEqual([row["id"] for row in payload["prerequisites"]], ["demand", "credit"])
        self.assertEqual([row["id"] for row in payload["confusions"]], ["inflation", "stagflation"])
        self.assertEqual([row["id"] for row in payload["next_steps"]], ["liquidity_trap", "debt"])

    def test_inline_term_matching_avoids_ascii_partial_word_matches(self):
        self.backend.concepts[0]["deep_article"] = (
            "# 一句话讲清\n"
            "This article mentions apis and capability, but not the standalone target term.\n\n"
            "## 核心定义拆解\n"
            "这里没有独立出现那个 ASCII 术语。"
        )
        self.backend.concepts[0]["related_concepts"] = [{"id": "api", "relation": "extends"}]

        payload = self.backend.get_deep_dive_payload("deflation")

        self.assertEqual(payload["inline_terms"], [])


class ApiSeamTests(unittest.TestCase):
    def test_get_deep_dive_payload_forwards_to_backend(self):
        expected = {"card": {"id": "x"}}

        class StubBackend:
            def __init__(self):
                self.calls = []

            def get_deep_dive_payload(self, card_id):
                self.calls.append(card_id)
                return expected

        backend = StubBackend()
        api = Api(backend)

        result = api.get_deep_dive_payload("deflation")

        self.assertEqual(result, expected)
        self.assertEqual(backend.calls, ["deflation"])


if __name__ == "__main__":
    unittest.main()
