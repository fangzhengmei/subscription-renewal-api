from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Subscription, Reminder, SubscriptionCycle, ReminderStatus
from app.schemas import SubscriptionCreate, SubscriptionUpdate


def calculate_next_renewal_date(
    current_date: datetime,
    cycle: SubscriptionCycle
) -> datetime:
    if cycle == SubscriptionCycle.DAILY:
        return current_date + timedelta(days=1)
    elif cycle == SubscriptionCycle.WEEKLY:
        return current_date + timedelta(weeks=1)
    elif cycle == SubscriptionCycle.MONTHLY:
        if current_date.month == 12:
            next_month = 1
            next_year = current_date.year + 1
        else:
            next_month = current_date.month + 1
            next_year = current_date.year
        
        try:
            return current_date.replace(year=next_year, month=next_month)
        except ValueError:
            if next_month == 2:
                if (next_year % 4 == 0 and next_year % 100 != 0) or (next_year % 400 == 0):
                    max_day = 29
                else:
                    max_day = 28
            else:
                max_day = 31 if next_month in [1, 3, 5, 7, 8, 10, 12] else 30
            return current_date.replace(year=next_year, month=next_month, day=max_day)
    elif cycle == SubscriptionCycle.YEARLY:
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            if current_date.month == 2 and current_date.day == 29:
                return current_date.replace(year=current_date.year + 1, day=28)
            raise
    return current_date


def is_reminder_window_open(
    next_renewal_date: datetime,
    reminder_days_before: int,
    current_date: Optional[datetime] = None
) -> bool:
    if current_date is None:
        current_date = datetime.utcnow()
    
    reminder_start_date = next_renewal_date - timedelta(days=reminder_days_before)
    return current_date >= reminder_start_date and current_date <= next_renewal_date


def get_days_until_renewal(
    next_renewal_date: datetime,
    current_date: Optional[datetime] = None
) -> int:
    if current_date is None:
        current_date = datetime.utcnow()
    
    delta = next_renewal_date - current_date
    return max(0, delta.days + (1 if delta.seconds > 0 else 0))


def create_subscription(db: Session, subscription: SubscriptionCreate) -> Subscription:
    db_subscription = Subscription(
        user_id=subscription.user_id,
        service_name=subscription.service_name,
        price=subscription.price,
        currency=subscription.currency,
        cycle=subscription.cycle,
        start_date=subscription.start_date,
        next_renewal_date=subscription.next_renewal_date,
        end_date=subscription.end_date,
        is_active=subscription.is_active,
        auto_renew=subscription.auto_renew,
        reminder_days_before=subscription.reminder_days_before,
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription


def get_subscription(db: Session, subscription_id: int) -> Optional[Subscription]:
    return db.query(Subscription).filter(Subscription.id == subscription_id).first()


def get_subscriptions_by_user(db: Session, user_id: str) -> List[Subscription]:
    return db.query(Subscription).filter(Subscription.user_id == user_id).all()


def update_subscription(
    db: Session,
    subscription_id: int,
    subscription_update: SubscriptionUpdate
) -> Optional[Subscription]:
    db_subscription = get_subscription(db, subscription_id)
    if db_subscription is None:
        return None
    
    update_data = subscription_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_subscription, key, value)
    
    db.commit()
    db.refresh(db_subscription)
    return db_subscription


def delete_subscription(db: Session, subscription_id: int) -> bool:
    db_subscription = get_subscription(db, subscription_id)
    if db_subscription is None:
        return False
    
    db.delete(db_subscription)
    db.commit()
    return True


def renew_subscription(db: Session, subscription_id: int) -> Optional[Subscription]:
    db_subscription = get_subscription(db, subscription_id)
    if db_subscription is None or not db_subscription.is_active:
        return None
    
    db_subscription.next_renewal_date = calculate_next_renewal_date(
        db_subscription.next_renewal_date,
        db_subscription.cycle
    )
    db.commit()
    db.refresh(db_subscription)
    return db_subscription


def get_upcoming_renewals(
    db: Session,
    days_ahead: int = 30,
    current_date: Optional[datetime] = None
) -> List[Tuple[Subscription, int, bool]]:
    if current_date is None:
        current_date = datetime.utcnow()
    
    end_date = current_date + timedelta(days=days_ahead)
    
    subscriptions = db.query(Subscription).filter(
        Subscription.is_active == 1,
        Subscription.next_renewal_date >= current_date,
        Subscription.next_renewal_date <= end_date
    ).all()
    
    result = []
    for sub in subscriptions:
        days_until = get_days_until_renewal(sub.next_renewal_date, current_date)
        window_open = is_reminder_window_open(
            sub.next_renewal_date,
            sub.reminder_days_before,
            current_date
        )
        result.append((sub, days_until, window_open))
    
    return sorted(result, key=lambda x: x[0].next_renewal_date)


def create_reminder(
    db: Session,
    subscription_id: int,
    reminder_type: str,
    scheduled_at: datetime
) -> Reminder:
    db_reminder = Reminder(
        subscription_id=subscription_id,
        reminder_type=reminder_type,
        scheduled_at=scheduled_at,
        status=ReminderStatus.PENDING,
    )
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder


def get_reminder(db: Session, reminder_id: int) -> Optional[Reminder]:
    return db.query(Reminder).filter(Reminder.id == reminder_id).first()


def get_reminders_by_subscription(
    db: Session,
    subscription_id: int
) -> List[Reminder]:
    return db.query(Reminder).filter(
        Reminder.subscription_id == subscription_id
    ).order_by(Reminder.created_at.desc()).all()


def update_reminder_status(
    db: Session,
    reminder_id: int,
    status: ReminderStatus,
    error_message: Optional[str] = None
) -> Optional[Reminder]:
    db_reminder = get_reminder(db, reminder_id)
    if db_reminder is None:
        return None
    
    db_reminder.status = status
    if status == ReminderStatus.SENT:
        db_reminder.sent_at = datetime.utcnow()
    if error_message:
        db_reminder.error_message = error_message
    
    db.commit()
    db.refresh(db_reminder)
    return db_reminder


def get_latest_reminder_for_subscription(
    db: Session,
    subscription_id: int
) -> Optional[Reminder]:
    return db.query(Reminder).filter(
        Reminder.subscription_id == subscription_id
    ).order_by(Reminder.created_at.desc()).first()
