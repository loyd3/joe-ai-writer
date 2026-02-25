from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.api.auth import get_current_user
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
    },
    
    # ========== 新增小说模板 ==========
    {
        "name": "都市异能",
        "description": "现代都市背景下的超能力故事",
        "category": "novel",
        "icon": "⚡",
        "outline": [
            {"title": "第一章：平凡日常", "description": "主角的普通生活，暗藏不凡"},
            {"title": "第二章：觉醒时刻", "description": "意外觉醒超能力"},
            {"title": "第三章：能力探索", "description": "摸索能力边界，意外发现"},
            {"title": "第四章：暗流涌动", "description": "发现隐藏在都市中的异能世界"},
            {"title": "第五章：卷入风波", "description": "被迫站队，面临选择"},
            {"title": "第六章：实力成长", "description": "训练提升，结识伙伴"},
            {"title": "终章：守护之战", "description": "保卫所爱，确立地位"}
        ],
        "world_building": {
            "能力类型": "元素操控、精神异能、身体强化、特殊天赋",
            "组织势力": "异能管理局、地下组织、世家大族",
            "世界规则": "表面是现代都市，实则暗流涌动"
        },
        "writing_style": "代入感强，都市生活细节真实，能力设定新颖有趣"
    },
    {
        "name": "历史架空",
        "description": "穿越或虚构历史背景的故事",
        "category": "novel",
        "icon": "👑",
        "outline": [
            {"title": "第一章：初入异世", "description": "来到陌生时代，观察环境"},
            {"title": "第二章：立足之地", "description": "凭借知识或能力获得一席之地"},
            {"title": "第三章：崭露头角", "description": "展现才华，引起注意"},
            {"title": "第四章：权谋博弈", "description": "卷入朝堂或势力纷争"},
            {"title": "第五章：宏图大业", "description": "改革或争霸，施展抱负"},
            {"title": "第六章：治国安邦", "description": "推行新政，富国强民"},
            {"title": "终章：名垂青史", "description": "功成名就，开创盛世"}
        ],
        "world_building": {
            "时代背景": "可基于秦汉唐宋明等朝代架空",
            "核心要素": "朝堂权谋、军事战争、民生改革、科技发展",
            "主题": "家国情怀、个人抱负、历史变革"
        },
        "writing_style": "历史细节考究，权谋描写精彩，格局宏大"
    },
    {
        "name": "恐怖灵异",
        "description": "恐怖悬疑或灵异怪谈故事",
        "category": "novel",
        "icon": "👻",
        "outline": [
            {"title": "第一章：诡异开端", "description": "异常现象出现，悬念建立"},
            {"title": "第二章：恐怖升级", "description": "怪事频发，恐怖氛围加重"},
            {"title": "第三章：探寻真相", "description": "调查事件源头，发现线索"},
            {"title": "第四章：深入险境", "description": "直面恐怖源头，危险重重"},
            {"title": "第五章：真相揭露", "description": "揭开背后的秘密或诅咒"},
            {"title": "第六章：结局或余波", "description": "解决问题或留下悬念"}
        ],
        "world_building": {
            "恐怖元素": "鬼魂、诅咒、灵异事件、心理恐惧",
            "氛围营造": "阴暗、压抑、紧张、突如其来的惊吓",
            "核心": "未知带来的恐惧，人性的黑暗面"
        },
        "writing_style": "氛围营造出色，心理描写细腻，节奏张弛有度"
    },
    {
        "name": "游戏电竞",
        "description": "电子竞技或游戏世界故事",
        "category": "novel",
        "icon": "🎮",
        "outline": [
            {"title": "第一章：游戏人生", "description": "主角与游戏的渊源"},
            {"title": "第二章：崭露头角", "description": "展现实力，引起关注"},
            {"title": "第三章：组建战队", "description": "结识队友，组建团队"},
            {"title": "第四章：征战赛场", "description": "参加赛事，面对强敌"},
            {"title": "第五章：低谷挫折", "description": "遭遇失败，团队危机"},
            {"title": "第六章：重返巅峰", "description": "克服困难，夺得冠军"}
        ],
        "world_building": {
            "游戏类型": "MOBA、FPS、MMORPG、策略游戏",
            "电竞生态": "职业选手、俱乐部、赛事体系、直播行业",
            "主题": "青春、热血、梦想、团队精神"
        },
        "writing_style": "热血激情，游戏细节专业，团队情谊动人"
    },
    {
        "name": "穿越重生",
        "description": "穿越或重生回到过去，改变命运",
        "category": "novel",
        "icon": "🌀",
        "outline": [
            {"title": "第一章：意外穿越", "description": "主角穿越或重生，获得第二次机会"},
            {"title": "第二章：适应新身份", "description": "熟悉环境，制定计划"},
            {"title": "第三章：先知优势", "description": "利用前世记忆，抢占先机"},
            {"title": "第四章：改变命运", "description": "避开前世遗憾，挽救重要之人"},
            {"title": "第五章：蝴蝶效应", "description": "改变引发的连锁反应"},
            {"title": "第六章：新的人生", "description": "建立事业，收获幸福"}
        ],
        "world_building": {
            "穿越类型": "古代穿越、平行世界、游戏世界、重生回过去",
            "核心优势": "先知先觉、现代知识、特殊技能",
            "目标": "弥补遗憾、追求梦想、守护所爱"
        },
        "writing_style": "情感共鸣强，对比前世今生的反差"
    },
    
    # ========== 新增博客模板 ==========
    {
        "name": "产品评测",
        "description": "产品测评和体验分享模板",
        "category": "blog",
        "icon": "⭐",
        "outline": [
            {"title": "产品简介", "description": "产品基本信息和定位"},
            {"title": "开箱/初印象", "description": "外观设计和第一印象"},
            {"title": "核心功能", "description": "主要功能详细体验"},
            {"title": "使用场景", "description": "适合什么人群和场景"},
            {"title": "优缺点分析", "description": "客观评价优点和不足"},
            {"title": "竞品对比", "description": "与同类产品比较"},
            {"title": "购买建议", "description": "值不值得买，适合谁"}
        ],
        "writing_style": "客观公正，体验真实，数据支撑，图文并茂"
    },
    {
        "name": "游记攻略",
        "description": "旅行游记和攻略分享",
        "category": "blog",
        "icon": "✈️",
        "outline": [
            {"title": "目的地介绍", "description": "旅行地点概况和特色"},
            {"title": "行程规划", "description": "详细路线和时间安排"},
            {"title": "交通住宿", "description": "交通方式和住宿推荐"},
            {"title": "景点体验", "description": "各个景点的游玩体验"},
            {"title": "美食推荐", "description": "当地特色美食分享"},
            {"title": "实用贴士", "description": "省钱技巧、注意事项"},
            {"title": "总结感悟", "description": "旅行心得和建议"}
        ],
        "writing_style": "生动有趣，信息实用，图片丰富，情感真挚"
    },
    {
        "name": "读书笔记",
        "description": "书籍阅读心得和总结",
        "category": "blog",
        "icon": "📚",
        "outline": [
            {"title": "书籍信息", "description": "书名、作者、出版信息"},
            {"title": "内容概述", "description": "书籍主要内容和结构"},
            {"title": "核心观点", "description": "书中重要观点和理论"},
            {"title": "精彩片段", "description": "摘录和解读经典段落"},
            {"title": "个人感悟", "description": "阅读后的思考和启发"},
            {"title": "实践应用", "description": "如何将书中内容应用到生活"},
            {"title": "推荐理由", "description": "适合什么人阅读"}
        ],
        "writing_style": "思考深入，观点独特，引用恰当，联系实际"
    },
    
    # ========== 新增工作模板 ==========
    {
        "name": "项目复盘",
        "description": "项目结束后总结复盘",
        "category": "work",
        "icon": "📊",
        "outline": [
            {"title": "项目概述", "description": "项目背景、目标、团队成员"},
            {"title": "执行过程", "description": "关键时间节点和里程碑"},
            {"title": "成果展示", "description": "达成的目标和产出物"},
            {"title": "数据回顾", "description": "关键指标和数据分析"},
            {"title": "成功经验", "description": "做得好的地方和原因"},
            {"title": "问题反思", "description": "遇到的挑战和不足"},
            {"title": "改进建议", "description": "未来如何做得更好"}
        ],
        "writing_style": "客观真实，数据支撑，反思深刻，建议可行"
    },
    {
        "name": "会议纪要",
        "description": "会议记录和待办跟进",
        "category": "work",
        "icon": "📝",
        "outline": [
            {"title": "会议信息", "description": "时间、地点、参会人、主题"},
            {"title": "议题讨论", "description": "各议题讨论要点"},
            {"title": "决议结论", "description": "达成的共识和决定"},
            {"title": "待办事项", "description": "Action Items，责任人和Deadline"},
            {"title": "下次安排", "description": "下次会议时间和议题"}
        ],
        "writing_style": "简洁明了，重点突出，条理清晰，待办明确"
    },
    {
        "name": "周报月报",
        "description": "工作汇报总结模板",
        "category": "work",
        "icon": "📅",
        "outline": [
            {"title": "本周/月总结", "description": "主要工作内容和完成情况"},
            {"title": "关键成果", "description": "重要成果和数据亮点"},
            {"title": "进展更新", "description": "各项目进度状态"},
            {"title": "问题风险", "description": "遇到的困难和需要支持"},
            {"title": "下周/月计划", "description": "接下来的工作计划和目标"}
        ],
        "writing_style": "简洁高效，重点突出，数据量化，问题明确"
    },
    {
        "name": "商业计划书",
        "description": "创业项目BP模板",
        "category": "work",
        "icon": "💼",
        "outline": [
            {"title": "项目概述", "description": "一句话介绍项目，核心价值"},
            {"title": "市场痛点", "description": "解决的问题和市场机会"},
            {"title": "解决方案", "description": "产品/服务如何解决问题"},
            {"title": "市场规模", "description": "TAM/SAM/SOM市场分析"},
            {"title": "商业模式", "description": "盈利方式和收入来源"},
            {"title": "竞争分析", "description": "竞品对比和差异化优势"},
            {"title": "运营数据", "description": "关键指标和增长趋势"},
            {"title": "团队介绍", "description": "核心团队背景和能力"},
            {"title": "融资计划", "description": "融资需求和资金用途"}
        ],
        "writing_style": "逻辑清晰，数据支撑，亮点突出，可信度高"
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
    
    # 创建 AI 记忆
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

@router.post("/{template_id}/import")
def import_template_to_project(
    template_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """将模板导入到已有项目"""
    # 获取模板
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 获取项目并验证权限
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or no permission")
    
    # 获取或创建 AI 记忆
    memory = db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
    if not memory:
        memory = AIMemory(project_id=project_id)
        db.add(memory)
    
    # 更新 AI 记忆（合并模板内容）
    if template.outline:
        # 追加大纲到现有内容
        existing_outline = memory.outline or []
        new_outline = existing_outline + template.outline
        memory.outline = new_outline
    
    if template.storyline:
        memory.storyline = template.storyline
    
    if template.characters:
        existing_chars = memory.characters or []
        memory.characters = existing_chars + template.characters
    
    if template.world_building:
        existing_wb = memory.world_building or {}
        merged_wb = {**existing_wb, **template.world_building}
        memory.world_building = merged_wb
    
    if template.writing_style:
        memory.writing_style = template.writing_style
    
    # 根据大纲创建新文档
    if template.outline:
        # 获取当前项目的最大 order_index
        max_order = db.query(Document).filter(
            Document.project_id == project_id
        ).count()
        
        for i, item in enumerate(template.outline):
            doc = Document(
                title=item.get("title", f"章节{i+1}"),
                content=[{
                    "id": f"block-{max_order + i}-1",
                    "type": "paragraph",
                    "content": item.get("description", ""),
                    "props": {}
                }],
                project_id=project_id,
                order_index=max_order + i
            )
            db.add(doc)
    
    db.commit()
    
    return {
        "message": "模板导入成功",
        "project_id": project_id,
        "documents_added": len(template.outline) if template.outline else 0
    }


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
