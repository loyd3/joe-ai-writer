"""
脑洞写作服务 - 基于网络流行脑洞和创意话题生成文章
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
import json
import re

from app.core.ai_client import ai_client
from app.services.hot_topics_service import HotTopicsService


# 脑洞话题分类和提示词模板
BRAINSTORM_CATEGORIES = {
    "科幻脑洞": {
        "description": "科幻设定、未来世界、外星文明、时间旅行等",
        "prompt_templates": [
            "如果{concept}，世界会变成什么样？",
            "假设{concept}，人类社会会如何演变？",
            "当{concept}发生时，普通人该如何应对？",
            "{concept}：一个改变人类命运的发现",
        ],
        "examples": [
            "人类发现可以上传意识到云端",
            "时间旅行成为普通人的日常通勤方式",
            "地球接收到来自4光年外的信号",
            "科学家发现灵魂确实存在且有重量",
            "人类可以冬眠，一觉睡到100年后",
        ]
    },
    "历史脑洞": {
        "description": "历史改写、平行时空、古人穿越等",
        "prompt_templates": [
            "如果{concept}，历史会如何改写？",
            "当{concept}，那个时代的人们会怎么想？",
            "{concept}：一个改变历史走向的决定",
        ],
        "examples": [
            "秦始皇得到了一本《世界地图》",
            "诸葛亮拥有无限量的方便面",
            "唐朝开通了直达欧洲的铁路",
            "郑和船队发现了美洲大陆",
            "李白穿越到现代成为网红诗人",
        ]
    },
    "生活脑洞": {
        "description": "日常生活、职场、校园、家庭的奇思妙想",
        "prompt_templates": [
            "如果{concept}，生活会变成什么样？",
            "当{concept}，你会怎么选择？",
            "{concept}：现代人的真实写照",
        ],
        "examples": [
            "每个人的头顶都显示着真实年龄",
            "说谎时身体会发出红光",
            "可以把自己的记忆卖给他人",
            "梦境可以被录制和回放",
            "每个人的运气值可视化显示",
        ]
    },
    "社会脑洞": {
        "description": "社会现象、人际关系、群体行为的另类思考",
        "prompt_templates": [
            "如果{concept}，社会规则会如何改变？",
            "当{concept}，人与人之间的关系会怎样？",
            "{concept}：一个关于人性的实验",
        ],
        "examples": [
            "每个人的存款数额公开透明",
            "人类可以交易自己的寿命",
            "颜值成为法定货币",
            "知识可以直接下载到大脑",
            "情绪可以被当作商品买卖",
        ]
    },
    "职场脑洞": {
        "description": "职场趣事、工作方式、职业发展的创意设想",
        "prompt_templates": [
            "如果{concept}，职场会变成什么样？",
            "当{concept}，打工人该如何生存？",
            "{concept}：职场人的终极幻想",
        ],
        "examples": [
            "工作效率和工资完全成正比",
            "老板的想法会实时显示在头顶",
            "加班时间可以兑换假期或金钱",
            "每个人的专业能力有等级显示",
            "辞职需要经过全公司投票",
        ]
    },
    "情感脑洞": {
        "description": "爱情、友情、亲情的另类解读",
        "prompt_templates": [
            "如果{concept}，爱情会变成什么样？",
            "当{concept}，你会如何面对感情？",
            "{concept}：关于爱的另一种可能",
        ],
        "examples": [
            "每个人一生只能爱一个人",
            "分手后记忆可以选择性删除",
            "真爱出现时会有特殊标记",
            "可以预览和某人的未来十年",
            "暗恋一个人对方会收到通知",
        ]
    },
    "动物脑洞": {
        "description": "动物拟人、人与动物互换视角",
        "prompt_templates": [
            "如果{concept}，世界会怎样？",
            "当{concept}，会发生什么有趣的事？",
            "{concept}：来自另一个视角的观察",
        ],
        "examples": [
            "猫和狗可以开口说话",
            "人类和宠物可以互换身体一天",
            "动物们建立了自己的互联网",
            "宠物可以给自己的主人打分",
            "野生动物开始收门票让人类参观",
        ]
    },
    "科技脑洞": {
        "description": "科技产品、AI、互联网相关的创意设想",
        "prompt_templates": [
            "如果{concept}，科技生活会变成什么样？",
            "当{concept}，我们会失去什么，得到什么？",
            "{concept}：技术发展的双刃剑",
        ],
        "examples": [
            "手机可以读取主人的心情",
            "AI助手有了自己的小情绪",
            "社交媒体点赞可以兑换现金",
            "每个人的搜索历史完全公开",
            "虚拟现实成为法定婚姻场所",
        ]
    },
}


# 网络流行梗和热门脑洞
TRENDING_BRAINSTORMS = [
    {"title": "如果古人有朋友圈，他们会发什么？", "category": "历史脑洞", "heat": 9999},
    {"title": "当你的猫突然开口说人话", "category": "动物脑洞", "heat": 8888},
    {"title": "假如颜值可以当钱花", "category": "社会脑洞", "heat": 7777},
    {"title": "如果时间可以存银行", "category": "科幻脑洞", "heat": 7666},
    {"title": "当老板的想法实时显示在头顶", "category": "职场脑洞", "heat": 7555},
    {"title": "如果梦境可以发朋友圈", "category": "生活脑洞", "heat": 7444},
    {"title": "当AI开始吐槽人类", "category": "科技脑洞", "heat": 7333},
    {"title": "如果分手可以像退快递一样简单", "category": "情感脑洞", "heat": 7222},
    {"title": "当动物们开始写 Yelp 评价", "category": "动物脑洞", "heat": 7111},
    {"title": "假如知识可以直接下载", "category": "科幻脑洞", "heat": 7000},
    {"title": "如果每个人的运气值可视化", "category": "生活脑洞", "heat": 6888},
    {"title": "当秦始皇收到世界地图", "category": "历史脑洞", "heat": 6777},
    {"title": "如果社交媒体点赞可以换钱", "category": "科技脑洞", "heat": 6666},
    {"title": "当打工人有了超能力", "category": "职场脑洞", "heat": 6555},
    {"title": "如果灵魂真的有重量", "category": "科幻脑洞", "heat": 6444},
    {"title": "当宠物开始给主人打分", "category": "动物脑洞", "heat": 6333},
    {"title": "如果暗恋会自动发送通知", "category": "情感脑洞", "heat": 6222},
    {"title": "当古人穿越到现代职场", "category": "历史脑洞", "heat": 6111},
    {"title": "如果记忆可以买卖", "category": "社会脑洞", "heat": 6000},
    {"title": "当AI成为你的恋爱顾问", "category": "科技脑洞", "heat": 5888},
]


class BrainstormWritingService:
    """脑洞写作服务"""
    
    @staticmethod
    def get_categories() -> List[Dict[str, str]]:
        """获取所有脑洞分类"""
        return [
            {"key": key, "name": key, "description": info["description"]}
            for key, info in BRAINSTORM_CATEGORIES.items()
        ]
    
    @staticmethod
    def get_trending_brainstorms(limit: int = 20) -> List[Dict[str, Any]]:
        """获取热门脑洞话题"""
        sorted_brainstorms = sorted(TRENDING_BRAINSTORMS, key=lambda x: x["heat"], reverse=True)
        return sorted_brainstorms[:limit]
    
    @staticmethod
    def generate_random_brainstorm(category: Optional[str] = None) -> Dict[str, Any]:
        """生成随机脑洞话题"""
        if category and category in BRAINSTORM_CATEGORIES:
            cat_info = BRAINSTORM_CATEGORIES[category]
        else:
            category = random.choice(list(BRAINSTORM_CATEGORIES.keys()))
            cat_info = BRAINSTORM_CATEGORIES[category]
        
        # 随机选择一个示例和模板
        concept = random.choice(cat_info["examples"])
        template = random.choice(cat_info["prompt_templates"])
        
        title = template.format(concept=concept)
        
        return {
            "title": title,
            "category": category,
            "concept": concept,
            "description": cat_info["description"],
            "heat": random.randint(5000, 9999)
        }
    
    @staticmethod
    def generate_brainstorm_from_hot_topic(hot_topic: Dict[str, Any]) -> Dict[str, Any]:
        """基于热点话题生成脑洞"""
        title = hot_topic.get("title", "")
        
        # 根据热点内容选择合适的脑洞方向
        brainstorm_types = [
            ("如果这件事发生在古代，会有什么不同？", "历史脑洞"),
            ("如果这件事被外星人观察到，他们会怎么想？", "科幻脑洞"),
            ("如果这件事可以被交易，值多少钱？", "社会脑洞"),
            ("如果这件事有超能力加持，会变成什么样？", "科幻脑洞"),
            ("如果这件事被拍成电影，剧情会如何发展？", "生活脑洞"),
            ("如果这件事发生在动物世界，会怎样？", "动物脑洞"),
            ("如果这件事可以被AI预测，我们会怎么做？", "科技脑洞"),
        ]
        
        template, category = random.choice(brainstorm_types)
        brainstorm_title = f"{title}｜{template}"
        
        return {
            "title": brainstorm_title,
            "category": category,
            "original_topic": title,
            "source": hot_topic.get("source", "热点"),
            "heat": hot_topic.get("heat", 5000)
        }
    
    @staticmethod
    async def generate_outline(
        brainstorm: Dict[str, Any],
        style: str = "幽默风趣",
        word_count: str = "medium",
        db=None
    ) -> Dict[str, Any]:
        """
        为脑洞话题生成文章大纲
        """
        title = brainstorm.get("title", "")
        category = brainstorm.get("category", "脑洞")
        
        # 构建提示词
        prompt = f"""请为以下脑洞话题生成一个有趣的文章大纲：

