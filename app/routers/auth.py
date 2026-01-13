from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.user_schema import UserCreate, UserResponse, UserLogin, Token
from app.controllers.auth_controller import AuthController
from app.models.models import User
from app.core.deps import get_current_user
from app.schemas.system import HeartbeatResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    회원가입 API
    - store_uuid는 서버에서 자동 생성됩니다.
    - password는 bcrypt로 해싱되어 저장됩니다.
    """
    return AuthController.register_user(db, user_in)

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """
    로그인 API
    - JWT Access Token을 발급합니다.
    """
    return AuthController.login_user(db, user_in)

@router.post("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Heartbeat API
    - 클라이언트는 1분마다 이 API를 호출해야 함.
    - 호출 시 last_heartbeat 갱신 및 좀비 상태 해제.
    """
    return AuthController.process_heartbeat(db, current_user)