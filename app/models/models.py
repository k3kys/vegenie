from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint, Date, Text
from sqlalchemy.sql import func
import uuid
from app.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    phone = Column(String)
    store_name = Column(String)
    store_uuid = Column(String, unique=True, default=lambda: str(uuid.uuid4()))
    role = Column(String, default="OWNER")
    last_heartbeat = Column(DateTime, nullable=True)
    is_offline_notified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class SalesReport(Base):
    __tablename__ = "sales_reports"
    report_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_date = Column(Date)
    hall = Column(Integer, default=0)
    baemin = Column(Integer, default=0)
    coupang = Column(Integer, default=0)
    yogiyo = Column(Integer, default=0)
    total_sales = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint('user_id', 'report_date', name='_user_date_uc'),)


class SystemLog(Base):
    __tablename__ = "system_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    type = Column(String)  # LOGIN, ERROR, ZOMBIE_SMS 등
    level = Column(String)  # INFO, WARN, ERROR
    source = Column(String)  # SERVER, CLIENT
    message = Column(String)
    status = Column(String)  # SUCCESS, FAIL
    meta = Column(String, nullable=True)  # JSON String
    timestamp = Column(DateTime, server_default=func.now())


class ReportNotification(Base):
    __tablename__ = "report_notifications"
    notif_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_date = Column(Date)
    upload_status = Column(String, default="RECEIVED")
    primary_channel = Column(String, default="ALIMTALK")
    primary_status = Column(String, nullable=True)
    primary_body = Column(String, nullable=True)

    # [수정됨] 이 필드가 없어서 에러가 났습니다. 꼭 포함되어야 합니다!
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    __table_args__ = (UniqueConstraint('user_id', 'report_date', name='_user_date_notif_uc'),)


# [신규 추가] 버전 관리용 테이블
class Release(Base):
    __tablename__ = "releases"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, index=True)  # 예: "1.0.2"
    description = Column(Text, nullable=True)  # 업데이트 내역
    download_url = Column(String, nullable=False)  # 설치파일 경로
    is_mandatory = Column(Boolean, default=False)  # 강제 업데이트 여부
    created_at = Column(DateTime, server_default=func.now())