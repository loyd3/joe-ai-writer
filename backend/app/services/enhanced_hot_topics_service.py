"""
增强版热点写作服务
提供更丰富的热点源和更智能的分析
"""
import json
import re
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.services.llm_service import LLMService
from app.services.cache_service import CacheService


class EnhancedHotTopicsService:
    """增强版热点写作服务"""

    # 热点分类和关键词
    TOPIC_CATEGORIES = {
        "社会": ["社会热点", "民生", "教育", "医疗", "就业", "住房", "养老", "环保"],
        "科技": ["人工智能", "互联网", "新能源", "芯片", "5G", "元宇宙", "区块链", "量子计算"],
        "娱乐": ["明星", "影视", "综艺", "音乐", "游戏", "动漫", "网红", "直播"],
        "财经": ["股市", "房地产", "消费", "投资", "创业", "电商", "数字货币", "宏观经济"],
        "体育": ["足球", "篮球", "奥运会", "世界杯", "电竞", "健身", "运动", "赛事"],
        "国际": ["国际关系", "地缘政治", "贸易", "外交", "军事", "疫情", "气候", "能源"],
        "文化": ["历史", "文学", "艺术", "传统", "非遗", "国学", "哲学", "美学"],
        "生活": ["美食", "旅行", "健康", "时尚", "家居", "宠物", "育儿", "情感"]
    }

    # 热点标题模板
    TITLE_TEMPLATES = {
        "社会": [
            "{keyword}引发热议：{aspect}背后的深层思考",
            "从{keyword}看{aspect}：我们需要怎样的改变？",
            "{keyword}刷屏：{aspect}为何牵动万人心？",
            "深度解读：{keyword}背后的{aspect}真相",
            "{keyword}事件：{aspect}的困境与出路"
        ],
        "科技": [
            "{keyword} breakthrough：{aspect}将如何改变世界？",
            "深度解析：{keyword}技术背后的{aspect}逻辑",
            "{keyword}时代来临：{aspect}迎来新机遇",
            "从{keyword}看{aspect}：科技创新的下一站",
            "{keyword}革命：{aspect}正在被重新定义"
        ],
        "娱乐": [
            "{keyword}爆火：{aspect}为何让人上头？",
            "深度剖析：{keyword}背后的{aspect}密码",
            "{keyword}现象：{aspect}的新表达方式",
            "从{keyword}看{aspect}：娱乐内容的进化论",
            "{keyword}出圈：{aspect}的破圈之道"
        ],
        "财经": [
            "{keyword}震荡：{aspect}的投资逻辑变了？",
            "深度解读：{keyword}背后的{aspect}信号",
            "{keyword}趋势：{aspect}的新格局正在形成",
            "从{keyword}看{aspect}：市场的下一个风口",
            "{keyword}观察：{aspect}的危与机"
        ],
        "体育": [
            "{keyword}激战：{aspect}的巅峰对决",
            "深度解析：{keyword}背后的{aspect}故事",
            "{keyword}时刻：{aspect}的荣耀与梦想",
            "从{keyword}看{aspect}：体育精神的传承",
            "{keyword}风云：{aspect}的变与不变"
        ],
        "国际": [
            "{keyword}局势：{aspect}的全球影响",
            "深度观察：{keyword}背后的{aspect}博弈",
            "{keyword}动态：{aspect}正在重塑世界",
            "从{keyword}看{aspect}：国际格局的新变化",
            "{keyword}解读：{aspect}的深层逻辑"
        ],
        "文化": [
            "{keyword}传承：{aspect}的时代价值",
            "深度解读：{keyword}背后的{aspect}内涵",
            "{keyword}复兴：{aspect}的创新表达",
            "从{keyword}看{aspect}：文化的力量",
            "{keyword}观察：{aspect}的当代表达"
        ],
        "生活": [
            "{keyword}攻略：{aspect}的正确打开方式",
            "深度体验：{keyword}带来的{aspect}改变",
            "{keyword}指南：{aspect}的实用秘籍",
            "从{keyword}看{aspect}：生活美学的升级",
            "{keyword}分享：{aspect}的小确幸"
        ]
    }

    # 角度关键词
    ASPECT_KEYWORDS = {
        "社会": ["社会公平", "制度完善", "公众参与", "权利保障", "价值观念", "社会责任"],
        "科技": ["技术创新", "产业变革", "用户体验", "商业模式", "伦理挑战", "未来趋势"],
        "娱乐": ["内容创作", "粉丝经济", "IP价值", "传播规律", "审美变迁", "文化消费"],
        "财经": ["市场规律", "政策导向", "消费趋势", "产业转型", "风险管控", "价值发现"],
        "体育": ["竞技水平", "团队精神", "商业运作", "粉丝文化", "国家荣誉", "全民健身"],
        "国际": ["大国博弈", "地缘战略", "经济依存", "文化冲突", "全球治理", "多边合作"],
        "文化": ["传统传承", "创新发展", "文化自信", "交流互鉴", "精神内核", "时代精神"],
        "生活": ["品质提升", "健康理念", "消费观念", "生活方式", "情感需求", "自我实现"]
    }

    def __init__(self, llm_service: LLMService, cache_service: CacheService):
        self.llm_service = llm_service
        self.cache_service = cache_service
        self.cache_key = "hot_topics_cache"
        self.cache_ttl = 1800  # 30分钟缓存

    async def get_hot_topics(self, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热点话题列表
        """
        cache_key = f"{self.cache_key}:{category}:{limit}"
        cached = await self.cache_service.get(cache_key)

        if cached:
            return json.loads(cached)

        # 生成热点数据
        topics = self._generate_hot_topics(category, limit)

        # 缓存结果
        await self.cache_service.set(cache_key, json.dumps(topics, ensure_ascii=False), self.cache_ttl)

        return topics

    def _generate_hot_topics(self, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        生成热点话题数据
        """
        topics = []
        categories = [category] if category else list(self.TOPIC_CATEGORIES.keys())

        for cat in categories:
            keywords = self.TOPIC_CATEGORIES.get(cat, [])
            templates = self.TITLE_TEMPLATES.get(cat, self.TITLE_TEMPLATES["社会"])
            aspects = self.ASPECT_KEYWORDS.get(cat, [])

            for i in range(min(limit // len(categories) + 1, 3)):
                keyword = random.choice(keywords)
                aspect = random.choice(aspects)
                template = random.choice(templates)

                title = template.format(keyword=keyword, aspect=aspect)

                # 生成热度值（模拟）
                heat_score = random.randint(70, 99)

                # 生成讨论数（模拟）
                discussion_count = random.randint(10000, 1000000)

                topics.append({
                    "id": f"{cat}_{i}_{int(datetime.now().timestamp())}",
                    "title": title,
                    "category": cat,
                    "keyword": keyword,
                    "aspect": aspect,
                    "heat_score": heat_score,
                    "discussion_count": discussion_count,
                    "created_at": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
                    "source": self._get_random_source(),
                    "summary": self._generate_summary(keyword, aspect)
                })

        # 按热度排序
        topics.sort(key=lambda x: x["heat_score"], reverse=True)

        return topics[:limit]

    def _get_random_source(self) -> str:
        """获取随机来源"""
        sources = ["微博热搜", "知乎热榜", "百度热搜", "今日头条", "抖音热榜", "B站热门"]
        return random.choice(sources)

    def _generate_summary(self, keyword: str, aspect: str) -> str:
        """生成热点摘要"""
        summaries = [
            f"近期{keyword}成为关注焦点，{aspect}引发广泛讨论。",
            f"{keyword}持续发酵，{aspect}成为舆论关注的核心议题。",
            f"围绕{keyword}的讨论不断升温，{aspect}值得深入思考。",
            f"{keyword}引发社会关注，{aspect}成为讨论热点。",
        ]
        return random.choice(summaries)

    async def analyze_topic(
        self,
        topic_title: str,
        topic_keyword: str,
        topic_aspect: str,
        category: str,
        analysis_depth: str = "standard"
    ) -> Dict[str, Any]:
        """
        深度分析热点话题
        """
        prompt = f"""请对以下热点话题进行深度分析：

话题标题: {topic_title}
核心关键词: {topic_keyword}
分析角度: {topic_aspect}
所属分类: {category}

请从以下几个维度进行分析（分析深度: {analysis_depth}）：

1. 事件背景与起因
2. 核心争议点梳理
3. 各方观点汇总
4. 深层原因分析
5. 可能的发展趋势
6. 写作切入点建议

请以JSON格式输出，包含以下字段：
- background: 事件背景
- controversies: 争议点列表
- viewpoints: 各方观点对象
- deep_analysis: 深层分析
- trends: 发展趋势预测
- writing_angles: 写作切入点建议列表
"""

        try:
            response = await self.llm_service.generate(prompt, max_tokens=2000)

            # 尝试解析JSON
            try:
                # 查找JSON部分
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = self._parse_analysis_text(response)
            except json.JSONDecodeError:
                analysis = self._parse_analysis_text(response)

            return {
                "topic_title": topic_title,
                "topic_keyword": topic_keyword,
                "topic_aspect": topic_aspect,
                "category": category,
                "analysis": analysis,
                "analysis_depth": analysis_depth,
                "analyzed_at": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "topic_title": topic_title,
                "error": str(e),
                "analysis": self._get_default_analysis(topic_keyword, topic_aspect)
            }

    def _parse_analysis_text(self, text: str) -> Dict[str, Any]:
        """从文本中解析分析内容"""
        analysis = {
            "background": "",
            "controversies": [],
            "viewpoints": {},
            "deep_analysis": "",
            "trends": "",
            "writing_angles": []
        }

        # 简单的文本解析逻辑
        sections = text.split("\n\n")
        current_section = None

        for section in sections:
            if "背景" in section[:20]:
                analysis["background"] = section
            elif "争议" in section[:20]:
                analysis["controversies"] = [line.strip("- ") for line in section.split("\n") if line.strip().startswith("-")]
            elif "观点" in section[:20]:
                analysis["viewpoints"]["summary"] = section
            elif "原因" in section[:20] or "深层" in section[:20]:
                analysis["deep_analysis"] = section
            elif "趋势" in section[:20]:
                analysis["trends"] = section
            elif "切入" in section[:20] or "角度" in section[:20]:
                analysis["writing_angles"] = [line.strip("- ") for line in section.split("\n") if line.strip().startswith("-")]

        return analysis

    def _get_default_analysis(self, keyword: str, aspect: str) -> Dict[str, Any]:
        """获取默认分析结果"""
        return {
            "background": f"{keyword}近期成为社会关注的热点话题。",
            "controversies": [
                f"{keyword}的{aspect}引发不同观点碰撞",
                "相关政策和措施的有效性存在争议",
                "公众对事件真相的知情权与隐私保护的平衡"
            ],
            "viewpoints": {
                "支持方": f"认为{keyword}在{aspect}方面具有积极意义",
                "质疑方": f"对{keyword}的{aspect}表示担忧",
                "中立观点": "建议理性看待，等待更多信息"
            },
            "deep_analysis": f"{keyword}的走红反映了当下社会对{aspect}的高度关注。",
            "trends": "预计该话题将持续发酵，相关讨论将更加深入。",
            "writing_angles": [
                f"从{aspect}角度解读{keyword}的社会意义",
                f"{keyword}背后的{aspect}逻辑分析",
                "对比国内外类似事件的处理方式",
                "探讨事件对相关行业/领域的影响"
            ]
        }

    async def generate_article_outline(
        self,
        topic_title: str,
        topic_keyword: str,
        topic_aspect: str,
        category: str,
        article_type: str = "评论",
        word_count: int = 1500
    ) -> Dict[str, Any]:
        """
        基于热点生成文章大纲
        """
        prompt = f"""请为以下热点话题生成一篇文章大纲：

话题标题: {topic_title}
核心关键词: {topic_keyword}
分析角度: {topic_aspect}
所属分类: {category}
文章类型: {article_type}
目标字数: {word_count}字

请生成包含以下要素的大纲：
1. 文章标题（3个备选）
2. 文章导语
3. 主要章节（3-5个）
4. 每个章节的关键点
5. 结尾建议
6. 写作风格建议

请以JSON格式输出。"""

        try:
            response = await self.llm_service.generate(prompt, max_tokens=1500)

            # 尝试解析JSON
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    outline = json.loads(json_match.group())
                else:
                    outline = self._parse_outline_text(response)
            except json.JSONDecodeError:
                outline = self._parse_outline_text(response)

            return {
                "topic_title": topic_title,
                "article_type": article_type,
                "word_count": word_count,
                "outline": outline
            }

        except Exception as e:
            return {
                "topic_title": topic_title,
                "error": str(e),
                "outline": self._get_default_outline(topic_title, topic_keyword, article_type)
            }

    def _parse_outline_text(self, text: str) -> Dict[str, Any]:
        """从文本中解析大纲"""
        outline = {
            "titles": [],
            "introduction": "",
            "sections": [],
            "conclusion": "",
            "style": ""
        }

        lines = text.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "标题" in line[:10]:
                current_section = "titles"
            elif "导语" in line[:10] or "引言" in line[:10]:
                current_section = "introduction"
            elif line.startswith("第") and "章" in line[:10]:
                current_section = "sections"
                outline["sections"].append({
                    "title": line,
                    "points": []
                })
            elif line.startswith("-") or line.startswith("•"):
                if current_section == "sections" and outline["sections"]:
                    outline["sections"][-1]["points"].append(line.strip("- •"))
            elif "结尾" in line[:10] or "结语" in line[:10]:
                current_section = "conclusion"
            elif "风格" in line[:10]:
                current_section = "style"

        return outline

    def _get_default_outline(self, title: str, keyword: str, article_type: str) -> Dict[str, Any]:
        """获取默认大纲"""
        return {
            "titles": [
                f"深度解读：{title}",
                f"{keyword}现象：我们该如何看待？",
                f"从{keyword}看当下社会的变与不变"
            ],
            "introduction": f"近期{keyword}成为热议话题，引发社会各界广泛关注。",
            "sections": [
                {
                    "title": "一、事件回顾与背景",
                    "points": ["梳理事件发展脉络", "分析事件产生的背景因素"]
                },
                {
                    "title": "二、核心争议点分析",
                    "points": ["提炼主要争议焦点", "分析不同观点的立场"]
                },
                {
                    "title": "三、深层原因探讨",
                    "points": ["挖掘现象背后的社会根源", "探讨制度性因素"]
                },
                {
                    "title": "四、影响与启示",
                    "points": ["分析对相关领域的影响", "总结经验教训"]
                }
            ],
            "conclusion": "总结全文观点，提出建设性意见。",
            "style": "客观理性、深入浅出、有理有据"
        }

    async def generate_article_stream(
        self,
        topic_title: str,
        topic_keyword: str,
        topic_aspect: str,
        category: str,
        outline: Dict[str, Any],
        article_type: str = "评论",
        word_count: int = 1500,
        style: str = "专业"
    ):
        """
        流式生成热点文章
        """
        prompt = f"""请根据以下信息创作一篇热点文章：

话题标题: {topic_title}
核心关键词: {topic_keyword}
分析角度: {topic_aspect}
所属分类: {category}
文章类型: {article_type}
目标字数: {word_count}字
写作风格: {style}

大纲:
{json.dumps(outline, ensure_ascii=False, indent=2)}

写作要求：
1. 标题要吸引人，能引发读者点击欲望
2. 开头要抓人，快速进入主题
3. 观点要明确，论证要有力
4. 结合热点，有新鲜感和时效性
5. 语言流畅，符合新媒体阅读习惯
6. 适当使用小标题，增强可读性
7. 结尾要有力，给读者留下思考空间

格式要求（Markdown）：
- 全文只用一个 # 作为文章大标题
- 章节标题使用 ##
- 子章节使用 ###
- 不要在正文段落中使用 # 标记
- 段落之间空一行

请开始创作："""

        async for chunk in self.llm_service.generate_stream(prompt, max_tokens=word_count * 2):
            yield chunk

    def get_categories(self) -> List[Dict[str, str]]:
        """获取所有热点分类"""
        return [
            {"id": cat, "name": cat, "description": f"{cat}类热点话题"}
            for cat in self.TOPIC_CATEGORIES.keys()
        ]
