import pytest
from datetime import datetime, timedelta


class TestRootEndpoints:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestSubscriptionAPI:
    def test_create_subscription(self, client, sample_subscription_data):
        response = client.post("/api/subscriptions/", json=sample_subscription_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["user_id"] == sample_subscription_data["user_id"]
        assert data["service_name"] == sample_subscription_data["service_name"]

    def test_get_subscription(self, client, sample_subscription):
        response = client.get(f"/api/subscriptions/{sample_subscription.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_subscription.id
        assert data["service_name"] == "Netflix"

    def test_get_subscription_not_found(self, client):
        response = client.get("/api/subscriptions/9999")
        assert response.status_code == 404

    def test_list_subscriptions(self, client, sample_subscription):
        response = client.get("/api/subscriptions/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_subscriptions_by_user(self, client, sample_subscription):
        response = client.get("/api/subscriptions/?user_id=user_123")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(s["user_id"] == "user_123" for s in data)

    def test_update_subscription(self, client, sample_subscription):
        update_data = {
            "service_name": "Netflix Premium",
            "price": 39.99
        }
        
        response = client.put(
            f"/api/subscriptions/{sample_subscription.id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "Netflix Premium"
        assert data["price"] == 39.99

    def test_update_subscription_not_found(self, client):
        response = client.put("/api/subscriptions/9999", json={"price": 99.99})
        assert response.status_code == 404

    def test_delete_subscription(self, client, sample_subscription):
        response = client.delete(f"/api/subscriptions/{sample_subscription.id}")
        
        assert response.status_code == 204
        
        get_response = client.get(f"/api/subscriptions/{sample_subscription.id}")
        assert get_response.status_code == 404

    def test_delete_subscription_not_found(self, client):
        response = client.delete("/api/subscriptions/9999")
        assert response.status_code == 404

    def test_renew_subscription(self, client, sample_subscription):
        response = client.post(f"/api/subscriptions/{sample_subscription.id}/renew")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_subscription.id

    def test_renew_subscription_not_found(self, client):
        response = client.post("/api/subscriptions/9999/renew")
        assert response.status_code == 404


class TestUpcomingRenewalsAPI:
    def test_get_upcoming_renewals(self, client, test_db):
        now = datetime.utcnow()
        future_10_days = now + timedelta(days=10)
        
        subscription_data = {
            "user_id": "user_123",
            "service_name": "Netflix",
            "price": 29.99,
            "currency": "CNY",
            "cycle": "monthly",
            "start_date": now.isoformat(),
            "next_renewal_date": future_10_days.isoformat(),
            "is_active": 1,
            "auto_renew": 1,
            "reminder_days_before": 7
        }
        
        client.post("/api/subscriptions/", json=subscription_data)
        
        response = client.get("/api/subscriptions/upcoming/renewals?days_ahead=30")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        if data:
            first = data[0]
            assert "subscription" in first
            assert "days_until_renewal" in first
            assert "reminder_window_open" in first

    def test_get_upcoming_renewals_with_days_ahead(self, client, test_db):
        now = datetime.utcnow()
        future_50_days = now + timedelta(days=50)
        
        subscription_data = {
            "user_id": "user_123",
            "service_name": "Netflix",
            "price": 29.99,
            "currency": "CNY",
            "cycle": "monthly",
            "start_date": now.isoformat(),
            "next_renewal_date": future_50_days.isoformat(),
            "is_active": 1,
            "auto_renew": 1,
            "reminder_days_before": 7
        }
        
        client.post("/api/subscriptions/", json=subscription_data)
        
        response = client.get("/api/subscriptions/upcoming/renewals?days_ahead=30")
        data = response.json()
        
        assert len(data) == 0


class TestReminderAPI:
    def test_get_reminder(self, client, sample_subscription, test_db):
        import app.services as services
        from datetime import timedelta
        
        reminder = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=datetime.utcnow() + timedelta(days=5)
        )
        
        response = client.get(f"/api/reminders/{reminder.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == reminder.id
        assert data["status"] == "pending"

    def test_get_reminder_not_found(self, client):
        response = client.get("/api/reminders/9999")
        assert response.status_code == 404

    def test_get_reminders_by_subscription(self, client, sample_subscription, test_db):
        import app.services as services
        from datetime import timedelta
        
        services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=datetime.utcnow() + timedelta(days=7)
        )
        services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="second_reminder",
            scheduled_at=datetime.utcnow() + timedelta(days=3)
        )
        
        response = client.get(f"/api/reminders/subscription/{sample_subscription.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_reminders_by_subscription_not_found(self, client):
        response = client.get("/api/reminders/subscription/9999")
        assert response.status_code == 404

    def test_mark_reminder_as_sent(self, client, sample_subscription, test_db):
        import app.services as services
        from datetime import timedelta
        
        reminder = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=datetime.utcnow() + timedelta(days=5)
        )
        
        response = client.post(f"/api/reminders/{reminder.id}/send")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert data["sent_at"] is not None

    def test_mark_reminder_as_sent_not_found(self, client):
        response = client.post("/api/reminders/9999/send")
        assert response.status_code == 404

    def test_mark_reminder_as_failed(self, client, sample_subscription, test_db):
        import app.services as services
        from datetime import timedelta
        
        reminder = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=datetime.utcnow() + timedelta(days=5)
        )
        
        response = client.post(
            f"/api/reminders/{reminder.id}/fail",
            params={"error_message": "Email service unavailable"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Email service unavailable"

    def test_mark_reminder_as_failed_not_found(self, client):
        response = client.post("/api/reminders/9999/fail")
        assert response.status_code == 404

    def test_cancel_reminder(self, client, sample_subscription, test_db):
        import app.services as services
        from datetime import timedelta
        
        reminder = services.create_reminder(
            test_db,
            subscription_id=sample_subscription.id,
            reminder_type="first_reminder",
            scheduled_at=datetime.utcnow() + timedelta(days=5)
        )
        
        response = client.post(f"/api/reminders/{reminder.id}/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_reminder_not_found(self, client):
        response = client.post("/api/reminders/9999/cancel")
        assert response.status_code == 404
