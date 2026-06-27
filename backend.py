import json
import os
import uuid
import random
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import date, datetime, timedelta


DEEP_ARTICLE_VERSION = 2
RELATION_ALIAS_MAP = {"similar": "confusable"}
RELATION_LABELS = {
    "prerequisite": "前置依赖",
    "confusable": "容易混淆",
    "extends": "相关扩展",
    "contrast": "对比关系",
}
RELATION_PRIORITY = {
    "prerequisite": 0,
    "confusable": 1,
    "contrast": 2,
    "extends": 3,
}


def _clamp_strength(value, fallback=0.5):
    try:
        strength = float(value)
    except (TypeError, ValueError):
        strength = fallback
    if strength < 0:
        return 0.0
    if strength > 1:
        return 1.0
    return strength


def compute_star_level(card, today):
    """返回 (level, dimmed)。level: 0暗星 1亮星 2燃星 3超新星；dimmed: 是否在遗忘中。"""
    has_chat = bool(card.get("chat_history"))
    reviewed = card.get("repetitions", 0) > 0 or card.get("last_review")
    interval = card.get("interval", 0)

    if has_chat and reviewed:
        level = 3                       # 超新星：问答过 + 学过
    elif reviewed and interval >= 3:
        level = 2                       # 燃星：SM-2 间隔 >= 3 天
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


