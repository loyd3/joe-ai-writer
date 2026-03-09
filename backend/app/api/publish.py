from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.api.auth import get_current_user
from app.services.wechat_publisher import WechatPublisher, WechatPublisherMock
from app.models.models import Document, Project
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/publish", tags=["publish"])


class WechatPublishRequest(BaseModel):
    """公众号发布请求"""
    document_id: int = Field(..., description="文档ID")
    title: Optional[str] = Field(default=None, description="文章标题（默认使用文档标题）")
    author: Optional[str] = Field(default=None, description="作者")
    digest: Optional[str] = Field(default=None, description="文章摘要")
    content_source_url: Optional[str] = Field(default=None, description="原文链接")
    thumb_media_id: Optional[str] = Field(default=None, description="封面图片素材ID")
    need_open_comment: bool = Field(default=True, description="是否开启评论")
    only_fans_can_comment: bool = Field(default=False, description="是否仅粉丝可评论")
    publish_now: bool = Field(default=False, description="是否立即发布（否则只保存为草稿）")
    mock_mode: bool = Field(default=False, description="模拟模式（用于测试，不实际发布）")


class WechatConfig(BaseModel):
    """公众号配置"""
    app_id: str = Field(..., description="公众号AppID")
    app_secret: str = Field(..., description="公众号AppSecret")


@router.post("/wechat/draft")
async def create_wechat_draft(
    request: WechatPublishRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    创建微信公众号图文草稿
    """
    # 获取文档
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 检查权限
    project = db.query(Project).filter(
        Project.id == document.project_id,
        Project.owner_id == current_user["id"]
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="无权访问该文档")
    
    # 获取文档内容
    content_blocks = document.content or []
    content_text = "\n\n".join([block.get("content", "") for block in content_blocks if block.get("content")])
    
    # 构建HTML内容
    html_content = _build_html_content(content_blocks)
    
    # 使用模拟模式或真实发布
    if request.mock_mode:
        publisher = WechatPublisherMock()
    else:
        # 从环境变量或数据库获取配置
        import os
        app_id = os.getenv("WECHAT_APP_ID", "")
        app_secret = os.getenv("WECHAT_APP_SECRET", "")
        
        if not app_id or not app_secret:
            raise HTTPException(status_code=400, detail="未配置公众号APP_ID和APP_SECRET")
        
        publisher = WechatPublisher(app_id, app_secret)
    
    try:
        result = publisher.draft_article(
            title=request.title or document.title,
            content=html_content,
            author=request.author,
            digest=request.digest,
            content_source_url=request.content_source_url,
            thumb_media_id=request.thumb_media_id,
            need_open_comment=request.need_open_comment,
            only_fans_can_comment=request.only_fans_can_comment
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "创建草稿失败"))
        
        # 如果要求立即发布
        if request.publish_now and not request.mock_mode:
            publish_result = publisher.submit_for_publish(result["media_id"])
            result["publish"] = publish_result
        
        return {
            "success": True,
            "draft": result,
            "document_title": document.title,
            "mode": "mock" if request.mock_mode else "real"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


@router.post("/wechat/publish/{media_id}")
async def publish_wechat_article(
    media_id: str,
    mock_mode: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    将草稿发布到公众号
    """
    if mock_mode:
        publisher = WechatPublisherMock()
    else:
        import os
        app_id = os.getenv("WECHAT_APP_ID", "")
        app_secret = os.getenv("WECHAT_APP_SECRET", "")
        
        if not app_id or not app_secret:
            raise HTTPException(status_code=400, detail="未配置公众号APP_ID和APP_SECRET")
        
        publisher = WechatPublisher(app_id, app_secret)
    
    try:
        result = publisher.submit_for_publish(media_id)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "发布失败"))
        
        return {
            "success": True,
            "publish_result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


@router.get("/wechat/status/{publish_id}")
async def get_publish_status(
    publish_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    查询发布状态
    """
    import os
    app_id = os.getenv("WECHAT_APP_ID", "")
    app_secret = os.getenv("WECHAT_APP_SECRET", "")
    
    if not app_id or not app_secret:
        raise HTTPException(status_code=400, detail="未配置公众号APP_ID和APP_SECRET")
    
    publisher = WechatPublisher(app_id, app_secret)
    
    try:
        result = publisher.get_publish_status(publish_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/wechat/materials")
async def get_material_list(
    type: str = "news",
    offset: int = 0,
    count: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取公众号素材列表
    """
    import os
    app_id = os.getenv("WECHAT_APP_ID", "")
    app_secret = os.getenv("WECHAT_APP_SECRET", "")
    
    if not app_id or not app_secret:
        raise HTTPException(status_code=400, detail="未配置公众号APP_ID和APP_SECRET")
    
    publisher = WechatPublisher(app_id, app_secret)
    
    try:
        result = publisher.get_material_list(type, offset, count)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取素材失败: {str(e)}")


def _build_html_content(blocks: list) -> str:
    """将文档块转换为微信公众号HTML格式"""
    html_parts = []
    
    for block in blocks:
        block_type = block.get("type", "paragraph")
        content = block.get("content", "")
        
        if not content:
            continue
        
        if block_type == "heading":
            # 根据标题级别选择标签
            level = block.get("props", {}).get("level", 2)
            if level == 1:
                html_parts.append(f"<h1>{content}</h1>")
            elif level == 2:
                html_parts.append(f"<h2>{content}</h2>")
            else:
                html_parts.append(f"<h3>{content}</h3>")
        
        elif block_type == "list":
            items = content.split('\n')
            list_items = ''.join([f"<li>{item.strip()}</li>" for item in items if item.strip()])
            html_parts.append(f"<ul>{list_items}</ul>")
        
        elif block_type == "quote":
            html_parts.append(f"<blockquote>{content}</blockquote>")
        
        else:  # paragraph and others
            # 处理换行
            paragraphs = content.split('\n')
            for para in paragraphs:
                if para.strip():
                    html_parts.append(f"<p>{para.strip()}</p>")
    
    return '\n'.join(html_parts)
