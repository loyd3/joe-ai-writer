from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.api.auth import get_current_user
from app.api.projects import check_project_owner
from app.models.models import Project, Document, Template, AIMemory
from app.schemas.schemas import TemplateCreate, TemplateResponse, ProjectCreate

router = APIRouter(prefix="/api/templates", tags=["templates"])

# 预置模板数据
DEFAULT_TEMPLATES = [
    {
        "name": "玄幻小说",
        "description": "包含修炼体系、门派势力的玄幻故事模板",
        "category": "novel",
        "icon": "🐉",
        "outline": [
            {"title": "序幕：平凡的开始", "description": "主角的日常生活"},
            {"title": "第一章：命运的转折", "description": "获得机缘或遭遇变故"},
            {"title": "第二章：踏上征途", "description": "离开家乡，开始修炼"},
            {"title": "第三章：初露锋芒", "description": "展现实力，获得认可"},
            {"title": "第四章：强敌环伺", "description": "面临挑战和危机"},
            {"title": "第五章：突破自我", "description": "实力突破，战胜困难"},
            {"title": "终章：巅峰之路", "description": "达到巅峰，守护所爱"}
        ],
        "world_building": {
            "修炼体系": "炼气→筑基→金丹→元婴→化神→渡劫→大乘",
            "门派分布": "正道联盟、魔道势力、中立散修",
            "世界背景": "仙侠世界，灵气充沛，强者为尊"
        },
        "writing_style": "节奏明快，打斗场面描写详细，人物性格鲜明"
    },
    {
        "name": "言情小说",
        "description": "都市爱情故事模板，甜蜜虐心皆可",
        "category": "novel",
        "icon": "💕",
        "outline": [
            {"title": "第一章：不期而遇", "description": "男女主角初次相遇"},
            {"title": "第二章：渐生情愫", "description": "相处中暗生情愫"},
            {"title": "第三章：误会重重", "description": "产生误会，关系紧张"},
            {"title": "第四章：真相大白", "description": "误会解除，感情升温"},
            {"title": "第五章：外界压力", "description": "面对现实考验"},
            {"title": "第六章：坚守爱情", "description": "克服困难，坚定选择"},
            {"title": "终章：幸福结局", "description": "修成正果，白头偕老"}
        ],
        "world_building": {
            "时代背景": "现代都市",
            "社会环境": "快节奏生活，职场竞争",
            "主题基调": "浪漫、温馨、治愈"
        },
        "writing_style": "细腻的情感描写，对话生动自然，氛围营造温馨"
    },
    {
        "name": "悬疑推理",
        "description": "侦探推理小说模板，层层推进",
        "category": "novel",
        "icon": "🔍",
        "outline": [
            {"title": "第一章：案件发生", "description": "离奇案件出现"},
            {"title": "第二章：展开调查", "description": "搜集线索，走访调查"},
            {"title": "第三章：疑点重重", "description": "发现更多疑点"},
            {"title": "第四章：抽丝剥茧", "description": "分析推理，接近真相"},
            {"title": "第五章：危机四伏", "description": "陷入危险，真相浮现"},
            {"title": "第六章：真相大白", "description": "揭露凶手，解开谜团"}
        ],
        "world_building": {
            "侦探设定": "聪明敏锐，观察力强",
            "案件类型": "密室杀人、连环命案、失踪案件",
            "氛围营造": "紧张、悬疑、反转"
        },
        "writing_style": "逻辑严密，伏笔巧妙，节奏紧凑，反转出人意料"
    },
    {
        "name": "科幻冒险",
        "description": "未来世界科幻探险模板",
        "category": "novel",
        "icon": "🚀",
        "outline": [
            {"title": "第一章：新世界", "description": "未来世界背景介绍"},
            {"title": "第二章：特殊使命", "description": "接受重要任务"},
            {"title": "第三章：星际航行", "description": "踏上未知旅程"},
            {"title": "第四章：异星奇遇", "description": "遭遇外星文明"},
            {"title": "第五章：危机降临", "description": "面对宇宙灾难"},
            {"title": "第六章：拯救行动", "description": "力挽狂澜"},
            {"title": "终章：新的篇章", "description": "开启新时代"}
        ],
        "world_building": {
            "科技水平": "星际航行、人工智能、基因改造",
            "社会形态": "星际联邦、企业帝国",
            "主题探讨": "科技与人性、文明冲突"
        },
        "writing_style": "想象力丰富，科技感强，探索人性深度"
    },
    {
        "name": "博客文章",
        "description": "技术博客写作模板",
        "category": "blog",
        "icon": "📝",
        "outline": [
            {"title": "引言", "description": "问题背景介绍"},
            {"title": "核心概念", "description": "关键知识点讲解"},
            {"title": "实践步骤", "description": "具体操作流程"},
            {"title": "代码示例", "description": "关键代码展示"},
            {"title": "总结", "description": "要点回顾和延伸"}
        ],
        "writing_style": "条理清晰，深入浅出，实用性强"
    },
    {
        "name": "产品文档",
        "description": "产品需求文档(PRD)模板",
        "category": "work",
        "icon": "📋",
        "outline": [
            {"title": "背景与目标", "description": "项目背景和目标说明"},
            {"title": "需求描述", "description": "功能需求详述"},
            {"title": "用户故事", "description": "使用场景和用户流程"},
            {"title": "功能规格", "description": "具体功能点说明"},
            {"title": "验收标准", "description": "完成标准和测试要求"},
            {"title": "时间规划", "description": "开发计划和里程碑"}
        ],
        "writing_style": "逻辑严谨，表述准确，便于执行"
    }
]