PRELOADED_CONCEPTS = {
    "AI": [
        ("LLM", "大语言模型（Large Language Model），基于 Transformer 架构在海量文本上训练的巨型神经网络，能理解和生成自然语言。代表有 GPT-4、Claude、文心一言等。核心能力：文本生成、翻译、摘要、问答、代码编写。"),
        ("RAG", "检索增强生成（Retrieval-Augmented Generation），将信息检索系统与生成式 AI 结合的架构。先从一个知识库中检索相关文档，再把文档作为上下文喂给 LLM 生成答案。有效缓解大模型的\"幻觉\"问题，让回答有据可查。"),
        ("Transformer", "2017 年由 Google 提出的革命性神经网络架构，用自注意力机制（Self-Attention）取代了传统的循环和卷积结构。所有现代大语言模型（GPT、BERT、Claude）都基于它。核心创新：并行处理整个序列、捕捉长距离依赖。"),
        ("Fine-tuning", "微调。在预训练好的大模型基础上，用特定领域的小数据集进行二次训练，使模型适配专有任务。比如把通用 GPT 微调成医疗问诊模型。比从头训练成本低 1000 倍以上。方法包括全量微调、LoRA、Adapter 等。"),
        ("Embedding", "嵌入向量。将文字、图片等非结构化数据映射到高维向量空间中的数值表示。语义相近的内容在向量空间中距离也近。用于语义搜索、推荐系统、聚类分析。常用模型：text-embedding-3、bge-large-zh。"),
        ("Prompt Engineering", "提示工程。设计和优化输入给大模型的指令，以引导模型输出期望的结果。技巧包括：角色设定、少样本示例（Few-shot）、思维链（Chain-of-Thought）、结构化输出要求。本质是用自然语言给模型\"编程\"。"),
        ("Attention Mechanism", "注意力机制。让模型在处理序列数据时，能够动态地关注输入的不同部分，并为每个部分分配不同的权重。是 Transformer 的核心组件。自注意力（Self-Attention）让每个词都与序列中所有其他词建立关联。"),
        ("GPT", "Generative Pre-trained Transformer，OpenAI 开发的大语言模型系列。从 GPT-3 到 GPT-4，参数规模从 1750 亿增长到万亿级别。使用自回归方式逐 token 生成文本，遵循\"预测下一个词\"的训练范式。"),
        ("Diffusion Model", "扩散模型。一种生成式模型，通过逐步向数据加噪再学习去噪来生成新样本。是 Stable Diffusion、Midjourney、DALL-E 等 AI 绘画工具的核心技术。训练稳定、生成质量高，已成为图像生成的主流方法。"),
        ("RLHF", "基于人类反馈的强化学习（Reinforcement Learning from Human Feedback）。先让人类标注员对模型输出排序，训练一个奖励模型，再用强化学习（PPO 算法）优化语言模型。是 ChatGPT 成功的关键技术——让模型学会\"对人有用的回答\"。"),
        ("Tokenization", "分词/词元化。将原始文本切分成 LLM 能处理的最小单元（token）。中文一个 token 约等于 0.5-1 个字，英文约 0.75 个单词。不同模型的分词器不同。token 数量直接影响推理成本和速度。"),
        ("Hallucination", "幻觉。大模型生成看似合理但事实错误的内容。原因包括：训练数据噪声、概率式生成机制、缺乏事实校验能力。缓解方案：RAG 检索增强、外部工具调用、事实性约束提示。是目前 LLM 最大的可靠性短板。"),
        ("Vector Database", "向量数据库。专门存储和检索高维向量数据的数据库。支持相似度搜索（余弦相似度、欧氏距离），是 RAG 架构的关键基础设施。代表产品：Pinecone、Milvus、Weaviate、Chroma。"),
        ("AI Agent", "AI 智能体。能够自主感知环境、制定计划、调用工具、执行多步任务来完成目标的 AI 系统。核心组件：LLM（大脑）+ 工具调用 + 记忆系统 + 规划能力。能独立完成\"订机票\"级复杂任务，不只是一问一答。"),
        ("Chain-of-Thought", "思维链（CoT）。在提示词中加入\"让我们一步步思考\"，引导模型将复杂问题拆解为中间推理步骤再给出最终答案。显著提升数学、逻辑推理类任务准确率。一个简单的提示技巧，但对复杂问题效果惊人。"),
    ],
    "金融": [
        ("市盈率(P/E)", "Price-to-Earnings Ratio，股票价格除以每股收益。衡量市场愿意为每元利润支付多少钱。高 PE 代表高增长预期（如科技股 50x），低 PE 可能表示价值被低估或前景不乐观（如银行股 5x）。是最常用的估值指标之一。"),
        ("市净率(P/B)", "Price-to-Book Ratio，股票价格除以每股净资产。适用于重资产行业估值（银行、地产）。P/B < 1 意味股价跌破净资产，可能是价值陷阱也可能是买入机会。不适合轻资产公司（互联网）的估值。"),
        ("ROE", "净资产收益率（Return on Equity），净利润除以股东权益。衡量公司用股东的钱赚钱的效率。巴菲特最看重的指标，偏好长期 ROE > 15% 的公司。公式可拆解为：净利率 × 总资产周转率 × 权益乘数（杜邦分析法）。"),
        ("ROA", "总资产收益率（Return on Assets），净利润除以总资产。衡量公司利用全部资产赚钱的效率，不区分资金来源（股权还是举债）。ROA 越高，公司的资产利用效率越高。与 ROE 结合看可以判断杠杆程度。"),
        ("ETF", "交易型开放式指数基金（Exchange Traded Fund）。像股票一样在交易所实时买卖的基金，追踪某个指数（如沪深 300、标普 500）。费用低（年费 0.1%-0.5%）、透明度高、分散风险。是普通投资者最推荐的工具。"),
        ("量化宽松(QE)", "Quantitative Easing，央行通过在公开市场购买国债等资产向金融体系注入大量流动性。导致利率下降、资产价格上涨。2008 年金融危机后美联储多次使用。副作用：通胀压力、贫富差距扩大。"),
        ("通货膨胀", "货币购买力持续下降，物价普遍上涨。温和通胀（2%-3%）对经济增长有利；恶性通胀（>50%）摧毁经济（如 1923 年德国、2008 年津巴布韦）。衡量指标：CPI（消费者物价指数）、PPI（生产者物价指数）。"),
        ("通货紧缩", "物价持续下跌。听起来好（钱更值钱）实际上很危险：消费者推迟购买→企业收入下降→裁员→需求进一步萎缩→死亡螺旋。日本\"失落的三十年\"就是通缩的经典案例。央行极度恐惧通缩。"),
        ("IPO", "首次公开募股（Initial Public Offering）。公司第一次向公众发行股票，从私有公司变为上市公司。过程：投行承销→路演推销→确定发行价→挂牌交易。目的是融资和发展。但 IPO 不代表公司盈利，很多上市后破发。"),
        ("债券", "政府或公司向投资者借钱时发行的债务凭证。承诺到期归还本金 + 按期支付利息（票息）。核心要素：面值、票面利率、到期日。价格与市场利率反向变动：利率上升，债券价格下跌。被视为比股票更安全的资产类别。"),
        ("期货", "一种标准化合约，约定在未来某个时间以今天确定的价格买卖某种商品或金融资产。最初为农民锁定粮价而设计（对冲风险），现在也大量用于投机。杠杆高、风险大。品种：商品期货（原油、大豆）、金融期货（股指、国债）。"),
        ("期权", "一种权利而非义务的合约。看涨期权（Call）：以约定价格买入的权利；看跌期权（Put）：以约定价格卖出的权利。买方支付\"权利金\"购买权利，卖方收取权利金但承担履约义务。是一种非线性损益的金融衍生品。"),
        ("对冲基金", "采用多种复杂策略（多空股票、全球宏观、事件驱动、量化套利等）追求绝对收益的私募基金。特点：高门槛（百万美元级）、高费率（2% 管理费 + 20% 业绩提成）、杠杆使用、监管较宽松。桥水（Bridgewater）和文艺复兴科技是最著名的两家。"),
        ("指数基金", "被动跟踪特定市场指数（如标普 500、沪深 300）的基金。不做个股选择，不择时。费用极低（0.03%-0.2%）。巴菲特多次推荐：长期来看 90% 以上的主动基金经理跑不赢指数。适合\"买了就不管\"的长期投资者。"),
        ("股息率", "Dividend Yield，每股年度分红除以股价。公司把利润分给股东的比例（相对于股价）。高股息率公司通常处于成熟期（银行、公用事业），低股息率或不派息公司看重再投资增长（科技公司）。A 股提醒：股息率还要考虑分红持续性。"),
    ],
    "哲学": [
        ("存在主义", "Existentialism。核心命题：存在先于本质。人首先存在、出现在这个世界上，然后才通过自己的选择和行动定义自己是谁。强调个体自由、选择和个人责任。代表：萨特、加缪、克尔凯郭尔。关键概念：荒谬、自由、本真性、他者。"),
        ("功利主义", "Utilitarianism。道德行为的正确性取决于其带来的结果——\"最大多数人的最大幸福\"。由边沁和密尔提出。优点：简单直观，提供决策框架。批评：可能为多数人利益牺牲少数人权利、幸福难以量化。是现代公共政策分析的哲学基础之一。"),
        ("形而上学", "Metaphysics。哲学中最古老的分支，研究存在本身的性质——什么是真实？什么东西存在？时间、空间、因果、自由意志的本质是什么？\"物理学之后\"（亚里士多德著作编目）。核心问题：物质 vs 心灵、共相问题、同一性问题。"),
        ("认识论", "Epistemology。研究知识的本质、来源和限度。核心问题：什么是知识？（被辩护的真信念？）我们如何获得知识？（理性 vs 经验）我们能知道什么？（怀疑论挑战）。柏拉图的知识是\"被辩护的真信念\"定义至今仍是讨论起点。"),
        ("斯多葛主义", "Stoicism。古希腊罗马哲学流派，核心教导是：不要为无法控制的事情焦虑，只关注你能控制的——你的判断、选择和品格。代表人物：塞涅卡、爱比克泰德、马可·奥勒留。锻炼方法：消极想象、预先沉思、自我抽离。近年来因为实用性强而复兴。"),
        ("虚无主义", "Nihilism。相信生命没有内在意义、客观价值或终极目的。尼采不是虚无主义者，而是诊断并试图克服虚无主义的哲学家。他区分了\"消极虚无主义\"（绝望放弃）和\"积极虚无主义\"（摧毁旧价值，创造新价值）。\"上帝已死\"是对基督教道德崩塌的诊断。"),
        ("经验主义", "Empiricism。认为一切知识最终来源于感官经验的哲学传统。\"心灵是一张白纸（tabula rasa）\"——洛克。与理性主义对立：经验主义强调经验和归纳，理性主义强调理性和演绎。关键人物：洛克、贝克莱、休谟。现代科学的基本方法论源于此。"),
        ("理性主义", "Rationalism。认为理性而非感官经验是知识的主要来源。感官会欺骗我们（水中筷子看起来弯曲），但理性可以把握永恒真理。代表人物：笛卡尔（\"我思故我在\"）、斯宾诺莎（几何学证明上帝）、莱布尼茨（单子论）。与经验主义的争论推动了整个近代哲学。"),
        ("现象学", "Phenomenology。胡塞尔创立的 20 世纪重要哲学方法。口号\"回到事物本身\"——悬置一切预设和前见，直接描述意识体验到的现象。研究意识的意向性结构（意识总是关于某物的意识）。深刻影响了海德格尔、梅洛-庞蒂、萨特。"),
        ("辩证法", "Dialectic。源于古希腊对话术，经黑格尔发展为系统的哲学方法：正题→反题→合题，通过矛盾推动思想演进。马克思将其改造为唯物辩证法，用经济基础与上层建筑的矛盾解释历史发展。核心洞见：变化不是线性的，而是通过矛盾冲突实现的。"),
        ("自由意志", "Free Will。人类能否自由地选择和行动？决定论者认为一切事件都有前因，自由只是幻觉。相容论者试图调和自由与因果决定：自由不在于没有原因，而在于按自己的意愿行事而不被外力胁迫。神经科学（Libet 实验）让这个争论更加激烈。"),
        ("决定论", "Determinism。一切事件——包括人类的每一个决定和行动——都是由先前的原因必然导致的。\"给定宇宙在任意时刻的完整状态，未来完全被决定了。\"拉普拉斯妖是极端决定论的经典思想实验。如果真是这样，道德责任还有意义吗？"),
        ("道德相对主义", "Moral Relativism。道德判断（什么事情是对的/错的）不是绝对的，而是相对于特定文化、社会或个人的标准。不同的时代和地点有不同的道德准则。优点是文化包容；批评是：如果一切都是相对的，如何谴责纳粹的暴行？是否存在普世底线？"),
        ("社会契约", "Social Contract。霍布斯、洛克、卢梭提出的政治哲学理论：人类从\"自然状态\"通过彼此同意（契约）进入政治社会，建立政府来保障权利。不同版本：霍布斯（强政府防战争）、洛克（有限政府保护财产）、卢梭（公意是全体人民的共同意志）。是现代民主国家的理论基石。"),
        ("我思故我在", "Cogito ergo sum。笛卡尔在普遍怀疑（可能一切都是幻觉或魔鬼欺骗）后找到的不可怀疑的支点：我可以怀疑一切，但\"我正在怀疑\"这件事本身证明了我的存在。\"我思故我在\"不是推理而是直觉，标志了近代哲学从外在权威转向主体性的开始。"),
    ],
}


