import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from app.routers import system, auth, users, sales
from app.settings import settings
from app.services.monitoring import MonitoringService

# 스케줄러 설정
scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 스케줄러 시작
    scheduler.add_job(MonitoringService.check_zombies, 'interval', minutes=1, id='check_zombies')
    scheduler.add_job(MonitoringService.daily_reset, 'cron', hour=0, minute=5, id='daily_reset')
    scheduler.start()
    print("--- [System] Monitoring Scheduler Started ---")
    yield
    scheduler.shutdown()
    print("--- [System] Monitoring Scheduler Shutdown ---")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# [수정됨] system 라우터의 prefix를 '/api/v1'으로 변경 (기존 '/api/v1/system' 제거)
app.include_router(system.router, prefix=settings.API_V1_STR, tags=["System & Reports"])

# 나머지 라우터는 기존 유지
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(sales.router, prefix=f"{settings.API_V1_STR}/sales", tags=["sales"])

@app.get("/")
def root():
    return {"message": "Vegenie API Server is running"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)