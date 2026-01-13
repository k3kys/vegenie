from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class SystemVersion(BaseModel):
    version: str
    status: str
    timezone: str


class HeartbeatResponse(BaseModel):
    status: str
    last_heartbeat: str


# [A5] 리포트 이력
class ReportHistoryItem(BaseModel):
    report_date: date
    upload_status: str
    primary_status: str
    sent_at: Optional[datetime]


class ReportDetailResponse(ReportHistoryItem):
    primary_body: Optional[str]
    error_message: Optional[str]


# [A5] 릴리즈 정보
class ReleaseInfo(BaseModel):
    version: str
    description: Optional[str]
    download_url: str
    is_mandatory: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReleaseCreate(BaseModel):
    version: str
    # [수정] = None 을 추가하여 입력하지 않아도 에러가 나지 않게 함
    description: Optional[str] = None
    download_url: str
    is_mandatory: bool = False