class Backend:
    def __init__(self, data_dir: str, config_file: str | None = None):
        self.data_file = os.path.join(data_dir, "concepts.json")
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = os.path.join(os.path.dirname(data_dir), "config.json")
        self.config = self._load_config()
        self.concepts: list[dict] = []
        self.review_log: list[dict] = []
        self._load()

    def _load_config(self) -> dict:
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_api_key(self) -> str:
        # Priority: env var > config file
        key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("DEEPSEEK_API_KEY")
        if key:
            return key
        return self.config.get("api_key", "")

    def set_api_key(self, key: str):
        self.config["api_key"] = key
        self._save_config()

    def get_brave_search_api_key(self) -> str:
        key = os.environ.get("BRAVE_SEARCH_API_KEY")
        if key:
            return key
        return self.config.get("brave_search_api_key", "")

    def set_brave_search_api_key(self, key: str):
        self.config["brave_search_api_key"] = key
        self._save_config()

    def _load(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.concepts = data.get("concepts", [])
                self.review_log = data.get("review_log", [])
            # 确保每个卡片含有 SM-2 必备字段（兼容旧文件 / demo 数据）
            today = date.today().isoformat()
            now = datetime.now().isoformat()
            for c in self.concepts:
                c.setdefault("ease_factor", 2.5)
                c.setdefault("interval", 0)
                c.setdefault("repetitions", 0)
                c.setdefault("next_review", today)
                c.setdefault("last_review", None)
                c.setdefault("created_at", now)
        else:
            self._init_with_preloaded()
            self._save()

    def _save(self):
        tmp = self.data_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"concepts": self.concepts, "review_log": self.review_log},
                      f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.data_file)

    def _init_with_preloaded(self):
        today = date.today().isoformat()
        now = datetime.now().isoformat()
        for category, items in PRELOADED_CONCEPTS.items():
            for term, definition in items:
                self.concepts.append({
                    "id": str(uuid.uuid4()),
                    "term": term,
                    "definition": definition,
                    "category": category,
                    "ease_factor": 2.5,
                    "interval": 0,
                    "repetitions": 0,
                    "next_review": today,
                    "last_review": None,
                    "created_at": now,
                })
        random.shuffle(self.concepts)

    # ---- SM-2 Algorithm ----

    def _apply_sm2(self, card: dict, quality: int):
        """Apply SM-2 spaced repetition algorithm to a card.
        quality: 1=forgot, 3=hard, 5=good
        """
        today = date.today()

        if quality < 3:
            card["repetitions"] = 0
            card["interval"] = 1
        else:
            if card["repetitions"] == 0:
                card["interval"] = 1
            elif card["repetitions"] == 1:
                card["interval"] = 6
            else:
                card["interval"] = round(card["interval"] * card["ease_factor"])

            card["repetitions"] += 1

            q = quality
            ef_delta = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
            card["ease_factor"] = max(1.3, card["ease_factor"] + ef_delta)

        card["next_review"] = (today + timedelta(days=card["interval"])).isoformat()
        card["last_review"] = today.isoformat()

    # ---- Public API ----

    def get_due_cards(self, category: str = "全部") -> list[dict]:
        today = date.today().isoformat()
        due = [c for c in self.concepts if c["next_review"] <= today]
        if category != "全部":
            due = [c for c in due if c["category"] == category]
        random.shuffle(due)
        return due

    def rate_card(self, card_id: str, quality: int):
        for card in self.concepts:
            if card["id"] == card_id:
                self._apply_sm2(card, quality)
                self.review_log.append({
                    "card_id": card_id,
                    "term": card["term"],
                    "category": card["category"],
                    "quality": quality,
                    "date": date.today().isoformat(),
                })
                self._save()
                return
        raise ValueError(f"Card not found: {card_id}")

    def add_concept(self, term: str, definition: str, category: str) -> dict:
        card = self._make_concept_card(term, definition, category)
        self.concepts.append(card)
        self._save()
        return card

    def _make_concept_card(self, term: str, definition: str, category: str, extra: dict | None = None) -> dict:
        card = {
            "id": str(uuid.uuid4()),
            "term": term,
            "definition": definition,
            "category": category,
            "ease_factor": 2.5,
            "interval": 0,
            "repetitions": 0,
            "next_review": date.today().isoformat(),
            "last_review": None,
            "created_at": datetime.now().isoformat(),
        }
        if extra:
            card.update(extra)
        return card

    def _brave_search(self, query: str, freshness: str) -> list[dict]:
        api_key = self.get_brave_search_api_key()
        if not api_key:
            raise ValueError("未配置 Brave Search API Key。请在设置里填写后再搜索。")

        params = urllib.parse.urlencode({
            "q": query,
            "count": 8,
            "search_lang": "zh",
            "freshness": freshness,
            "extra_snippets": "true",
        })
        req = urllib.request.Request(
            f"https://api.search.brave.com/res/v1/web/search?{params}",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return [{"error": f"Brave 搜索失败 ({e.code})，请检查 API Key 或稍后重试。"}]
        except Exception as e:
            return [{"error": f"Brave 搜索网络失败：{str(e)}"}]

        items = []
        for result in data.get("web", {}).get("results", [])[:8]:
            items.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "description": result.get("description", ""),
                "extra_snippets": result.get("extra_snippets", [])[:3],
            })
        return items

    def discover_industry_terms(self, industry: str, freshness: str = "pm") -> dict:
        industry = (industry or "").strip()
        freshness = freshness if freshness in {"pd", "pw", "pm", "py"} else "pm"
        if not industry:
            return {"ok": False, "error": "请输入一个行业词。", "items": []}
        if not self.get_brave_search_api_key():
            return {"ok": False, "error": "未配置 Brave Search API Key。请在设置里填写后再搜索。", "items": []}
        if not self.get_api_key():
            return {"ok": False, "error": "未配置 DeepSeek API Key。请在设置里填写后再搜索。", "items": []}

        queries = [
            f"{industry} 黑话 概念",
            f"{industry} 术语 趋势",
            f"{industry} 行业词 新词",
        ]
        seen_urls = set()
        snippets = []
        for query in queries:
            results = self._brave_search(query, freshness)
            if results and results[0].get("error"):
                return {"ok": False, "error": results[0]["error"], "items": []}
            for item in results:
                url = item.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                text = " ".join([
                    item.get("title", ""),
                    item.get("description", ""),
                    " ".join(item.get("extra_snippets", [])),
                ])
                snippets.append({
                    "title": item.get("title", "")[:120],
                    "url": url,
                    "text": re.sub(r"\s+", " ", text).strip()[:520],
                })
                if len(snippets) >= 24:
                    break

        if not snippets:
            return {"ok": True, "items": [], "source_count": 0}

        existing_terms = {c.get("term", "").strip().lower() for c in self.concepts}
        source_block = "\n".join(
            f"[{idx + 1}] 标题：{s['title']}\nURL：{s['url']}\n摘要：{s['text']}"
            for idx, s in enumerate(snippets)
        )
        prompt = (
            f"你只能根据下面的网页搜索摘要，提取「{industry}」行业最近出现或常被使用的黑话、术语、新概念。\n"
            f"不要凭空补充，不要输出摘要里没有依据的词。\n\n"
            f"已有概念库词名（避免重复）：{', '.join(sorted(existing_terms))[:1200]}\n\n"
            f"搜索摘要：\n{source_block}\n\n"
            f"请只返回 JSON 数组，不要 Markdown，不要解释。最多 12 项。\n"
            f"每项字段：term, definition, category, why_relevant, source_urls, confidence。\n"
            f"definition 用 40-90 字中文解释；category 优先用「{industry}」；"
            f"source_urls 必须来自上面的 URL；confidence 是 0 到 1 的数字。"
        )
        raw = self._call_deepseek([
            {"role": "system", "content": "你是严谨的行业术语整理助手，只基于给定材料抽取候选概念。"},
            {"role": "user", "content": prompt},
        ])
        if raw.startswith("⚠️"):
            return {"ok": False, "error": raw, "items": []}

        try:
            json_text = raw.strip()
            if "```" in json_text:
                json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", json_text, flags=re.S).strip()
            start, end = json_text.find("["), json_text.rfind("]")
            if start >= 0 and end >= start:
                json_text = json_text[start:end + 1]
            parsed = json.loads(json_text)
        except Exception:
            return {"ok": False, "error": "AI 返回格式无法解析，请重试。", "items": []}

        valid_urls = {s["url"] for s in snippets}
        items = []
        seen_terms = set()
        for item in parsed if isinstance(parsed, list) else []:
            term = str(item.get("term", "")).strip()
            key = term.lower()
            if not term or key in seen_terms or key in existing_terms:
                continue
            source_urls = [u for u in item.get("source_urls", []) if u in valid_urls]
            if not source_urls:
                continue
            try:
                confidence = float(item.get("confidence", 0.5))
            except Exception:
                confidence = 0.5
            seen_terms.add(key)
            items.append({
                "term": term[:60],
                "definition": str(item.get("definition", "")).strip()[:180],
                "category": str(item.get("category", industry)).strip()[:40] or industry,
                "why_relevant": str(item.get("why_relevant", "")).strip()[:180],
                "source_urls": source_urls[:3],
                "confidence": max(0, min(1, confidence)),
                "discovered_from": industry,
            })

        items.sort(key=lambda x: x["confidence"], reverse=True)
        return {"ok": True, "items": items[:12], "source_count": len(snippets)}

    def import_discovered_terms(self, items: list[dict]) -> dict:
        if not isinstance(items, list):
            return {"ok": False, "error": "导入数据格式不正确。", "imported": []}
        existing_terms = {c.get("term", "").strip().lower() for c in self.concepts}
        imported = []
        for item in items[:12]:
            term = str(item.get("term", "")).strip()
            definition = str(item.get("definition", "")).strip()
            category = str(item.get("category", "")).strip() or str(item.get("discovered_from", "")).strip() or "自定义"
            if not term or not definition or term.lower() in existing_terms:
                continue
            card = self._make_concept_card(term, definition, category, {
                "source_urls": item.get("source_urls", [])[:3],
                "discovered_from": item.get("discovered_from", category),
            })
            self.concepts.append(card)
            existing_terms.add(term.lower())
            imported.append(card)
        if imported:
            self._save()
        return {"ok": True, "imported": imported, "count": len(imported)}

    # ---- AI Deep Dive ----

    def random_explore(self, category: str = "全部", exclude_ids: list[str] | None = None) -> dict | None:
        pool = self.concepts if category == "全部" else [c for c in self.concepts if c["category"] == category]
        if exclude_ids:
            pool = [c for c in pool if c["id"] not in exclude_ids]
        if not pool:
            return None
        card = random.choice(pool)

        # Check cache
        cache_key = f"explore_reason_{card['id']}"
        if card.get(cache_key):
            return {"id": card["id"], "term": card["term"], "definition": card["definition"],
                    "category": card["category"], "reason": card[cache_key]}

        system_prompt = (
            "你是一个有品位的知识策展人，擅长用一个意想不到的角度介绍概念。"
            "你的风格像一位博学的朋友在咖啡馆里随口分享一个有趣的想法——轻松、有洞察、不卖弄。"
        )

        prompt = (
            f"用户今天随机遇到了这个概念：「{card['term']}」\n\n"
            f"定义：{card['definition']}\n\n"
            f"请用 150 字左右，从一个出人意料的有趣角度，告诉用户为什么今天了解这个概念很值得。\n"
            f"要求：\n"
            f"- 不要复述定义，要提供一个新鲜视角\n"
            f"- 可以联系日常生活、热点事件、或一个有趣的类比\n"
            f"- 语气轻松自然，像朋友聊天\n"
            f"- 用中文，2-3 句话即可"
        )

        reason = self._call_deepseek([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ])

        if not reason.startswith("⚠️"):
            card[cache_key] = reason
            self._save()

        return {"id": card["id"], "term": card["term"], "definition": card["definition"],
                "category": card["category"], "reason": reason}

    def _find_card(self, card_id: str) -> dict | None:
        for c in self.concepts:
            if c["id"] == card_id:
                return c
        return None

    def _normalize_relation_type(self, relation) -> str:
        if not isinstance(relation, str):
            return "extends"
        relation = relation.strip().lower()
        relation = RELATION_ALIAS_MAP.get(relation, relation)
        if relation in RELATION_LABELS:
            return relation
        return "extends"

    def _default_relation_reason(self, source_card: dict, target_card: dict, relation: str) -> str:
        relation = self._normalize_relation_type(relation)
        source_term = source_card.get("term", "当前概念")
        target_term = target_card.get("term", "相关概念")
        if relation == "prerequisite":
            return f"{target_term} 是理解 {source_term} 的前置基础。"
        if relation == "confusable":
            return f"{source_term} 和 {target_term} 容易在概念边界上混淆。"
        if relation == "contrast":
            return f"{source_term} 和 {target_term} 可以放在一起对比理解。"
        return f"{target_term} 可以作为 {source_term} 的延伸理解。"

    def _default_relation_hint(self, source_card: dict, target_card: dict, relation: str) -> str:
        relation = self._normalize_relation_type(relation)
        source_term = source_card.get("term", "当前概念")
        target_term = target_card.get("term", "相关概念")
        if relation == "prerequisite":
            return f"先掌握 {target_term}，再回来看 {source_term}。"
        if relation == "confusable":
            return f"重点区分 {source_term} 和 {target_term} 的边界。"
        if relation == "contrast":
            return f"把 {source_term} 和 {target_term} 放在一起比较。"
        return f"把 {target_term} 当作 {source_term} 的补充背景。"

    def _build_normalized_relation_row(self, source_card: dict, target_card: dict, rel: dict) -> dict:
        relation = self._normalize_relation_type(rel.get("relation"))
        reason = rel.get("reason") or self._default_relation_reason(source_card, target_card, relation)
        hint = rel.get("hint") or self._default_relation_hint(source_card, target_card, relation)
        difference = rel.get("difference") or f"{source_card.get('term', '当前概念')} 与 {target_card.get('term', '相关概念')} 的侧重点不同。"
        strength = _clamp_strength(rel.get("strength"))
        return {
            "id": target_card["id"],
            "term": target_card.get("term", ""),
            "definition": target_card.get("definition", ""),
            "category": target_card.get("category", ""),
            "relation": relation,
            "relation_label": RELATION_LABELS.get(relation, RELATION_LABELS["extends"]),
            "reason": reason,
            "hint": hint,
            "difference": difference,
            "strength": strength,
        }

    def _normalize_relations(self, card: dict) -> list[dict]:
        raw_relations = card.get("related_concepts") or []
        if not isinstance(raw_relations, list):
            return []

        normalized_by_id: dict[str, dict] = {}
        order: list[str] = []
        source_card = card
        for rel in raw_relations:
            if not isinstance(rel, dict):
                continue
            target_id = rel.get("id")
            if not isinstance(target_id, str) or not target_id or target_id == card.get("id"):
                continue
            target_card = self._find_card(target_id)
            if not target_card:
                continue

            candidate = self._build_normalized_relation_row(source_card, target_card, rel)
            if target_id not in normalized_by_id:
                normalized_by_id[target_id] = candidate
                order.append(target_id)
                continue

            current = normalized_by_id[target_id]
            candidate_rank = (
                RELATION_PRIORITY.get(candidate["relation"], RELATION_PRIORITY["extends"]),
                -candidate["strength"],
            )
            current_rank = (
                RELATION_PRIORITY.get(current["relation"], RELATION_PRIORITY["extends"]),
                -current["strength"],
            )
            if candidate_rank < current_rank:
                normalized_by_id[target_id] = candidate

        return [normalized_by_id[target_id] for target_id in order]

    def _split_markdown_sections(self, article: str) -> list[dict]:
        if not isinstance(article, str) or not article.strip():
            return []

        sections = []
        current_title = None
        current_lines: list[str] = []

        for raw_line in article.splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                if current_title is not None:
                    sections.append({
                        "title": current_title,
                        "content": "\n".join(current_lines).strip(),
                    })
                current_title = line[3:].strip()
                current_lines = []
                continue
            if line.startswith("# ") and current_title is None:
                current_title = line[2:].strip()
                current_lines = []
                continue
            if current_title is not None:
                current_lines.append(raw_line)

        if current_title is not None:
            sections.append({
                "title": current_title,
                "content": "\n".join(current_lines).strip(),
            })

        return [section for section in sections if section["title"] or section["content"]]

    def _article_mentions_term(self, article: str, term: str) -> bool:
        if not isinstance(article, str) or not isinstance(term, str):
            return False
        term = term.strip()
        if not term:
            return False
        if re.search(r"[\u4e00-\u9fff]", term):
            return term in article
        if re.fullmatch(r"[A-Za-z0-9_-]+", term):
            pattern = rf"(?<![A-Za-z0-9_-]){re.escape(term)}(?![A-Za-z0-9_-])"
            return re.search(pattern, article) is not None
        return term in article

    def _pick_inline_terms(self, article: str, relations: list[dict]) -> list[dict]:
        if not isinstance(article, str) or not article.strip() or not isinstance(relations, list):
            return []

        allowed_relations = ("prerequisite", "confusable", "extends")
        picks = []
        seen_terms: set[str] = set()

        for relation_type in allowed_relations:
            for row in relations:
                if row.get("relation") != relation_type:
                    continue
                term = row.get("term")
                if not isinstance(term, str) or not term.strip() or term in seen_terms:
                    continue
                if not self._article_mentions_term(article, term):
                    continue
                picks.append(dict(row))
                seen_terms.add(term)
                if len(picks) >= 6:
                    return picks

        return picks

    def _build_learning_navigation(self, card: dict, article: str) -> dict:
        relations = self._normalize_relations(card)
        prerequisites = [row for row in relations if row["relation"] == "prerequisite"][:2]
        confusions = [row for row in relations if row["relation"] in {"confusable", "contrast"}][:2]
        next_steps = [row for row in relations if row["relation"] == "extends"][:2]
        local_graph_nodes = (prerequisites + confusions + next_steps)[:7]

        return {
            "prerequisites": prerequisites,
            "confusions": confusions,
            "next_steps": next_steps,
            "inline_terms": self._pick_inline_terms(article, relations),
            "local_graph": {
                "center": {
                    "id": card.get("id"),
                    "term": card.get("term", ""),
                    "definition": card.get("definition", ""),
                    "category": card.get("category", ""),
                },
                "nodes": local_graph_nodes,
            },
        }

    def get_deep_dive_payload(self, card_id: str) -> dict:
        card = self._find_card(card_id)
        if not card:
            return {"error": "not_found"}

        article = self.deep_dive(card_id)
        safe_article = ""
        if isinstance(article, str) and not article.startswith("\u26a0\ufe0f"):
            safe_article = article

        navigation = self._build_learning_navigation(card, safe_article)

        return {
            "card": {
                "id": card.get("id"),
                "term": card.get("term", ""),
                "definition": card.get("definition", ""),
                "category": card.get("category", ""),
            },
            "article": article,
            "sections": self._split_markdown_sections(safe_article),
            "prerequisites": navigation["prerequisites"],
            "confusions": navigation["confusions"],
            "next_steps": navigation["next_steps"],
            "inline_terms": navigation["inline_terms"],
            "local_graph": navigation["local_graph"],
        }

    def _interval_of(self, card_id: str) -> int:
        c = self._find_card(card_id)
        return c.get("interval", 0) if c else 0

    def _pick_core_stars(self, stars: list[dict]) -> set[str]:
        """每个 category 选 level 最高、平手取 interval 最大的概念为主星。"""
        by_cat: dict[str, list[dict]] = {}
        for s in stars:
            by_cat.setdefault(s["category"], []).append(s)
        core_ids: set[str] = set()
        for cat, group in by_cat.items():
            lit = [s for s in group if s["level"] >= 1]
            if not lit:
                continue
            best = max(lit, key=lambda s: (s["level"], self._interval_of(s["id"])))
            core_ids.add(best["id"])
        return core_ids

    def _call_deepseek(self, messages: list[dict], stream: bool = False) -> str:
        api_key = self.get_api_key()
        if not api_key:
            return "⚠️ 未配置 API Key，无法使用 AI 学习功能。请点击右上角 ⚙ 设置。"

        data = json.dumps({
            "model": "deepseek-chat",
            "messages": messages,
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": 4096,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return f"⚠️ API 调用失败 ({e.code})。请检查网络和 API Key 配置。"
        except Exception as e:
            return f"⚠️ 网络请求失败: {str(e)}"

    def deep_dive(self, card_id: str) -> str:
        card = self._find_card(card_id)
        if not card:
            return "⚠️ 未找到该概念。"

        # Return cached if it was generated by the current article structure.
        if card.get("deep_article") and card.get("deep_article_version") == DEEP_ARTICLE_VERSION:
            return card["deep_article"]

        system_prompt = (
            "你是一位知识渊博的导师，擅长用通俗易懂的方式解释复杂概念。"
            "你的回答要既有深度又容易理解，适合非专业读者。"
            "使用中文回答，Markdown 格式排版。"
            "不要写成百科词条，要像一篇循序渐进的概念深读。"
            "不要寒暄、不要导语、不要总结性客套话、不要使用 --- 分隔线。"
            "第一行必须直接是：## 一句话讲清"
        )

        user_prompt = (
            f"我正在学习一个概念：「{card['term']}」\n\n"
            f"它的基本定义是：{card['definition']}\n\n"
            f"请生成一篇由浅入深的概念深读，严格使用下面 8 个二级标题，"
            f"每段要具体、有信息密度，不要泛泛而谈：\n\n"
            f"## 一句话讲清\n用一句非常白话的话讲清这个概念。不要超过 35 字。\n\n"
            f"## 核心定义拆解\n把定义拆成 3-5 个关键点解释。关键术语用加粗标出。\n\n"
            f"## 为什么重要\n说明它解决什么问题，为什么在现实生活、工作或学习里值得理解。\n\n"
            f"## 底层机制\n解释它为什么会这样运作。不要只重复定义，要说出因果链条。\n\n"
            f"## 生活类比\n给 2-3 个不同角度的类比，每个类比后说明类比的边界，避免误导。\n\n"
            f"## 常见误区\n列 3 个容易误解的点。每个误区包含：错误理解、正确理解。\n\n"
            f"## 相邻概念对比\n选 2-3 个容易混淆的相邻概念，用简短对比讲清差别。\n\n"
            f"## 真实案例与自测\n给 2 个真实或贴近日常的案例，然后给 3 道短答自测题。"
        )

        content = self._call_deepseek([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        if not content.startswith("⚠️"):
            card["deep_article"] = content
            card["deep_article_version"] = DEEP_ARTICLE_VERSION
            self._save()

        return content

    def ask_question(self, card_id: str, question: str, history: list[dict] | None = None) -> str:
        card = self._find_card(card_id)
        if not card:
            return "⚠️ 未找到该概念。"

        system_prompt = (
            f"你是一位耐心博学的导师。用户正在学习一个概念：\n"
            f"**{card['term']}**：{card['definition']}\n\n"
            f"用户会围绕这个概念提问。请用通俗易懂的中文回答，"
            f"可以结合案例、类比来帮助理解。"
            f"如果不确定答案，坦诚说明，不要编造。\n\n"
            f"【格式要求】\n"
            f"- 使用 Markdown 标题（## 或 ###）将内容分成小节，不要一大段文字\n"
            f"- 用短段落，每段不超过 3 行\n"
            f"- 适当使用列表（- ）和加粗（**）突出重点\n"
            f"- 重要术语用反引号标注\n"
            f"- 总回复控制在 300 字以内，简洁优先"
        )

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        return self._call_deepseek(messages)

    def get_stats(self) -> dict:
        today = date.today().isoformat()
        total = len(self.concepts)
        due_today = sum(1 for c in self.concepts if c["next_review"] <= today)
        reviewed_today = sum(1 for c in self.concepts if c["last_review"] == today)
        return {"total": total, "due_today": due_today, "reviewed_today": reviewed_today}

    def get_categories(self) -> list[str]:
        return sorted(set(c["category"] for c in self.concepts))

    def get_chat_history(self, card_id: str) -> list:
        card = self._find_card(card_id)
        if card:
            return card.get("chat_history", [])
        return []

    def save_chat_history(self, card_id: str, history: list):
        card = self._find_card(card_id)
        if card:
            card["chat_history"] = history
            self._save()

    def clear_chat_history(self, card_id: str):
        card = self._find_card(card_id)
        if card and "chat_history" in card:
            del card["chat_history"]
            self._save()

    def delete_category(self, category: str) -> int:
        before = len(self.concepts)
        self.concepts = [c for c in self.concepts if c["category"] != category]
        deleted = before - len(self.concepts)
        if deleted:
            self._save()
        return deleted

    def delete_card(self, card_id: str) -> bool:
        card = self._find_card(card_id)
        if not card:
            return False
        self.concepts = [c for c in self.concepts if c["id"] != card_id]
        self.review_log = [e for e in self.review_log if e["card_id"] != card_id]
        self._save()
        return True

    def get_daily_stats(self, days: int = 90) -> dict[str, int]:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        counts: dict[str, int] = {}
        for entry in self.review_log:
            d = entry["date"]
            if d >= cutoff:
                counts[d] = counts.get(d, 0) + 1
        return counts

    def get_category_stats(self) -> list[dict]:
        today = date.today().isoformat()
        cats: dict[str, dict] = {}
        for c in self.concepts:
            cat = c["category"]
            if cat not in cats:
                cats[cat] = {"category": cat, "total": 0, "ease_sum": 0.0, "due": 0, "reviewed_today": 0}
            s = cats[cat]
            s["total"] += 1
            s["ease_sum"] += c["ease_factor"]
            if c["next_review"] <= today:
                s["due"] += 1
            if c["last_review"] == today:
                s["reviewed_today"] += 1
        result = []
        for cat, s in cats.items():
            result.append({
                "category": cat,
                "total": s["total"],
                "avg_ease": round(s["ease_sum"] / s["total"], 2) if s["total"] else 0,
                "due": s["due"],
                "reviewed_today": s["reviewed_today"],
            })
        result.sort(key=lambda x: x["category"])
        return result

    def get_review_log(self, limit: int = 50) -> list[dict]:
        return list(reversed(self.review_log[-limit:]))

    def get_recent_cards(self, limit: int = 30) -> list[dict]:
        seen: set[str] = set()
        result = []
        for entry in reversed(self.review_log):
            cid = entry["card_id"]
            if cid not in seen:
                seen.add(cid)
                card = self._find_card(cid)
                if card:
                    result.append({
                        "id": card["id"],
                        "term": card["term"],
                        "definition": card["definition"],
                        "category": card["category"],
                        "last_review": entry["date"],
                        "last_quality": entry["quality"],
                    })
                if len(result) >= limit:
                    break
        return result

    # ---- Star Map ----

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
        # §9.2 改1: 标记主星
        core_ids = self._pick_core_stars(stars)
        for s in stars:
            s["is_core"] = s["id"] in core_ids
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
                "lit": s["lit"],
                "burning": s["burning"],
                "progress": round(ratio, 2),
                "formed": ratio >= 0.8,
            })
        return result

    def get_star_detail(self, concept_id):
        c = self._find_card(concept_id)
        if not c:
            return None
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

    def get_collisions(self):
        # 取最近学过的、跨板块的两个概念
        learned = [c for c in self.concepts if c.get("repetitions", 0) > 0]
        cats = {}
        for c in learned:
            cats.setdefault(c["category"], []).append(c)
        if len(cats) < 2:
            return None
        # 选两个不同板块各一个最近的
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
            self.config[cache_key] = result
            self._save_config()
        return result

    def get_sources(self, concept_id):
        c = self._find_card(concept_id)
        if not c:
            return []
        # 优先返回已缓存的 sources，否则拼接维基链接
        sources = c.get("sources", [])
        if sources:
            return sources
        term = c["term"]
        return [{"name": "Wikipedia", "url": f"https://zh.wikipedia.org/wiki/{term}", "type": "wikipedia"}]
