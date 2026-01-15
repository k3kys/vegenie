import random
import string
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta, datetime

from app.models.models import User
from app.schemas.user_schema import UserCreate, UserLogin, FindIdRequest, ResetPasswordRequest
from app.core.security import get_password_hash, verify_password, create_access_token
from app.settings import settings
from app.services.notification import NotificationService


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
            data={"sub": user.username, "user_id": user.id},
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

        # 2. [로직 수정] 앱이 켜져서 신호를 보냈으므로 감시 상태를 True(정상/감시중)로 유지
        # 이렇게 해두어야 monitoring에서 '오늘 신호가 있었고 상태가 True인 매장'을 감시합니다.
        current_user.is_offline_notified = True

        db.add(current_user)
        db.commit()
        db.refresh(current_user)

        return {
            "status": "alive",
            "last_heartbeat": str(current_user.last_heartbeat)
        }

    # ------------------------------------------------------------------
    # [NEW] 아이디 찾기 (휴대폰 번호 기준)
    # ------------------------------------------------------------------
    @staticmethod
    def find_username(db: Session, user_in: FindIdRequest):
        user = db.query(User).filter(User.phone == user_in.phone).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 번호로 등록된 아이디가 없습니다."
            )

        # 보안을 위해 아이디의 일부를 마스킹 처리
        masked_username = user.username[:3] + "*" * (len(user.username) - 3)
        return {"username": masked_username}

    # ------------------------------------------------------------------
    # [NEW] 비밀번호 재설정 (임시 비밀번호 생성 및 SMS 발송)
    # ------------------------------------------------------------------
    @staticmethod
    def reset_password(db: Session, user_in: ResetPasswordRequest):
        user = db.query(User).filter(
            User.username == user_in.username,
            User.phone == user_in.phone
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="일치하는 사용자 정보가 없습니다."
            )

        # 1. 8자리 영문+숫자 혼합 임시 비밀번호 생성
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # 2. 비밀번호 해싱 및 DB 업데이트
        user.password_hash = get_password_hash(temp_password)
        db.add(user)
        db.commit()

        # 3. SMS 발송
        sms_text = f"[{user.store_name}] 임시 비밀번호는 [{temp_password}] 입니다. 로그인 후 반드시 변경해주세요."
        sent = NotificationService.send_generic_sms(user.phone, sms_text)

        if not sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="임시 비밀번호 발송에 실패했습니다. 관리자에게 문의하세요."
            )

        return {"message": "임시 비밀번호가 휴대폰으로 발송되었습니다."}