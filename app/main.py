from fastapi import FastAPI
from app.database import engine, Base
from app.routers import subscriptions, reminders

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="订阅续费提醒 API",
    description="管理订阅周期、计算提醒窗口、查询即将续费的 API",
    version="1.0.0"
)

app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(reminders.router, prefix="/api/reminders", tags=["reminders"])


@app.get("/")
def read_root():
    return {"message": "订阅续费提醒 API 服务运行中", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
