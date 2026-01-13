# app/controllers/auth_controller.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import User
from app.schemas.user_schema import UserCreate, UserLogin
from app.core.security import get_password_hash, verify_password, create_access_token
from app.settings import settings
from datetime import timedelta
from datetime import datetime

class AuthController:
    @staticmethod
    def register_user(db: Session, user_in: UserCreate):
        # 1. Username 중복 체크
        existing_user = db.query(User).filter(User.username == user_in.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )

        # 2. 비밀번호 해싱 및 User 객체 생성
        # [cite_start]store_uuid는 Model의 default=uuid.uuid4()에 의해 자동 생성 (서버 권위) [cite: 19]
        db_user = User(
            username=user_in.username,
            password_hash=get_password_hash(user_in.password),
            phone=user_in.phone,
            store_name=user_in.store_name,
            role="OWNER"
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def login_user(db: Session, user_in: UserLogin):
        # 1. 유저 조회
        user = db.query(User).filter(User.username == user_in.username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        # 2. 비밀번호 검증
        if not verify_password(user_in.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        # 3. 토큰 발급
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id},  # user_id 포함
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    @staticmethod
    def process_heartbeat(db: Session, current_user: User):
        # 1. 마지막 수신 시간 갱신
        current_user.last_heartbeat = datetime.now()

        # 2. 좀비 상태였다면 해제 (재수신 시 is_offline_notified=False)
        if current_user.is_offline_notified:
            current_user.is_offline_notified = False

            # (선택) 복구 로그 남기기
            # MonitoringService.log_event(...)

        db.add(current_user)
        db.commit()
        db.refresh(current_user)

        return {
            "status": "alive",
            "last_heartbeat": str(current_user.last_heartbeat)
        }