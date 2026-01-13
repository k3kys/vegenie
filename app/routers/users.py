from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.user_schema import UserResponse, UserUpdate
from app.models.models import User
from app.controllers.user_controller import UserController

# [FIX] 이 줄이 없어서 에러가 났습니다. 반드시 추가해주세요.
from app.core.deps import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    내 정보 조회 (Authentication 필수)
    """
    return UserController.get_me(current_user)

@router.put("/profile", response_model=UserResponse)
def update_user_profile(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    프로필 수정 (Authentication 필수)
    """
    return UserController.update_profile(db, current_user, user_in)