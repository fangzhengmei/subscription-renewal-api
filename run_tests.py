import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import SubscriptionCycle, ReminderStatus
from app.schemas import SubscriptionCreate, SubscriptionUpdate
import app.services as services


def get_test_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )


def test_calculate_next_renewal_date():
    print("Testing calculate_next_renewal_date...")
    
    current = datetime(2024, 1, 15, 10, 0, 0)
    
    result = services.calculate_next_renewal_date(current, SubscriptionCycle.DAILY)
    assert result == datetime(2024, 1, 16, 10, 0, 0), f"DAILY failed: {result}"
    
    result = services.calculate_next_renewal_date(current, SubscriptionCycle.WEEKLY)
    assert result == datetime(2024, 1, 22, 10, 0, 0), f"WEEKLY failed: {result}"
    
    result = services.calculate_next_renewal_date(current, SubscriptionCycle.MONTHLY)
    assert result == datetime(2024, 2, 15, 10, 0, 0), f"MONTHLY failed: {result}"
    
    result = services.calculate_next_renewal_date(current, SubscriptionCycle.YEARLY)
    assert result == datetime(2025, 1, 15, 10, 0, 0), f"YEARLY failed: {result}"
    
    print("  [OK] All cycle calculations passed")


def test_reminder_window():
    print("Testing reminder window...")
    
    next_renewal = datetime(2024, 1, 20, 10, 0, 0)
    reminder_days = 7
    
    current = datetime(2024, 1, 15, 10, 0, 0)
    result = services.is_reminder_window_open(next_renewal, reminder_days, current)
    assert result is True, f"Within window should be True, got {result}"
    
    current = datetime(2024, 1, 10, 10, 0, 0)
    result = services.is_reminder_window_open(next_renewal, reminder_days, current)
    assert result is False, f"Before window should be False, got {result}"
    
    current = datetime(2024, 1, 15, 10, 0, 0)
    days = services.get_days_until_renewal(next_renewal, current)
    assert days == 5, f"Days until should be 5, got {days}"
    
    print("  [OK] All reminder window tests passed")


def test_subscription_crud():
    print("Testing subscription CRUD...")
    
    engine = get_test_engine()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    try:
        now = datetime.utcnow()
        subscription = SubscriptionCreate(
            user_id="user_123",
            service_name="Netflix",
            price=29.99,
            currency="CNY",
            cycle=SubscriptionCycle.MONTHLY,
            start_date=now,
            next_renewal_date=now + timedelta(days=30),
            is_active=1,
            auto_renew=1,
            reminder_days_before=7
        )
        
        created = services.create_subscription(db, subscription)
        assert created.id is not None, "Create failed"
        assert created.service_name == "Netflix"
        print(f"  [OK] Created subscription: id={created.id}")
        
        found = services.get_subscription(db, created.id)
        assert found is not None, "Get failed"
        assert found.id == created.id
        print("  [OK] Got subscription")
        
        update_data = SubscriptionUpdate(
            service_name="Netflix Premium",
            price=39.99
        )
        updated = services.update_subscription(db, created.id, update_data)
        assert updated is not None, "Update failed"
        assert updated.service_name == "Netflix Premium"
        assert updated.price == 39.99
        print("  [OK] Updated subscription")
        
        subs = services.get_subscriptions_by_user(db, "user_123")
        assert len(subs) >= 1, "Get by user failed"
        print(f"  [OK] Got {len(subs)} subscriptions for user")
        
        success = services.delete_subscription(db, created.id)
        assert success is True, "Delete failed"
        print("  [OK] Deleted subscription")
        
    finally:
        db.close()
    
    print("  [OK] All CRUD tests passed")


def test_reminder_services():
    print("Testing reminder services...")
    
    engine = get_test_engine()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    try:
        now = datetime.utcnow()
        subscription = SubscriptionCreate(
            user_id="user_123",
            service_name="Netflix",
            price=29.99,
            currency="CNY",
            cycle=SubscriptionCycle.MONTHLY,
            start_date=now,
            next_renewal_date=now + timedelta(days=30),
            is_active=1,
            auto_renew=1,
            reminder_days_before=7
        )
        created_sub = services.create_subscription(db, subscription)
        
        scheduled_at = datetime.utcnow() + timedelta(days=5)
        reminder = services.create_reminder(
            db,
            subscription_id=created_sub.id,
            reminder_type="first_reminder",
            scheduled_at=scheduled_at
        )
        assert reminder.id is not None, "Create reminder failed"
        assert reminder.status == ReminderStatus.PENDING
        print(f"  [OK] Created reminder: id={reminder.id}")
        
        found = services.get_reminder(db, reminder.id)
        assert found is not None, "Get reminder failed"
        print("  [OK] Got reminder")
        
        sent = services.update_reminder_status(db, reminder.id, ReminderStatus.SENT)
        assert sent is not None, "Update status failed"
        assert sent.status == ReminderStatus.SENT
        assert sent.sent_at is not None
        print("  [OK] Marked reminder as sent")
        
        latest = services.get_latest_reminder_for_subscription(db, created_sub.id)
        assert latest is not None, "Get latest failed"
        print("  [OK] Got latest reminder")
        
    finally:
        db.close()
    
    print("  [OK] All reminder tests passed")


def test_upcoming_renewals():
    print("Testing upcoming renewals...")
    
    engine = get_test_engine()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    try:
        now = datetime(2024, 1, 15, 10, 0, 0)
        
        sub1 = SubscriptionCreate(
            user_id="user_123",
            service_name="Netflix",
            price=29.99,
            currency="CNY",
            cycle=SubscriptionCycle.MONTHLY,
            start_date=now,
            next_renewal_date=now + timedelta(days=10),
            is_active=1,
            auto_renew=1,
            reminder_days_before=7
        )
        sub2 = SubscriptionCreate(
            user_id="user_123",
            service_name="Spotify",
            price=15.00,
            currency="CNY",
            cycle=SubscriptionCycle.MONTHLY,
            start_date=now,
            next_renewal_date=now + timedelta(days=40),
            is_active=1,
            auto_renew=1,
            reminder_days_before=7
        )
        
        services.create_subscription(db, sub1)
        services.create_subscription(db, sub2)
        
        upcoming = services.get_upcoming_renewals(db, days_ahead=30, current_date=now)
        assert len(upcoming) == 1, f"Expected 1 upcoming, got {len(upcoming)}"
        assert upcoming[0][0].service_name == "Netflix"
        print(f"  [OK] Found {len(upcoming)} upcoming renewals within 30 days")
        
        upcoming = services.get_upcoming_renewals(db, days_ahead=50, current_date=now)
        assert len(upcoming) == 2, f"Expected 2 upcoming, got {len(upcoming)}"
        print(f"  [OK] Found {len(upcoming)} upcoming renewals within 50 days")
        
    finally:
        db.close()
    
    print("  [OK] All upcoming renewals tests passed")


if __name__ == "__main__":
    print("=" * 50)
    print("Running Subscription Renewal API Tests")
    print("=" * 50)
    print()
    
    try:
        test_calculate_next_renewal_date()
        print()
        test_reminder_window()
        print()
        test_subscription_crud()
        print()
        test_reminder_services()
        print()
        test_upcoming_renewals()
        
        print()
        print("=" * 50)
        print("[OK] All tests passed!")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
