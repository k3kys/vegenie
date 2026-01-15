from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# [기존]
class UserBase(BaseModel):
    username: str
    phone: str
    store_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    store_uuid: str
    created_at: datetime
    class Config:
        from_attributes = True

# [NEW] 로그인 및 토큰
class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


# app/schemas/user_schema.py (기존 내용 아래에 추가)

class UserUpdate(BaseModel):
    phone: Optional[str] = None
    store_name: Optional[str] = None
    username: Optional[str] = None  # [추가] 아이디 변경 허용
    password: Optional[str] = None  # [추가] 비밀번호 변경 허용

    class Config:
        extra = "forbid"  # 정의되지 않은 필드가 오면 422 Unprocessable Entity 발생 (사실상 거부)

class FindIdRequest(BaseModel):
    phone: str

class ResetPasswordRequest(BaseModel):
    username: str
    phone: str