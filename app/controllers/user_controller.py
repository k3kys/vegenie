# app/controllers/user_controller.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import User
from app.schemas.user_schema import UserUpdate
from app.core.security import get_password_hash  # [필수] 비밀번호 암호화를 위해 추가


class UserController:
    @staticmethod
    def get_me(current_user: User):
        # 현재 로그인한 사용자 객체 반환
        return current_user

    @staticmethod
    def update_profile(db: Session, current_user: User, user_in: UserUpdate):
        """
        프로필 수정 로직
        - 전화번호, 매장명 수정 (기존)
        - 아이디, 비밀번호 수정 (신규 추가)
        """
        updates_made = False

        # 1. 전화번호 수정
        if user_in.phone is not None and user_in.phone != current_user.phone:
            current_user.phone = user_in.phone
            updates_made = True

        # 2. 매장명 수정
        if user_in.store_name is not None and user_in.store_name != current_user.store_name:
            current_user.store_name = user_in.store_name
            updates_made = True

        # 3. [신규] 아이디 수정 (중복 체크 필수)
        if user_in.username is not None and user_in.username != current_user.username:
            # DB에서 중복된 아이디가 있는지 확인
            existing_user = db.query(User).filter(User.username == user_in.username).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="이미 존재하는 아이디입니다."
                )

            current_user.username = user_in.username
            updates_made = True

        # 4. [신규] 비밀번호 수정 (해싱 필수)
        # 빈 문자열이나 공백만 있는 경우는 변경하지 않음
        if user_in.password is not None and user_in.password.strip() != "":
            # 비밀번호 해싱하여 저장
            current_user.password_hash = get_password_hash(user_in.password)
            updates_made = True

        # 변경사항이 하나라도 있으면 DB 커밋
        if updates_made:
            db.add(current_user)
            db.commit()
            db.refresh(current_user)

        return current_user