from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ReminderStatus
from app.schemas import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    UpcomingRenewalResponse,
    SubscriptionWithReminders
)
import app.services as services

router = APIRouter()


@router.post("/", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db)
):
    return services.create_subscription(db, subscription)


@router.get("/{subscription_id}", response_model=SubscriptionWithReminders)
def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    db_subscription = services.get_subscription(db, subscription_id)
    if db_subscription is None:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return db_subscription


@router.get("/", response_model=List[SubscriptionResponse])
def list_subscriptions(
    user_id: Optional[str] = Query(None, description="用户ID，可选"),
    db: Session = Depends(get_db)
):
    if user_id:
        return services.get_subscriptions_by_user(db, user_id)
    return db.query(services.Subscription).all()


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: int,
    subscription_update: SubscriptionUpdate,
    db: Session = Depends(get_db)
):
    db_subscription = services.update_subscription(db, subscription_id, subscription_update)
    if db_subscription is None:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return db_subscription


@router.delete("/{subscription_id}", status_code=204)
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    success = services.delete_subscription(db, subscription_id)
    if not success:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return None


@router.post("/{subscription_id}/renew", response_model=SubscriptionResponse)
def renew_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    db_subscription = services.renew_subscription(db, subscription_id)
    if db_subscription is None:
        raise HTTPException(status_code=404, detail="订阅不存在或已失效")
    return db_subscription


@router.get("/upcoming/renewals", response_model=List[UpcomingRenewalResponse])
def get_upcoming_renewals(
    days_ahead: int = Query(30, ge=1, le=365, description="查询未来多少天内的续费"),
    current_date: Optional[datetime] = Query(None, description="指定当前日期，可选"),
    db: Session = Depends(get_db)
):
    if current_date is None:
        current_date = datetime.utcnow()
    
    upcoming = services.get_upcoming_renewals(db, days_ahead, current_date)
    
    result = []
    for subscription, days_until, window_open in upcoming:
        latest_reminder = services.get_latest_reminder_for_subscription(db, subscription.id)
        reminder_status = latest_reminder.status if latest_reminder else None
        
        result.append(UpcomingRenewalResponse(
            subscription=subscription,
            days_until_renewal=days_until,
            reminder_window_open=window_open,
            reminder_status=reminder_status
        ))
    
    return result
