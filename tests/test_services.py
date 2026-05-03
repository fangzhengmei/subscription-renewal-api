import pytest
from datetime import datetime, timedelta
from app.models import SubscriptionCycle, ReminderStatus
from app.schemas import SubscriptionCreate, SubscriptionUpdate
import app.services as services


class TestCalculateNextRenewalDate:
    def test_daily_cycle(self):
        current = datetime(2024, 1, 15, 10, 0, 0)
        result = services.calculate_next_renewal_date(current, SubscriptionCycle.DAILY)
        assert result == datetime(2024, 1, 16, 10, 0, 0)

    def test_weekly_cycle(self):
        current = datetime(2024, 1, 15, 10, 0, 0)
        result = services.calculate_next_renewal_date(current, SubscriptionCycle.WEEKLY)
        assert result == datetime(2024, 1, 22, 10, 0, 0)

    def test_monthly_cycle_normal(self):
        current = datetime(2024, 1, 15, 10, 0, 0)
        result = services.calculate_next_renewal_date(current, SubscriptionCycle.MONTHLY)
        assert result == datetime(2024, 2, 15, 10, 0, 0)

    def test_monthly_cycle_december(self):
        current = datetime(2024, 12, 15, 10, 0, 0)
        result = services.calculate_next_renewal_date(current, SubscriptionCycle.MONTHLY)
        assert result == datetime(2025, 1, 15, 10, 0, 0)

    def test_monthly_cycle_end_of_month(self):
        current = datetime(2024, 1, 31, 10, 0, 0)
        result = services.calculate_next_renewal_date(current, SubscriptionCycle.MONTHLY)
        assert result == datetime(2024, 2, 29, 10, 0, 0)

    def test_yearly_cycle_normal(self):
        current = datetime(2024, 1, 15, 10, 0, 0)
        result = services.calculate_next_renewal_date(current, SubscriptionCycle.YEARLY)
        assert result == datetime(2025, 1, 15, 10, 0, 0)

    def test_yearly_cycle_leap_year(self):
        current = datetime(2024, 2, 29, 10, 0, 0)
        result = services.calculate_next_renewal_date(current, SubscriptionCycle.YEARLY)
        assert result == datetime(2025, 2, 28, 10, 0, 0)


class TestReminderWindow:
    def test_is_reminder_window_open_within_window(self):
        next_renewal = datetime(2024, 1, 20, 10, 0, 0)
        reminder_days = 7
        current = datetime(2024, 1, 15, 10, 0, 0)
        
        result = services.is_reminder_window_open(next_renewal, reminder_days, current)
        assert result is True

    def test_is_reminder_window_open_before_window(self):
        next_renewal = datetime(2024, 1, 20, 10, 0, 0)
        reminder_days = 7
        current = datetime(2024, 1, 10, 10, 0, 0)
        
        result = services.is_reminder_window_open(next_renewal, reminder_days, current)
        assert result is False

    def test_is_reminder_window_open_after_renewal(self):
        next_renewal = datetime(2024, 1, 20, 10, 0, 0)
        reminder_days = 7
        current = datetime(2024, 1, 21, 10, 0, 0)
        
        result = services.is_reminder_window_open(next_renewal, reminder_days, current)
        assert result is False

    def test_get_days_until_renewal_future(self):
        next_renewal = datetime(2024, 1, 20, 10, 0, 0)
        current = datetime(2024, 1, 15, 10, 0, 0)
        
        result = services.get_days_until_renewal(next_renewal, current)
        assert result == 5

    def test_get_days_until_renewal_past(self):
        next_renewal = datetime(2024, 1, 10, 10, 0, 0)
        current = datetime(2024, 1, 15, 10, 0, 0)
        
        result = services.get_days_until_renewal(next_renewal, current)
        assert result == 0


