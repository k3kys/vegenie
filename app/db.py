from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base # [수정] 최신 버전에 맞춰 import 방식 조정
from .settings import settings

# [수정] SQLite일 때만 check_same_thread 옵션 적용
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()