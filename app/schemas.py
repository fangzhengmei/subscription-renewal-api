from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models import SubscriptionCycle, ReminderStatus


class SubscriptionBase(BaseModel):
    user_id: str
    service_name: str
    price: float
    currency: str = "CNY"
    cycle: SubscriptionCycle = SubscriptionCycle.MONTHLY
    start_date: datetime
    next_renewal_date: datetime
    end_date: Optional[datetime] = None
    is_active: int = 1
    auto_renew: int = 1
    reminder_days_before: int = 7


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    service_name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    cycle: Optional[SubscriptionCycle] = None
    next_renewal_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[int] = None
    auto_renew: Optional[int] = None
    reminder_days_before: Optional[int] = None
    last_reminder_sent_at: Optional[datetime] = None


class SubscriptionResponse(SubscriptionBase):
    id: int
    last_reminder_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReminderBase(BaseModel):
    subscription_id: int
    reminder_type: str
    scheduled_at: datetime


class ReminderResponse(BaseModel):
    id: int
    subscription_id: int
    reminder_type: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    status: ReminderStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpcomingRenewalResponse(BaseModel):
    subscription: SubscriptionResponse
    days_until_renewal: int
    reminder_window_open: bool
    reminder_status: Optional[ReminderStatus] = None


class SubscriptionWithReminders(SubscriptionResponse):
    reminders: List[ReminderResponse] = []

    class Config:
        from_attributes = True