class TestSubscriptionCRUD:
    def test_create_subscription(self, test_db):
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
        
        result = services.create_subscription(test_db, subscription)
        
        assert result.id is not None
        assert result.user_id == "user_123"
        assert result.service_name == "Netflix"

    def test_get_subscription(self, test_db, sample_subscription):
        result = services.get_subscription(test_db, sample_subscription.id)
        
        assert result is not None
        assert result.id == sample_subscription.id
        assert result.service_name == "Netflix"

    def test_get_subscription_not_found(self, test_db):
        result = services.get_subscription(test_db, 9999)
        assert result is None

    def test_get_subscriptions_by_user(self, test_db):
        now = datetime.utcnow()
        
        sub1 = SubscriptionCreate(
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
        sub2 = SubscriptionCreate(
            user_id="user_123",
            service_name="Spotify",
            price=15.00,
            currency="CNY",
            cycle=SubscriptionCycle.MONTHLY,
            start_date=now,
            next_renewal_date=now + timedelta(days=15),
            is_active=1,
            auto_renew=1,
            reminder_days_before=7
        )
        
        services.create_subscription(test_db, sub1)
        services.create_subscription(test_db, sub2)
        
        result = services.get_subscriptions_by_user(test_db, "user_123")
        
        assert len(result) == 2
        assert {s.service_name for s in result} == {"Netflix", "Spotify"}

    def test_update_subscription(self, test_db, sample_subscription):
        update_data = SubscriptionUpdate(
            service_name="Netflix Premium",
            price=39.99
        )
        
        result = services.update_subscription(test_db, sample_subscription.id, update_data)
        
        assert result is not None
        assert result.service_name == "Netflix Premium"
        assert result.price == 39.99

    def test_delete_subscription(self, test_db, sample_subscription):
        result = services.delete_subscription(test_db, sample_subscription.id)
        assert result is True
        
        deleted = services.get_subscription(test_db, sample_subscription.id)
        assert deleted is None

    def test_delete_subscription_not_found(self, test_db):
        result = services.delete_subscription(test_db, 9999)
        assert result is False


class TestRenewSubscription:
    def test_renew_subscription(self, test_db):
        now = datetime(2024, 1, 15, 10, 0, 0)
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
        
        created = services.create_subscription(test_db, subscription)
        original_next = created.next_renewal_date
        
        result = services.renew_subscription(test_db, created.id)
        
        assert result is not None
        assert result.next_renewal_date > original_next

    def test_renew_inactive_subscription(self, test_db):
        now = datetime.utcnow()
        subscription = SubscriptionCreate(
            user_id="user_123",
            service_name="Netflix",
            price=29.99,
            currency="CNY",
            cycle=SubscriptionCycle.MONTHLY,
            start_date=now,
            next_renewal_date=now + timedelta(days=30),
            is_active=0,
            auto_renew=1,
            reminder_days_before=7
        )
        
        created = services.create_subscription(test_db, subscription)
        result = services.renew_subscription(test_db, created.id)
        
        assert result is None


class TestUpcomingRenewals:
    def test_get_upcoming_renewals(self, test_db):
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
        
        services.create_subscription(test_db, sub1)
        services.create_subscription(test_db, sub2)
        
        result = services.get_upcoming_renewals(test_db, days_ahead=30, current_date=now)
        
        assert len(result) == 1
        assert result[0][0].service_name == "Netflix"

    def test_get_upcoming_renewals_sorted(self, test_db):
        now = datetime(2024, 1, 15, 10, 0, 0)
        
        sub1 = SubscriptionCreate(
            user_id="user_123",
            service_name="Netflix",
            price=29.99,
            currency="CNY",
            cycle=SubscriptionCycle.MONTHLY,
            start_date=now,
            next_renewal_date=now + timedelta(days=20),
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
            next_renewal_date=now + timedelta(days=10),
            is_active=1,
            auto_renew=1,
            reminder_days_before=7
        )
        
        services.create_subscription(test_db, sub1)
        services.create_subscription(test_db, sub2)
        
        result = services.get_upcoming_renewals(test_db, days_ahead=30, current_date=now)
        
        assert len(result) == 2
        assert result[0][0].service_name == "Spotify"
        assert result[1][0].service_name == "Netflix"


class TestReminderServices:
    def test_create_reminder(self, test_db, sample_subscription):
        scheduled_at = datetime.utcnow() + timedelta(days=5)
        
        reminder = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=scheduled_at
        )
        
        assert reminder.id is not None
        assert reminder.subscription_id == sample_subscription.id
        assert reminder.status == ReminderStatus.PENDING

    def test_get_reminder(self, test_db, sample_subscription):
        scheduled_at = datetime.utcnow() + timedelta(days=5)
        created = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=scheduled_at
        )
        
        result = services.get_reminder(test_db, created.id)
        
        assert result is not None
        assert result.id == created.id

    def test_get_reminders_by_subscription(self, test_db, sample_subscription):
        now = datetime.utcnow()
        
        services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=now + timedelta(days=7)
        )
        services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="second_reminder",
            scheduled_at=now + timedelta(days=3)
        )
        
        result = services.get_reminders_by_subscription(test_db, sample_subscription.id)
        
        assert len(result) == 2

    def test_update_reminder_status_sent(self, test_db, sample_subscription):
        scheduled_at = datetime.utcnow() + timedelta(days=5)
        reminder = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=scheduled_at
        )
        
        result = services.update_reminder_status(test_db, reminder.id, ReminderStatus.SENT)
        
        assert result is not None
        assert result.status == ReminderStatus.SENT
        assert result.sent_at is not None

    def test_update_reminder_status_failed(self, test_db, sample_subscription):
        scheduled_at = datetime.utcnow() + timedelta(days=5)
        reminder = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=scheduled_at
        )
        
        result = services.update_reminder_status(
            test_db,
            reminder.id,
            ReminderStatus.FAILED,
            error_message="Email service unavailable"
        )
        
        assert result is not None
        assert result.status == ReminderStatus.FAILED
        assert result.error_message == "Email service unavailable"

    def test_get_latest_reminder(self, test_db, sample_subscription):
        now = datetime.utcnow()
        
        services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=now + timedelta(days=7)
        )
        latest = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="second_reminder",
            scheduled_at=now + timedelta(days=3)
        )
        
        result = services.get_latest_reminder_for_subscription(test_db, sample_subscription.id)
        
        assert result is not None
        assert result.id == latest.id
