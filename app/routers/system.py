from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.db import get_db
from app.models.models import User, ReportNotification, Release
from app.schemas.system import SystemVersion, ReportHistoryItem, ReportDetailResponse, ReleaseInfo, ReleaseCreate
from app.core.deps import get_current_user
from app.settings import settings

# [중요] 라우터 생성
router = APIRouter()


# ---------------------------------------------------------
# 1. System Info (경로 명시: /system/version)
# ---------------------------------------------------------
@router.get("/system/version", response_model=SystemVersion)
def get_version():
    return {
        "version": settings.VERSION,
        "status": "running",
        "timezone": settings.TIMEZONE
    }


# ---------------------------------------------------------
# 2. Reports (경로: /reports/...)
# ---------------------------------------------------------
@router.get("/reports/history", response_model=List[ReportHistoryItem])
def get_report_history(
        days: int = 10,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """최근 N일간의 리포트 알림 상태 요약"""
    history = db.query(ReportNotification).filter(
        ReportNotification.user_id == current_user.id
    ).order_by(ReportNotification.report_date.desc()).limit(days).all()

    return [
        ReportHistoryItem(
            report_date=h.report_date,
            upload_status=h.upload_status,
            primary_status=h.primary_status,
            sent_at=h.updated_at
        ) for h in history
    ]


@router.get("/reports/history/{report_date}", response_model=ReportDetailResponse)
def get_report_detail(
        report_date: date,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """특정 날짜 알림 상세"""
    noti = db.query(ReportNotification).filter(
        ReportNotification.user_id == current_user.id,
        ReportNotification.report_date == report_date
    ).first()

    if not noti:
        raise HTTPException(status_code=404, detail="No report found for this date")

    return ReportDetailResponse(
        report_date=noti.report_date,
        upload_status=noti.upload_status,
        primary_status=noti.primary_status,
        sent_at=noti.updated_at,
        primary_body=noti.primary_body,
        error_message=noti.error_message
    )


# ---------------------------------------------------------
# 3. Releases (경로: /releases)
# ---------------------------------------------------------
@router.get("/releases", response_model=List[ReleaseInfo])
def get_releases(db: Session = Depends(get_db)):
    return db.query(Release).order_by(Release.id.desc()).all()


@router.post("/releases", response_model=ReleaseInfo, status_code=201)
def create_release(
        release_in: ReleaseCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can publish releases")

    existing = db.query(Release).filter(Release.version == release_in.version).first()
    if existing:
        raise HTTPException(status_code=400, detail="Version already exists")

    new_release = Release(
        version=release_in.version,
        description=release_in.description,
        download_url=release_in.download_url,
        is_mandatory=release_in.is_mandatory
    )
    db.add(new_release)
    db.commit()
    db.refresh(new_release)
    return new_release