from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.api.auth import get_current_user
from app.models.models import Project, Document, AIInteraction

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def count_words_from_content(content: list) -> int:
    """从内容块列表中计算字数"""
    if not content:
        return 0
    return sum(len(block.get("content", "")) for block in content)


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取用户仪表盘统计数据（优化版，避免 N+1 查询）"""
    user_id = current_user["id"]
    
    # 基础统计 - 使用子查询一次获取
    total_projects = db.query(Project).filter(Project.owner_id == user_id).count()
    
    total_documents = db.query(Document).join(Project).filter(
        Project.owner_id == user_id
    ).count()
    
    # 优化：使用单个查询获取所有文档及其项目信息
    all_docs = db.query(Document).join(Project).filter(
        Project.owner_id == user_id
    ).options(joinedload(Document.project)).all()
    
    # 计算总字数
    total_words = sum(count_words_from_content(doc.content) for doc in all_docs)
    
    # AI 交互统计
    ai_interactions = db.query(AIInteraction).join(Document).join(Project).filter(
        Project.owner_id == user_id
    ).count()
    
    # 按类型统计 AI 使用
    ai_by_type = db.query(
        AIInteraction.interaction_type,
        func.count(AIInteraction.id)
    ).join(Document).join(Project).filter(
        Project.owner_id == user_id
    ).group_by(AIInteraction.interaction_type).all()
    
    ai_usage = {
        "polish": 0,
        "continue": 0,
        "brainstorm": 0,
        "chat": 0,
        "guide": 0,
        "revise": 0,
        "expand": 0,
        "summarize": 0,
        "total": ai_interactions
    }
    
    for interaction_type, count in ai_by_type:
        if interaction_type in ai_usage:
            ai_usage[interaction_type] = count
    
    # 优化：使用 joinedload 一次性获取最近项目和它们的文档
    recent_projects = db.query(Project).filter(
        Project.owner_id == user_id
    ).order_by(desc(Project.updated_at)).limit(5).options(
        joinedload(Project.documents)
    ).all()
    
    # 构建项目统计（无需额外查询）
    recent_projects_data = []
    for project in recent_projects:
        project_docs = project.documents or []
        doc_count = len(project_docs)
        word_count = sum(count_words_from_content(doc.content) for doc in project_docs)
        
        # 计算进度（假设目标为 10000 字）
        progress = min(int((word_count / 10000) * 100), 100)
        
        recent_projects_data.append({
            "id": project.id,
            "title": project.title,
            "documentCount": doc_count,
            "wordCount": word_count,
            "progress": progress,
            "updatedAt": project.updated_at.isoformat()
        })
    
    # 计算今日和本周字数（基于实际更新时间）
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    today_words = sum(
        count_words_from_content(doc.content) 
        for doc in all_docs 
        if doc.updated_at and doc.updated_at.date() == today
    )
    
    week_words = sum(
        count_words_from_content(doc.content) 
        for doc in all_docs 
        if doc.updated_at and doc.updated_at.date() >= week_ago
    )
    
    return {
        "stats": {
            "totalProjects": total_projects,
            "totalDocuments": total_documents,
            "totalWords": total_words,
            "totalAIInteractions": ai_interactions,
            "todayWords": today_words,
            "weekWords": week_words,
            "streakDays": 0
        },
        "aiUsage": ai_usage,
        "recentProjects": recent_projects_data
    }

@router.get("/writing-activity")
async def get_writing_activity(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取写作活动数据（用于图表）"""
    user_id = current_user["id"]
    
    # 获取日期范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 获取该时间段内的文档更新
    docs = db.query(Document, Project).join(Project).filter(
        Project.owner_id == user_id,
        Document.updated_at >= start_date
    ).all()
    
    # 按日期分组统计字数
    activity_by_date: Dict[str, int] = {}
    for doc, project in docs:
        date_key = doc.updated_at.strftime("%Y-%m-%d")
        word_count = sum(len(block.get("content", "")) for block in (doc.content or []))
        activity_by_date[date_key] = activity_by_date.get(date_key, 0) + word_count
    
    # 填充没有数据的日期
    result = []
    current = start_date
    while current <= end_date:
        date_key = current.strftime("%Y-%m-%d")
        result.append({
            "date": date_key,
            "words": activity_by_date.get(date_key, 0)
        })
        current += timedelta(days=1)
    
    return result
