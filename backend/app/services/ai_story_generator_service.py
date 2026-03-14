"""
AI 故事生成服务 - 根据主题自动生成大纲、角色、情节等
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.ai_client import ai_client
import json
import re

try:
    import json_repair
except ImportError:
    json_repair = None


class AIStoryGeneratorService:
    """AI 故事生成服务 - 一站式创作助手"""

    # 生成完整故事设定的系统提示词
    STORY_GENERATION_PROMPT = """你是一位专业的故事创作顾问和编剧。你的任务是根据用户提供的主题，生成一份完整的故事创作指南，包括大纲、角色设定、情节设计等。

你需要生成以下内容：

1. **故事标题** - 提供3个吸引人的标题选项
2. **故事类型/题材** - 如：科幻、悬疑、爱情、历史、奇幻等
3. **核心主题** - 故事要表达的核心思想
4. **故事大纲** - 包含起承转合的完整结构，分为3-5幕
5. **角色设定** - 主要角色（3-5个）的详细信息
6. **关键情节点** - 推动故事发展的关键事件（5-10个）
7. **世界观设定** - 故事发生的时间、地点、背景规则
8. **写作风格建议** - 适合这个故事的叙述风格

输出格式必须是合法的 JSON：
{
    "title_options": ["标题1", "标题2", "标题3"],
    "genre": "故事类型",
    "core_theme": "核心主题",
    "outline": [
        {
            "act": "第一幕",
            "title": "幕标题",
            "content": "主要内容",
            "word_count_estimate": "预估字数"
        }
    ],
    "characters": [
        {
            "name": "角色名",
            "role": "主角/反派/配角",
            "age": "年龄",
            "appearance": "外貌特征",
            "personality": "性格特点",
            "background": "背景故事",
            "goals": "目标/动机",
            "conflict": "内心冲突"
        }
    ],
    "plot_points": [
        {
            "point": "情节点描述",
            "position": "在故事中的位置",
            "significance": "重要性"
        }
    ],
    "world_building": {
        "time_period": "时代背景",
        "location": "主要地点",
        "rules": "世界规则/设定",
        "atmosphere": "氛围基调"
    },
    "writing_style": {
        "tone": "语气风格",
        "pov": "视角建议",
        "pacing": "节奏建议",
        "techniques": ["推荐的写作技巧"]
    }
}"""

    # 仅生成大纲的提示词
    OUTLINE_ONLY_PROMPT = """你是一位资深的故事大纲设计师。请根据用户提供的主题，生成一个详细的故事大纲。

要求：
1. 将故事分为3-5幕（Act）
2. 每幕包含多个场景（Scene）
3. 标注每个场景的预估字数
4. 说明场景之间的衔接关系
5. 标注高潮点和转折点

输出格式必须是合法的 JSON：
{
    "title": "故事标题",
    "genre": "类型",
    "total_estimate": "总预估字数",
    "acts": [
        {
            "act_number": 1,
            "title": "幕标题",
            "theme": "本幕主题",
            "scenes": [
                {
                    "scene_number": 1,
                    "title": "场景标题",
                    "content": "场景内容简述",
                    "characters": ["出场角色"],
                    "word_count": 预估字数,
                    "significance": "重要性说明",
                    "climax": false
                }
            ]
        }
    ],
    "key_moments": [
        {
            "type": "转折点/高潮/悬念",
            "position": "位置（如：第一幕结尾）",
            "description": "描述"
        }
    ]
}"""

    # 生成角色的提示词
    CHARACTERS_PROMPT = """你是一位角色设计专家。请根据用户提供的主题，设计3-5个有深度、有冲突的角色。

每个角色应包含：
- 基本信息（姓名、年龄、外貌）
- 性格特点（优点、缺点）
- 背景故事（成长经历、关键事件）
- 目标与动机（想要什么、为什么想要）
- 内心冲突（矛盾、恐惧、挣扎）
- 与其他角色的关系

