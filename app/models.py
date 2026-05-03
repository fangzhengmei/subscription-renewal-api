from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base


class SubscriptionCycle(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ReminderStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    service_name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="CNY")
    
    cycle = Column(SQLEnum(SubscriptionCycle), default=SubscriptionCycle.MONTHLY)
    
    start_date = Column(DateTime, nullable=False)
    next_renewal_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    
    is_active = Column(Integer, default=1)
    auto_renew = Column(Integer, default=1)
    
    reminder_days_before = Column(Integer, default=7)
    last_reminder_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reminders = relationship("Reminder", back_populates="subscription")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    
    reminder_type = Column(String, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    
    status = Column(SQLEnum(ReminderStatus), default=ReminderStatus.PENDING)
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscription = relationship("Subscription", back_populates="reminders")
