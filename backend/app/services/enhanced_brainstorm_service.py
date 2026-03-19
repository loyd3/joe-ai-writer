"""
增强版脑洞写作服务
提供更多创意模式和更智能的创意生成
"""
import json
import re
import random
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from app.services.llm_service import LLMService


class EnhancedBrainstormService:
    """增强版脑洞写作服务"""

    # 创意模式定义
    CREATIVE_MODES = {
        "random": {
            "name": "随机脑洞",
            "description": "完全随机的创意组合，突破常规思维",
            "icon": "🎲",
            "color": "#FF6B6B"
        },
        "crossover": {
            "name": "跨界融合",
            "description": "将不同领域的概念进行融合创新",
            "icon": "🔄",
            "color": "#4ECDC4"
        },
        "whatif": {
            "name": "What If",
            "description": "假设性思考，探索可能性边界",
            "icon": "❓",
            "color": "#45B7D1"
        },
        "reverse": {
            "name": "逆向思维",
            "description": "从相反角度思考问题",
            "icon": "🔄",
            "color": "#96CEB4"
        },
        "analogy": {
            "name": "类比联想",
            "description": "通过类比产生新创意",
            "icon": "🔗",
            "color": "#FFEAA7"
        },
        "extreme": {
            "name": "极端化",
            "description": "将特征推向极端产生创意",
            "icon": "⚡",
            "color": "#DDA0DD"
        },
        "combination": {
            "name": "组合创新",
            "description": "将多个元素组合产生新创意",
            "icon": "➕",
            "color": "#98D8C8"
        },
        "constraint": {
            "name": "约束创新",
            "description": "在限制条件下寻找创新方案",
            "icon": "🔒",
            "color": "#F7DC6F"
        }
    }

    # 创意元素库
    CREATIVE_ELEMENTS = {
        "人物": ["时间旅行者", "失忆侦探", "会说话的猫", "机器人哲学家", "梦境编织者",
               "透明人", "记忆商人", "情绪收藏家", "平行世界来客", "文字魔法师"],
        "场景": ["漂浮图书馆", "倒悬城市", "时间尽头的咖啡馆", "梦境交易所",
               "记忆回收站", "彩虹尽头的驿站", "云朵农场", "镜子迷宫", "遗忘之海"],
        "物品": ["能预知未来的怀表", "写满秘密的日记", "会唱歌的钥匙", "储存记忆的瓶子",
               "通往平行世界的门", "实现愿望的硬币", "记录梦境的相机", "暂停时间的沙漏"],
        "情境": ["世界突然失去了颜色", "所有人开始说真话", "时间开始倒流", "梦境成为现实",
               "记忆可以被交易", "影子有了独立意识", "文字从书中逃逸", "重力突然消失"],
        "主题": ["identity", "time", "memory", "choice", "connection", "loss", "discovery", "transformation"]
    }

    # 创意提示词模板
    PROMPT_TEMPLATES = {
        "random": """请基于以下随机元素生成一个创意脑洞：
人物: {element1}
场景: {element2}
物品: {element3}
情境: {element4}

要求：
1. 生成一个独特的故事概念
2. 包含标题、核心设定、主要冲突
3. 提供3个可能的发展方向
4. 给出写作建议

请以JSON格式输出。""",

        "crossover": """请将以下两个不同领域的概念进行融合创新：
领域A: {element1}
领域B: {element2}

要求：
1. 找到两个领域的连接点
2. 生成一个跨界创意概念
3. 说明融合的逻辑和新颖性
4. 提供应用场景或故事框架

请以JSON格式输出。""",

        "whatif": """请基于以下假设进行What If思考：
假设: {element1}

要求：
1. 分析这个假设实现后的连锁反应
2. 生成3个不同的发展分支
3. 每个分支包含：世界变化、人物影响、潜在冲突
4. 提供最有潜力的方向建议

请以JSON格式输出。""",

        "reverse": """请从相反角度思考以下概念：
原概念: {element1}

要求：
1. 找出原概念的核心假设
2. 反转这些假设
3. 生成基于反转假设的新概念
4. 分析这种逆向思维的价值

请以JSON格式输出。""",

        "analogy": """请通过类比联想生成创意：
源概念: {element1}
类比对象: {element2}

要求：
1. 分析源概念和类比对象的相似点
2. 通过类比产生新的洞察或创意
3. 生成具体的应用场景
4. 提供类比思维的拓展方向

请以JSON格式输出。""",

        "extreme": """请将以下概念推向极端：
概念: {element1}
特征: {element2}

要求：
1. 将该特征推向极致
2. 分析极端化后的影响和后果
3. 生成基于极端化的故事或应用场景
4. 提供平衡极端与现实的建议

请以JSON格式输出。""",

        "combination": """请将以下元素进行组合创新：
元素1: {element1}
元素2: {element2}
元素3: {element3}

要求：
1. 找到元素间的潜在联系
2. 生成一个有机融合的新概念
3. 说明组合的创新性和可行性
4. 提供具体的发展建议

请以JSON格式输出。""",

        "constraint": """请在以下约束条件下寻找创新方案：
约束条件: {element1}
目标: {element2}

要求：
1. 分析约束条件带来的限制
2. 在限制中寻找创新的突破口
3. 生成3个不同的解决方案
4. 评估每个方案的创新性和可行性

请以JSON格式输出。"""
    }

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def get_creative_modes(self) -> List[Dict[str, Any]]:
        """获取所有创意模式"""
        return [
            {"id": key, **value}
            for key, value in self.CREATIVE_MODES.items()
        ]

    def get_random_elements(self, count: int = 4) -> List[str]:
        """获取随机创意元素"""
        elements = []
        categories = list(self.CREATIVE_ELEMENTS.keys())

        for _ in range(count):
            category = random.choice(categories)
            element = random.choice(self.CREATIVE_ELEMENTS[category])
            elements.append(f"{category}:{element}")

        return elements

    async def generate_idea(
        self,
        mode: str = "random",
        keywords: Optional[List[str]] = None,
        count: int = 3
    ) -> Dict[str, Any]:
        """
        生成创意脑洞
        """
        if mode not in self.CREATIVE_MODES:
            mode = "random"

        # 获取创意元素
        if keywords and len(keywords) > 0:
            elements = keywords[:4]
            # 如果关键词不够，补充随机元素
            while len(elements) < 4:
                elements.append(random.choice(self.get_random_elements(1)))
        else:
            elements = self.get_random_elements(4)

        # 构建提示词
        template = self.PROMPT_TEMPLATES.get(mode, self.PROMPT_TEMPLATES["random"])

        # 根据模式填充元素
        element_values = [e.split(":")[-1] if ":" in e else e for e in elements]

        if mode == "random":
            prompt = template.format(
                element1=element_values[0],
                element2=element_values[1],
                element3=element_values[2],
                element4=element_values[3]
            )
        elif mode in ["crossover", "analogy"]:
            prompt = template.format(
                element1=element_values[0],
                element2=element_values[1]
            )
        elif mode == "whatif":
            prompt = template.format(element1=element_values[0])
        elif mode == "reverse":
            prompt = template.format(element1=element_values[0])
        elif mode == "extreme":
            prompt = template.format(
                element1=element_values[0],
                element2=element_values[1]
            )
        elif mode == "combination":
            prompt = template.format(
                element1=element_values[0],
                element2=element_values[1],
                element3=element_values[2]
            )
        elif mode == "constraint":
            prompt = template.format(
                element1=element_values[0],
                element2=element_values[1]
            )
        else:
            prompt = template.format(
                element1=element_values[0],
                element2=element_values[1],
                element3=element_values[2],
                element4=element_values[3]
            )

        try:
            response = await self.llm_service.generate(prompt, max_tokens=1500)

            # 尝试解析JSON
            ideas = self._parse_ideas(response, mode, elements)

            return {
                "success": True,
                "mode": mode,
                "mode_info": self.CREATIVE_MODES[mode],
                "elements": elements,
                "ideas": ideas[:count],
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            # 返回默认创意
            return {
                "success": True,
                "mode": mode,
                "mode_info": self.CREATIVE_MODES[mode],
                "elements": elements,
                "ideas": self._get_default_ideas(mode, elements)[:count],
                "generated_at": datetime.now().isoformat()
            }

    def _parse_ideas(self, response: str, mode: str, elements: List[str]) -> List[Dict[str, Any]]:
        """解析AI返回的创意"""
        ideas = []

        try:
            # 尝试解析JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                # 处理不同的返回格式
                if isinstance(data, list):
                    ideas = data
                elif isinstance(data, dict):
                    if "ideas" in data:
                        ideas = data["ideas"]
                    else:
                        ideas = [data]
            else:
                # 文本解析
                ideas = self._parse_ideas_from_text(response)
        except json.JSONDecodeError:
            ideas = self._parse_ideas_from_text(response)

        # 确保每个创意有必要的字段
        for i, idea in enumerate(ideas):
            if isinstance(idea, str):
                ideas[i] = {
                    "title": f"创意 {i+1}",
                    "content": idea,
                    "tags": []
                }
            else:
                ideas[i] = {
                    "title": idea.get("title", f"创意 {i+1}"),
                    "content": idea.get("content", idea.get("concept", idea.get("description", ""))),
                    "concept": idea.get("concept", ""),
                    "setting": idea.get("setting", ""),
                    "conflict": idea.get("conflict", ""),
                    "directions": idea.get("directions", []),
                    "suggestions": idea.get("suggestions", []),
                    "tags": idea.get("tags", [e.split(":")[0] if ":" in e else "创意" for e in elements[:2]])
                }

        return ideas

    def _parse_ideas_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中解析创意"""
        ideas = []

        # 简单的段落分割
        sections = text.split("\n\n")
        current_idea = {}

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # 检测新创意开始
            if section.startswith("创意") or section.startswith("#") or section.startswith("标题"):
                if current_idea:
                    ideas.append(current_idea)
                current_idea = {"title": section.replace("#", "").strip(), "content": ""}
            elif "概念" in section[:10] or "设定" in section[:10]:
                current_idea["concept"] = section
            elif "冲突" in section[:10]:
                current_idea["conflict"] = section
            elif "方向" in section[:10]:
                current_idea["directions"] = [line.strip("- ") for line in section.split("\n") if line.strip().startswith("-")]
            else:
                if "content" in current_idea:
                    current_idea["content"] += "\n" + section
                else:
                    current_idea["content"] = section

        if current_idea:
            ideas.append(current_idea)

        return ideas if ideas else [{"title": "创意", "content": text}]

    def _get_default_ideas(self, mode: str, elements: List[str]) -> List[Dict[str, Any]]:
        """获取默认创意"""
        element_names = [e.split(":")[-1] if ":" in e else e for e in elements]

        return [
            {
                "title": f"{element_names[0]}的奇妙冒险",
                "content": f"在一个{element_names[1]}的世界里，{element_names[0]}发现了{element_names[2]}，从而引发了一系列不可思议的事件。",
                "concept": f"{element_names[0]} + {element_names[1]} + {element_names[2]}",
                "setting": element_names[1],
                "conflict": f"{element_names[0]}如何运用{element_names[2]}应对{element_names[3]}",
                "directions": [
                    "探索世界观的深度设定",
                    "挖掘人物内心的成长弧线",
                    "构建复杂的势力对抗"
                ],
                "suggestions": [
                    "注重世界观的细节刻画",
                    "保持设定的内在一致性",
                    "在奇幻中体现人性真实"
                ],
                "tags": ["奇幻", "冒险", "创意"]
            },
            {
                "title": f"当{element_names[0]}遇见{element_names[1]}",
                "content": f"这是一个关于相遇与改变的故事。{element_names[0]}原本平静的生活因为{element_names[1]}而彻底改变。",
                "concept": f"相遇改变人生",
                "setting": f"现实与{element_names[1]}的交界",
                "conflict": f"适应新环境还是回归旧生活",
                "directions": [
                    "温情治愈路线",
                    "悬疑探索路线",
                    "喜剧冲突路线"
                ],
                "suggestions": [
                    "突出人物关系的微妙变化",
                    "在冲突中展现人物性格",
                    "设置令人印象深刻的场景"
                ],
                "tags": ["情感", "成长", "相遇"]
            },
            {
                "title": f"{element_names[2]}的秘密",
                "content": f"{element_names[2]}隐藏着不为人知的秘密。{element_names[0]}在追寻真相的过程中，逐渐揭开了{element_names[3]}的真相。",
                "concept": f"追寻真相的悬疑故事",
                "setting": f"充满谜团的{element_names[1]}",
                "conflict": f"真相与谎言的对抗",
                "directions": [
                    "层层递进的解谜过程",
                    "出人意料的真相揭示",
                    "道德困境的艰难抉择"
                ],
                "suggestions": [
                    "设置合理的线索铺垫",
                    "控制信息释放的节奏",
                    "结局要有冲击力"
                ],
                "tags": ["悬疑", "解谜", "秘密"]
            }
        ]

    async def expand_idea(
        self,
        idea: Dict[str, Any],
        expansion_type: str = "outline",
        detail_level: str = "standard"
    ) -> Dict[str, Any]:
        """
        扩展创意为完整方案
        """
        prompt = f"""请将以下创意扩展为详细的写作方案：

创意标题: {idea.get('title', '')}
核心概念: {idea.get('concept', idea.get('content', ''))}
故事设定: {idea.get('setting', '')}
主要冲突: {idea.get('conflict', '')}

扩展类型: {expansion_type}
详细程度: {detail_level}

请提供：
1. 详细的故事大纲（起承转合）
2. 主要人物设定（3-5个核心人物）
3. 关键场景设计（3-5个重要场景）
4. 情节发展时间线
5. 主题与象征意义
6. 写作风格建议
7. 可能的难点与解决方案

请以JSON格式输出。"""

        try:
            response = await self.llm_service.generate(prompt, max_tokens=2000)

            # 解析扩展内容
            expansion = self._parse_expansion(response)

            return {
                "success": True,
                "original_idea": idea,
                "expansion_type": expansion_type,
                "detail_level": detail_level,
                "expansion": expansion,
                "expanded_at": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_idea": idea
            }

    def _parse_expansion(self, response: str) -> Dict[str, Any]:
        """解析扩展内容"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        # 默认结构
        return {
            "outline": response[:500] if len(response) > 500 else response,
            "characters": [],
            "scenes": [],
            "timeline": "",
            "themes": "",
            "style_suggestions": [],
            "challenges": []
        }

    async def generate_content_stream(
        self,
        idea: Dict[str, Any],
        content_type: str = "opening",
        word_count: int = 1000,
        style: str = "creative"
    ) -> AsyncGenerator[str, None]:
        """
        流式生成内容
        """
        prompt = f"""请基于以下创意创作一段内容：

创意标题: {idea.get('title', '')}
核心概念: {idea.get('concept', idea.get('content', ''))}

创作类型: {content_type}
目标字数: {word_count}字
写作风格: {style}

要求：
1. 开头要吸引人，快速抓住读者
2. 保持创意的独特性和新鲜感
3. 语言生动形象，有画面感
4. 情节推进自然流畅
5. 适当设置悬念或冲突

请开始创作："""

        async for chunk in self.llm_service.generate_stream(prompt, max_tokens=word_count * 2):
            yield chunk

    def remix_ideas(self, ideas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        混合多个创意生成新创意
        """
        if len(ideas) < 2:
            return ideas[0] if ideas else {}

        # 提取元素进行混合
        titles = [i.get('title', '') for i in ideas]
        concepts = [i.get('concept', i.get('content', '')) for i in ideas]
        settings = [i.get('setting', '') for i in ideas if i.get('setting')]
        conflicts = [i.get('conflict', '') for i in ideas if i.get('conflict')]

        # 生成混合创意
        return {
            "title": f"融合：{titles[0][:10]}...",
            "content": f"将{len(ideas)}个创意元素融合，创造全新故事。",
            "concept": f"融合概念: {' + '.join(concepts[:2])}",
            "setting": settings[0] if settings else "多元融合世界",
            "conflict": conflicts[0] if conflicts else "多重冲突交织",
            "source_ideas": [i.get('id', i.get('title', '')) for i in ideas],
            "is_remixed": True,
            "tags": list(set([tag for i in ideas for tag in i.get('tags', [])]))
        }