输出格式必须是合法的 JSON：
{
    "protagonist": {
        "name": "主角姓名",
        "age": "年龄",
        "appearance": "外貌描述",
        "personality": {"strengths": ["优点"], "weaknesses": ["缺点"]},
        "background": "背景故事",
        "goals": "目标",
        "internal_conflict": "内心冲突",
        "arc": "角色成长弧线"
    },
    "antagonist": {
        "name": "反派姓名",
        ...
    },
    "supporting": [
        {
            "name": "配角姓名",
            "role": "在故事中的作用",
            "relationship_to_protagonist": "与主角关系"
        }
    ]
}"""

    @staticmethod
    async def generate_full_story(
        theme: str,
        genre: Optional[str] = None,
        word_count: int = 5000,
        additional_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据主题生成完整的故事设定

        Args:
            theme: 故事主题/核心概念
            genre: 故事类型（可选）
            word_count: 目标字数
            additional_requirements: 额外要求
        """
        user_prompt = f"""请为以下主题生成完整的故事创作指南：

主题：{theme}
目标字数：{word_count}字
{f'故事类型：{genre}' if genre else ''}
{f'额外要求：{additional_requirements}' if additional_requirements else ''}

请确保输出是合法的 JSON 格式。"""

        messages = [
            {"role": "system", "content": AIStoryGeneratorService.STORY_GENERATION_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await ai_client.chat_completion(messages, timeout=120.0)

            # 尝试解析 JSON
            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            story_data = json.loads(json_str.strip())
            story_data["input_theme"] = theme
            story_data["target_word_count"] = word_count

            return story_data

        except json.JSONDecodeError as e:
            return {
                "error": "故事生成失败，AI返回格式不正确",
                "raw_response": response,
                "parse_error": str(e)
            }
        except Exception as e:
            return {
                "error": f"故事生成失败: {str(e)}"
            }

    @staticmethod
    async def generate_outline_only(
        theme: str,
        genre: Optional[str] = None,
        acts: int = 3,
        word_count: int = 5000
    ) -> Dict[str, Any]:
        """仅生成故事大纲"""
        user_prompt = f"""请为以下主题生成详细的故事大纲：

主题：{theme}
{f'故事类型：{genre}' if genre else ''}
幕数：{acts}幕
目标字数：{word_count}字

请确保输出是合法的 JSON 格式。"""

        messages = [
            {"role": "system", "content": AIStoryGeneratorService.OUTLINE_ONLY_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await ai_client.chat_completion(messages, timeout=60.0)

            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            outline = json.loads(json_str.strip())
            outline["input_theme"] = theme

            return outline

        except json.JSONDecodeError as e:
            return {
                "error": "大纲生成失败",
                "raw_response": response,
                "parse_error": str(e)
            }
        except Exception as e:
            return {
                "error": f"大纲生成失败: {str(e)}"
            }

    @staticmethod
    async def generate_characters(
        theme: str,
        existing_outline: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """生成角色设定"""
        user_prompt = f"""请为以下主题设计角色：

主题：{theme}
{f'已有大纲：{json.dumps(existing_outline, ensure_ascii=False)}' if existing_outline else ''}

请确保输出是合法的 JSON 格式。"""

        messages = [
            {"role": "system", "content": AIStoryGeneratorService.CHARACTERS_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await ai_client.chat_completion(messages, timeout=60.0)

            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            return json.loads(json_str.strip())

        except Exception as e:
            return {"error": f"角色生成失败: {str(e)}"}

    @staticmethod
    async def generate_full_story_stream(
        theme: str,
        genre: Optional[str] = None,
        word_count: int = 5000,
        additional_requirements: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成完整故事设定"""
        user_prompt = f"""请为以下主题生成完整的故事创作指南：

主题：{theme}
目标字数：{word_count}字
{f'故事类型：{genre}' if genre else ''}
{f'额外要求：{additional_requirements}' if additional_requirements else ''}

请确保输出是合法的 JSON 格式。"""

        messages = [
            {"role": "system", "content": AIStoryGeneratorService.STORY_GENERATION_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        # 流式接收时边收边过滤：用状态机在字符串内转义换行/控制字符，得到可供解析的 cleaned_response
        full_response = ""
        cleaned_parts: List[str] = []
        stream_state = {"in_string": False, "escape_next": False}

        def _stream_filter_char(c: str) -> str:
            """在流上逐字符过滤：仅在双引号字符串内把 \\n/\\r 等转为转义形式，便于最后解析"""
            nonlocal stream_state
            in_str = stream_state["in_string"]
            escape = stream_state["escape_next"]
            if escape:
                stream_state["escape_next"] = False
                return c
            if c == "\\" and in_str:
                stream_state["escape_next"] = True
                return c
            if c == '"':
                stream_state["in_string"] = not in_str
                return c
            if in_str and c in "\n\r":
                return "\\n" if c == "\n" else "\\r"
            if in_str and ord(c) in range(0x00, 0x20) and c not in "\t":
                return " "  # 字符串内其它控制字符替换为空格
            return c

        async for chunk in ai_client.stream_completion(messages):
            full_response += chunk
            # 用于下发的预览：只去掉 Markdown 代码块标记
            cleaned_chunk = chunk
            if "```json" in cleaned_chunk:
                cleaned_chunk = cleaned_chunk.replace("```json", "")
            if "```" in cleaned_chunk:
                cleaned_chunk = cleaned_chunk.replace("```", "")
            # 流式过滤：每字符过状态机，得到可用于最终解析的片段
            for char in chunk:
                cleaned_parts.append(_stream_filter_char(char))
            if cleaned_chunk.strip():
                yield json.dumps({"chunk": cleaned_chunk}, ensure_ascii=False)

        cleaned_response = "".join(cleaned_parts)

        # 解析最终 JSON（优先用流式过滤后的 cleaned_response，再配合 json_repair 等容错）
        def _fix_newlines_in_strings(s: str) -> str:
            """把双引号字符串内的真实换行改为 \\n，否则 json.loads 会报 Expecting value"""
            out = []
            i = 0
            in_str = False
            escape = False
            while i < len(s):
                c = s[i]
                if escape:
                    out.append(c)
                    escape = False
                    i += 1
                    continue
                if c == "\\" and in_str:
                    out.append(c)
                    escape = True
                    i += 1
                    continue
                if c == '"':
                    in_str = not in_str
                    out.append(c)
                    i += 1
                    continue
                if in_str and c in "\n\r":
                    out.append("\\n" if c == "\n" else "\\r")
                    i += 1
                    continue
                out.append(c)
                i += 1
            return "".join(out)

        def _parse_story_json(s: str) -> dict:
            s = s.strip()
            if "```json" in s:
                s = s.split("```json")[1].split("```")[0]
            elif "```" in s:
                s = s.split("```")[1].split("```")[0]
            s = s.strip()
            first_error = None
            # 1) 先试 json_repair（能修尾随逗号、截断、未转义换行、注释等）
            if json_repair is not None:
                try:
                    return json_repair.loads(s)
                except Exception as e:
                    first_error = e
            # 2) 再试标准解析 + 简单容错
            s_fixed = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
            s_fixed = _fix_newlines_in_strings(s_fixed)
            s_fixed = re.sub(r",\s*]", "]", s_fixed)
            s_fixed = re.sub(r",\s*}", "}", s_fixed)
            s_fixed = re.sub(r":\s*,", ": null,", s_fixed)
            s_fixed = re.sub(r":\s*}", ": null}", s_fixed)
            s_fixed = re.sub(r":\s*]", ": null]", s_fixed)
            try:
                return json.loads(s_fixed)
            except json.JSONDecodeError as e:
                if first_error is None:
                    first_error = e
            try:
                open_br = s_fixed.count("[") - s_fixed.count("]")
                open_cur = s_fixed.count("{") - s_fixed.count("}")
                s_fixed = s_fixed.rstrip()
                if s_fixed.endswith(","):
                    s_fixed = s_fixed[:-1]
                s_fixed += "]" * max(0, open_br) + "}" * max(0, open_cur)
                return json.loads(s_fixed)
            except json.JSONDecodeError as e:
                if first_error is None:
                    first_error = e
            if first_error is not None:
                raise first_error
            raise ValueError("无法解析故事 JSON")

        try:
            story_data = _parse_story_json(cleaned_response)
            story_data["input_theme"] = theme
            story_data["target_word_count"] = word_count

            # 最后发送完整的数据（仅 payload，API 层加 data: 前缀）
            yield json.dumps({"success": True, "data": story_data}, ensure_ascii=False)
        except json.JSONDecodeError as e:
            yield json.dumps(
                {"success": False, "error": f"故事生成失败，AI返回格式不正确: {str(e)}", "raw_response": full_response[:500]},
                ensure_ascii=False,
            )
        except Exception as e:
            yield json.dumps({"success": False, "error": f"故事生成失败: {str(e)}"}, ensure_ascii=False)

    @staticmethod
    def convert_to_project_memory(story_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将生成的故事数据转换为项目记忆格式
        用于直接保存到项目的 AI 记忆中
        """
        # 转换角色数据格式，确保符合 Character schema
        raw_characters = story_data.get("characters", [])
        converted_characters = []
        
        for char in raw_characters:
            if isinstance(char, dict):
                # 构建 description：组合 role, age, appearance 等信息
                description_parts = []
                if char.get("role"):
                    description_parts.append(f"角色定位：{char['role']}")
                if char.get("age"):
                    description_parts.append(f"年龄：{char['age']}")
                if char.get("appearance"):
                    description_parts.append(f"外貌：{char['appearance']}")
                if char.get("conflict"):
                    description_parts.append(f"内心冲突：{char['conflict']}")
                
                description = "；".join(description_parts) if description_parts else char.get("name", "未命名角色")
                
                converted_characters.append({
                    "name": char.get("name", "未命名角色"),
                    "description": description,
                    "personality": char.get("personality") or char.get("personality", ""),
                    "background": char.get("background", ""),
                    "goals": char.get("goals") or char.get("goal", "")
                })
        
        memory = {
            "outline": story_data.get("outline", []),
            "characters": converted_characters,
            "storyline": story_data.get("core_theme", ""),
            "world_building": story_data.get("world_building", {}),
            "writing_style": story_data.get("writing_style", {}).get("tone", ""),
            "notes": f"""基于主题「{story_data.get('input_theme', '')}」生成的故事设定
类型：{story_data.get('genre', '')}
关键情节点：{json.dumps(story_data.get('plot_points', []), ensure_ascii=False)}"""
        }
        return memory