@router.get("/", response_model=List[TemplateResponse])
def list_templates(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取模板列表"""
    # 初始化预置模板（如果没有）
    init_default_templates(db, current_user["id"])
    
    query = db.query(Template).filter(
        or_(
            Template.is_system == True,
            Template.created_by == current_user["id"]
        )
    )
    
    if category:
        query = query.filter(Template.category == category)
    
    templates = query.order_by(Template.is_system.desc(), Template.created_at.desc()).all()
    return templates

@router.post("/", response_model=TemplateResponse)
def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建自定义模板"""
    db_template = Template(
        **template.model_dump(),
        created_by=current_user["id"],
        is_system=False
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@router.post("/{template_id}/apply")
def apply_template(
    template_id: int,
    project_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """应用模板创建项目"""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 创建项目
    project = Project(
        title=project_name or f"{template.name}项目",
        description=template.description,
        owner_id=current_user["id"]
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # 创建 项目设定
    memory = AIMemory(
        project_id=project.id,
        outline=template.outline or [],
        storyline=template.storyline,
        characters=template.characters or [],
        world_building=template.world_building or {},
        writing_style=template.writing_style
    )
    db.add(memory)
    
    # 根据大纲创建文档
    if template.outline:
        for i, item in enumerate(template.outline):
            doc = Document(
                title=item.get("title", f"章节{i+1}"),
                content=[{
                    "id": f"block-{i}-1",
                    "type": "paragraph",
                    "content": item.get("description", ""),
                    "props": {}
                }],
                project_id=project.id,
                order_index=i
            )
            db.add(doc)
    
    db.commit()
    
    return {
        "message": "模板应用成功",
        "project_id": project.id
    }


@router.post("/{template_id}/apply-to-project")
def apply_template_to_project(
    template_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """将模板应用到现有项目（覆盖当前项目的大纲、项目设定与文档）"""
    check_project_owner(db, project_id, current_user["id"])
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 更新或创建 项目设定
    memory = db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
    if not memory:
        memory = AIMemory(
            project_id=project_id,
            outline=template.outline or [],
            storyline=template.storyline,
            characters=template.characters or [],
            world_building=template.world_building or {},
            writing_style=template.writing_style,
        )
        db.add(memory)
    else:
        memory.outline = template.outline or []
        memory.storyline = template.storyline
        memory.characters = template.characters or []
        memory.world_building = template.world_building or {}
        memory.writing_style = template.writing_style

    # 删除现有文档
    db.query(Document).filter(Document.project_id == project_id).delete()

    # 按模板大纲创建新文档
    if template.outline:
        for i, item in enumerate(template.outline):
            doc = Document(
                title=item.get("title", f"章节{i+1}"),
                content=[{
                    "id": f"block-{i}-1",
                    "type": "paragraph",
                    "content": item.get("description", ""),
                    "props": {}
                }],
                project_id=project_id,
                order_index=i,
            )
            db.add(doc)

    db.commit()
    return {"message": "模板已应用到当前项目", "project_id": project_id}


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除自定义模板"""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.created_by == current_user["id"],
        Template.is_system == False
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or cannot delete system template")
    
    db.delete(template)
    db.commit()
    return {"message": "Template deleted"}

def init_default_templates(db: Session, user_id: int):
    """初始化预置模板"""
    existing = db.query(Template).filter(Template.is_system == True).count()
    if existing > 0:
        return
    
    for template_data in DEFAULT_TEMPLATES:
        template = Template(
            **template_data,
            created_by=user_id,
            is_system=True
        )
        db.add(template)
    
    db.commit()

# 需要在 models.py 中添加 Template 模型
# 需要在 schemas.py 中添加 TemplateCreate, TemplateResponse