话题：{title}
类型：{category}
写作风格：{style}

要求：
1. 大纲要有创意，角度新颖
2. 包含3-5个主要部分
3. 每个部分有2-3个要点
4. 整体结构要有起承转合
5. 可以适当加入幽默元素

请以JSON格式返回，包含以下字段：
- title: 文章标题（可以比原话题更有吸引力）
- sections: 章节列表，每个章节包含 name（章节名）和 points（要点列表）
- keywords: 关键词列表
- angle: 写作角度简述
"""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            # 调用写作服务生成大纲
            content = await ai_client.chat_completion(
                messages=messages,
                temperature=0.8,
            )
            
            # 尝试解析JSON
            try:
                # 提取JSON部分
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    outline = json.loads(json_match.group())
                else:
                    outline = json.loads(content)
                
                # 确保必要字段存在
                if "title" not in outline:
                    outline["title"] = title
                if "sections" not in outline:
                    outline["sections"] = []
                if "keywords" not in outline:
                    outline["keywords"] = []
                    
                return outline
                
            except json.JSONDecodeError:
                # 如果解析失败，返回结构化数据
                return {
                    "title": title,
                    "sections": [
                        {"name": "引言", "points": ["引入话题", "设置悬念"]},
                        {"name": "主体展开", "points": ["多角度分析", "举例说明"]},
                        {"name": "深度思考", "points": ["引申意义", "现实联系"]},
                        {"name": "结尾", "points": ["总结升华", "开放思考"]},
                    ],
                    "keywords": [category, "脑洞", "创意"],
                    "angle": "从独特视角解读话题",
                    "raw_content": content
                }
                
        except Exception as e:
            print(f"[Brainstorm] 生成大纲失败: {e}")
            return {
                "title": title,
                "sections": [
                    {"name": "引言", "points": [f"介绍{title}的背景", "引发读者兴趣"]},
                    {"name": "脑洞展开", "points": ["详细描述假设情景", "分析可能的影响"]},
                    {"name": "现实对照", "points": ["与现实的对比", "引发的思考"]},
                    {"name": "结语", "points": ["总结观点", "留给读者的思考"]},
                ],
                "keywords": [category, "脑洞", "创意写作"],
                "angle": "假设性思考"
            }
    
    @staticmethod
    async def generate_article(
        brainstorm: Dict[str, Any],
        outline: Optional[Dict[str, Any]] = None,
        style: str = "幽默风趣",
        word_count: str = "medium",
        db=None
    ) -> Dict[str, Any]:
        """
        根据脑洞话题生成完整文章
        """
        title = brainstorm.get("title", "")
        category = brainstorm.get("category", "脑洞")
        
        # 如果没有提供大纲，先生成
        if outline is None:
            outline = await BrainstormWritingService.generate_outline(
                brainstorm, style, word_count, db
            )
        
        # 确定字数
        word_count_map = {
            "short": "800-1000",
            "medium": "1500-2000",
            "long": "2500-3000"
        }
        target_words = word_count_map.get(word_count, "1500-2000")
        
        # 构建大纲文本
        outline_text = ""
        for section in outline.get("sections", []):
            outline_text += f"\n## {section.get('name', '')}\n"
            for point in section.get('points', []):
                outline_text += f"- {point}\n"
        
        # 构建写作提示词
        prompt = f"""请根据以下脑洞话题和大纲，创作一篇有趣的文章。

