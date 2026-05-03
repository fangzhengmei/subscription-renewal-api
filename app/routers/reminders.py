from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ReminderStatus
from app.schemas import ReminderResponse
import app.services as services

router = APIRouter()


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(
    reminder_id: int,
    db: Session = Depends(get_db)
):
    db_reminder = services.get_reminder(db, reminder_id)
    if db_reminder is None:
        raise HTTPException(status_code=404, detail="提醒记录不存在")
    return db_reminder


@router.get("/subscription/{subscription_id}", response_model=List[ReminderResponse])
def get_reminders_by_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    db_subscription = services.get_subscription(db, subscription_id)
    if db_subscription is None:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return services.get_reminders_by_subscription(db, subscription_id)


@router.post("/{reminder_id}/send", response_model=ReminderResponse)
def mark_reminder_as_sent(
    reminder_id: int,
    db: Session = Depends(get_db)
):
    db_reminder = services.update_reminder_status(db, reminder_id, ReminderStatus.SENT)
    if db_reminder is None:
        raise HTTPException(status_code=404, detail="提醒记录不存在")
    return db_reminder


@router.post("/{reminder_id}/fail", response_model=ReminderResponse)
def mark_reminder_as_failed(
    reminder_id: int,
    error_message: Optional[str] = None,
    db: Session = Depends(get_db)
):
    db_reminder = services.update_reminder_status(
        db, reminder_id, ReminderStatus.FAILED, error_message
    )
    if db_reminder is None:
        raise HTTPException(status_code=404, detail="提醒记录不存在")
    return db_reminder


@router.post("/{reminder_id}/cancel", response_model=ReminderResponse)
def cancel_reminder(
    reminder_id: int,
    db: Session = Depends(get_db)
):
    db_reminder = services.update_reminder_status(db, reminder_id, ReminderStatus.CANCELLED)
    if db_reminder is None:
        raise HTTPException(status_code=404, detail="提醒记录不存在")
    return db_reminder
