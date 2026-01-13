import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import Base, engine
from app.models.models import User, SalesReport

def init_db():
    print("Vegenie DB 초기화 중...")
    Base.metadata.create_all(bind=engine)
    print("테이블 생성 완료: users, sales_reports")

if __name__ == "__main__":
    init_db()
