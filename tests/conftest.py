import os
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import SubscriptionCycle, ReminderStatus
import app.services as services


@pytest.fixture(scope="function")
def test_db():
    settings = get_settings()
    engine = create_engine(
        settings.test_database_url,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_subscription_data():
    now = datetime.utcnow()
    return {
        "user_id": "user_123",
        "service_name": "Netflix",
        "price": 29.99,
        "currency": "CNY",
        "cycle": "monthly",
        "start_date": now.isoformat(),
        "next_renewal_date": (now + timedelta(days=10)).isoformat(),
        "is_active": 1,
        "auto_renew": 1,
        "reminder_days_before": 7
    }


@pytest.fixture
def sample_subscription(test_db):
    now = datetime.utcnow()
    from app.schemas import SubscriptionCreate
    
    subscription = SubscriptionCreate(
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
    return services.create_subscription(test_db, subscription)