话题：{title}
类型：{category}
写作风格：{style}
目标字数：{target_words}字

大纲：
{outline_text}

写作要求：
1. 文章要有趣、有创意，符合"脑洞"风格
2. 可以适当夸张，但要逻辑自洽
3. 语言风格要{style}，吸引读者
4. 适当使用网络流行语和梗
5. 要有起承转合，不能平淡
6. 结尾要有思考或反转

请直接输出文章正文，不需要额外的格式说明。
"""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            content = await ai_client.chat_completion(
                messages=messages,
                temperature=0.85,
            )
            
            return {
                "title": outline.get("title", title),
                "content": content,
                "outline": outline,
                "brainstorm": brainstorm,
                "word_count": len(content),
                "style": style,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[Brainstorm] 生成文章失败: {e}")
            return {
                "title": title,
                "content": f"生成文章时出错: {str(e)}",
                "brainstorm": brainstorm,
                "error": str(e)
            }
    
    @staticmethod
    async def generate_from_hot_topics(
        limit: int = 5,
        style: str = "幽默风趣",
        db=None
    ) -> List[Dict[str, Any]]:
        """
        基于当前热点生成脑洞话题
        """
        # 获取热点
        hot_topics_data = await HotTopicsService.fetch_all_hot_topics()
        hot_topics = hot_topics_data.get("topics", [])[:limit]
        
        brainstorms = []
        for topic in hot_topics:
            brainstorm = BrainstormWritingService.generate_brainstorm_from_hot_topic(topic)
            brainstorms.append(brainstorm)
        
        return brainstorms
