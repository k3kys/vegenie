# app/controllers/user_controller.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import User
from app.schemas.user_schema import UserUpdate


class UserController:
    @staticmethod
    def get_me(current_user: User):
        # 현재 로그인한 사용자 객체 반환
        return current_user

    @staticmethod
    def update_profile(db: Session, current_user: User, user_in: UserUpdate):
        # 명세: phone/store_name만 변경 허용 (화이트리스트)
        # 스키마(UserUpdate)에서 이미 필터링되지만, 로직에서도 명시적으로 처리

        updates_made = False

        if user_in.phone is not None:
            current_user.phone = user_in.phone
            updates_made = True

        if user_in.store_name is not None:
            current_user.store_name = user_in.store_name
            updates_made = True

        if updates_made:
            db.add(current_user)
            db.commit()
            db.refresh(current_user)

        return current_user