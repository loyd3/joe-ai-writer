from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.api.auth import get_current_user
from app.api.projects import check_document_access
from app.models.models import Document, AIMemory
from app.core.ai_client import ai_client
import json

router = APIRouter(prefix="/api/extract", tags=["extract"])

EXTRACTION_PROMPT = """你是一个专业的写作分析助手。请分析以下文本内容，提取关键信息并以JSON格式返回。

请提取以下内容：
1. characters - 文中出现的角色列表，每个角色包含：
   - name: 角色名
   - description: 角色描述（外貌、身份等）
   - personality: 性格特点
   - goals: 目标/动机

2. outline - 文章结构大纲，提取主要章节/段落：
   - title: 章节标题或主要内容概括
   - description: 该部分内容简介

3. key_points - 关键情节点（3-5个）：
   - 每一点是一个字符串描述

4. world_building - 世界观元素（如有）：
   - 以键值对形式返回，如 {"时代背景": "现代都市", "特殊设定": "存在超能力"}

5. writing_style - 写作风格分析（1-2句话）

请严格按照以下JSON格式返回，不要包含其他文字：
{
    "characters": [...],
    "outline": [...],
    "key_points": [...],
    "world_building": {...},
    "writing_style": "..."
}"""

@router.post("/document/{document_id}")
async def extract_from_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """从文档内容自动提取角色、大纲等信息"""
    document = check_document_access(db, document_id, current_user["id"])
    
    # 获取文档内容
    content_text = "\n".join([block.get("content", "") for block in (document.content or [])])
    
    if len(content_text) < 100:
        raise HTTPException(status_code=400, detail="文档内容太短，无法提取有效信息")
    
    try:
        # 调用 AI 分析
        messages = [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"请分析以下文本：\n\n{content_text[:5000]}"}  # 限制长度
        ]
        
        response = await ai_client.chat_completion(messages)
        
        # 解析 JSON 响应
        try:
            extracted_data = json.loads(response)
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                extracted_data = json.loads(response[json_start:json_end])
            else:
                raise HTTPException(status_code=500, detail="AI 返回格式错误")
        
        return {
            "success": True,
            "document_id": document_id,
            "extracted": extracted_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取失败: {str(e)}")

@router.post("/document/{document_id}/apply")
async def apply_extraction(
    document_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """将提取的信息应用到项目设定中"""
    document = check_document_access(db, document_id, current_user["id"])
    
    # 获取或创建 项目设定
    memory = db.query(AIMemory).filter(
        AIMemory.project_id == document.project_id
    ).first()
    
    if not memory:
        memory = AIMemory(project_id=document.project_id)
        db.add(memory)
    
    # 应用提取的数据
    extracted = data.get("extracted", {})
    
    # 合并角色（避免重复）
    if extracted.get("characters"):
        existing_names = {c.get("name") for c in (memory.characters or [])}
        for char in extracted["characters"]:
            if char.get("name") not in existing_names:
                if memory.characters is None:
                    memory.characters = []
                memory.characters.append(char)
    
    # 合并大纲
    if extracted.get("outline"):
        if memory.outline is None:
            memory.outline = []
        # 添加新的大纲项（不重复）
        existing_titles = {item.get("title") for item in memory.outline}
        for item in extracted["outline"]:
            if item.get("title") not in existing_titles:
                memory.outline.append(item)
    
    # 合并关键情节点
    if extracted.get("key_points"):
        if memory.key_points is None:
            memory.key_points = []
        for point in extracted["key_points"]:
            if point not in memory.key_points:
                memory.key_points.append(point)
    
    # 合并世界观
    if extracted.get("world_building"):
        if memory.world_building is None:
            memory.world_building = {}
        memory.world_building.update(extracted["world_building"])
    
    # 写作风格（直接覆盖或追加）
    if extracted.get("writing_style"):
        if memory.writing_style:
            memory.writing_style += f"\n\n{extracted['writing_style']}"
        else:
            memory.writing_style = extracted["writing_style"]
    
    db.commit()
    
    return {
        "success": True,
        "message": "提取信息已应用到项目设定",
        "applied": {
            "characters_count": len(extracted.get("characters", [])),
            "outline_items": len(extracted.get("outline", [])),
            "key_points": len(extracted.get("key_points", []))
        }
    }

@router.post("/analyze-storyline")
async def analyze_storyline(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """分析文档情节发展，生成故事线"""
    document = check_document_access(db, document_id, current_user["id"])
    
    content_text = "\n".join([block.get("content", "") for block in (document.content or [])])
    
    if len(content_text) < 200:
        raise HTTPException(status_code=400, detail="文档内容太短")
    
    prompt = """请分析以下故事内容，梳理出清晰的故事线。按时间顺序描述主要情节发展，包括：
1. 开端 - 故事背景和人物介绍
2. 发展 - 主要事件和冲突
3. 高潮 - 最紧张/关键的时刻
4. 结局 - 目前的结局或进展

请用简洁的段落描述（200-400字）。"""
    
    try:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content_text[:8000]}
        ]
        
        storyline = await ai_client.chat_completion(messages)
        
        # 更新到项目设定
        memory = db.query(AIMemory).filter(
            AIMemory.project_id == document.project_id
        ).first()
        
        if memory:
            memory.storyline = storyline
            db.commit()
        
        return {
            "success": True,
            "storyline": storyline
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@router.post("/suggest-characters")
async def suggest_characters(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """根据已有内容建议新角色"""
    document = check_document_access(db, document_id, current_user["id"])
    
    # 获取已有角色
    memory = db.query(AIMemory).filter(
        AIMemory.project_id == document.project_id
    ).first()
    
    existing_chars = memory.characters if memory and memory.characters else []
    content_text = "\n".join([block.get("content", "") for block in (document.content or [])])
    
    prompt = f"""基于以下故事内容，建议3-5个可以丰富情节的新角色。

已有角色: {[c.get('name') for c in existing_chars]}

要求：
1. 每个角色包含：名称、身份、性格、与主角的关系
2. 角色要有冲突性或互补性
3. 解释该角色可以推动什么情节

以列表形式返回。"""
    
    try:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content_text[:5000]}
        ]
        
        suggestions = await ai_client.chat_completion(messages)
        
        return {
            "success": True,
            "suggestions": suggestions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成建议失败: {str(e)}")
