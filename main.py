import os
import sys
import webview
from backend import Backend


class Api:
    """Methods exposed to JavaScript via pywebview.api"""

    def __init__(self, backend: Backend):
        self.backend = backend

    def get_due_cards(self, category: str = "全部") -> list:
        return self.backend.get_due_cards(category)

    def rate_card(self, card_id: str, quality: int):
        self.backend.rate_card(card_id, quality)

    def add_concept(self, term: str, definition: str, category: str) -> dict:
        return self.backend.add_concept(term, definition, category)

    def get_stats(self) -> dict:
        return self.backend.get_stats()

    def deep_dive(self, card_id: str) -> str:
        return self.backend.deep_dive(card_id)

    def get_deep_dive_payload(self, card_id: str) -> dict:
        return self.backend.get_deep_dive_payload(card_id)

    def ask_question(self, card_id: str, question: str, history: list | None = None) -> str:
        return self.backend.ask_question(card_id, question, history)

    def get_config_status(self) -> dict:
        has_key = bool(self.backend.get_api_key())
        has_brave_key = bool(self.backend.get_brave_search_api_key())
        return {"has_api_key": has_key, "has_brave_search_api_key": has_brave_key}

    def set_api_key(self, key: str):
        self.backend.set_api_key(key.strip())

    def set_brave_search_api_key(self, key: str):
        self.backend.set_brave_search_api_key(key.strip())

    def discover_industry_terms(self, industry: str, freshness: str = "pm") -> dict:
        return self.backend.discover_industry_terms(industry, freshness)

    def import_discovered_terms(self, items: list) -> dict:
        return self.backend.import_discovered_terms(items)

    def random_explore(self, category: str = "全部", exclude_ids: list | None = None) -> dict | None:
        return self.backend.random_explore(category, exclude_ids)

    def get_categories(self) -> list:
        return self.backend.get_categories()

    def get_chat_history(self, card_id: str) -> list:
        return self.backend.get_chat_history(card_id)

    def save_chat_history(self, card_id: str, history: list):
        self.backend.save_chat_history(card_id, history)

    def clear_chat_history(self, card_id: str):
        self.backend.clear_chat_history(card_id)

    def delete_category(self, category: str) -> int:
        return self.backend.delete_category(category)

    def get_daily_stats(self, days: int = 90) -> dict:
        return self.backend.get_daily_stats(days)

    def get_category_stats(self) -> list:
        return self.backend.get_category_stats()

    def get_review_log(self, limit: int = 50) -> list:
        return self.backend.get_review_log(limit)

    def get_recent_cards(self, limit: int = 30) -> list:
        return self.backend.get_recent_cards(limit)

    def delete_card(self, card_id: str) -> bool:
        return self.backend.delete_card(card_id)

    def get_star_map(self, category="全部"):
        return self.backend.get_star_map(category)

    def get_star_detail(self, concept_id):
        return self.backend.get_star_detail(concept_id)

    def generate_relations(self, concept_id=None):
        return self.backend.generate_relations(concept_id)

    def get_collisions(self):
        return self.backend.get_collisions()

    def get_sources(self, concept_id):
        return self.backend.get_sources(concept_id)

    def get_galaxy_state(self):
        return self.backend.get_galaxy_state()


def main():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(app_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    backend = Backend(data_dir)
    api = Api(backend)

    html_path = os.path.join(app_dir, "frontend", "index.html")

    window = webview.create_window(
        title="概念复习",
        url=html_path,
        js_api=api,
        width=1050,
        height=750,
        min_size=(800, 600),
        resizable=True,
        text_select=True,
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
