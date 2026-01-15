from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.user_schema import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    FindIdRequest,
    ResetPasswordRequest
)
from app.controllers.auth_controller import AuthController
from app.models.models import User
from app.core.deps import get_current_user
from app.schemas.system import HeartbeatResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    회원가입 API [cite: 304]
    - store_uuid는 서버에서 자동 생성됩니다. [cite: 304]
    - password는 bcrypt로 해싱되어 저장됩니다. [cite: 304]
    """
    return AuthController.register_user(db, user_in)

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """
    로그인 API [cite: 304]
    - JWT Access Token을 발급합니다. [cite: 304]
    """
    return AuthController.login_user(db, user_in)

@router.post("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Heartbeat API [cite: 305]
    - 클라이언트는 1분마다 이 API를 호출해야 함. [cite: 305]
    - 호출 시 last_heartbeat 갱신 및 좀비 상태 해제. [cite: 306]
    """
    return AuthController.process_heartbeat(db, current_user)

# ------------------------------------------------------------------
# [신규 추가] 아이디 / 비밀번호 찾기 엔드포인트
# ------------------------------------------------------------------

@router.post("/find-id")
def find_id(user_in: FindIdRequest, db: Session = Depends(get_db)):
    """
    아이디 찾기 API
    - 휴대폰 번호를 통해 마스킹 처리된 아이디를 반환합니다.
    """
    return AuthController.find_username(db, user_in)

@router.post("/reset-password")
def reset_password(user_in: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    비밀번호 재설정 API
    - 아이디와 번호가 일치하면 임시 비밀번호를 생성하여 SMS로 발송합니다.
    """
    return AuthController.reset_password(db, user_in)