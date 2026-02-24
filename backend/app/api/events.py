"""
事件设定 API - 管理故事中的关键事件
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Event
from app.schemas.schemas import EventCreate, EventUpdate, EventResponse

router = APIRouter(prefix="/api/projects/{project_id}/events", tags=["events"])

@router.get("", response_model=List[EventResponse])
def list_events(project_id: int, db: Session = Depends(get_db)):
    """获取项目下的所有事件"""
    events = db.query(Event).filter(
        Event.project_id == project_id
    ).order_by(Event.order_index, Event.created_at).all()
    return events

@router.post("", response_model=EventResponse)
def create_event(project_id: int, event: EventCreate, db: Session = Depends(get_db)):
    """创建新事件"""
    db_event = Event(**event.model_dump(), project_id=project_id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.get("/{event_id}", response_model=EventResponse)
def get_event(project_id: int, event_id: int, db: Session = Depends(get_db)):
    """获取事件详情"""
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.project_id == project_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    project_id: int, 
    event_id: int, 
    event_update: EventUpdate, 
    db: Session = Depends(get_db)
):
    """更新事件"""
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.project_id == project_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    for field, value in event_update.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    
    db.commit()
    db.refresh(event)
    return event

@router.delete("/{event_id}")
def delete_event(project_id: int, event_id: int, db: Session = Depends(get_db)):
    """删除事件"""
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.project_id == project_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}

@router.post("/{event_id}/reorder")
def reorder_event(
    project_id: int,
    event_id: int,
    new_index: int,
    db: Session = Depends(get_db)
):
    """重新排序事件"""
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.project_id == project_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.order_index = new_index
    db.commit()
    db.refresh(event)
    return event
