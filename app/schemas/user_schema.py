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

    # 그 외 필드(username, role 등)가 들어오면 에러를 뱉거나 무시하도록 설정
    # 명세의 "변경 거부"를 확실히 하기 위해, Pydantic 레벨에서 필터링합니다.
    class Config:
        extra = "forbid"  # 정의되지 않은 필드가 오면 422 Unprocessable Entity 발생 (사실상 거부)