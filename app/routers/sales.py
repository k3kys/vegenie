from datetime import date, datetime, timedelta
import io
import openpyxl
from typing import Optional, List

from fastapi import APIRouter, Depends, File, UploadFile, Form, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import User, SalesReport
from app.core.deps import get_current_user
from app.controllers.sales_controller import SalesController
from app.schemas.sales_schema import SalesReportResponse, MonthlySalesResponse, MonthlySalesSummary

router = APIRouter()


@router.post("/upload", response_model=SalesReportResponse)
async def upload_sales_report(
        report_date: Optional[date] = Form(None),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await SalesController.upload_sales(db, current_user, file, report_date)


# [A5 추가] 월별 매출 조회
@router.get("/monthly", response_model=MonthlySalesResponse)
def get_monthly_sales(
        month: str = Query(..., description="YYYY-MM format"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        target_date = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

    # 월의 시작일과 끝일 계산
    start_date = date(target_date.year, target_date.month, 1)
    if target_date.month == 12:
        end_date = date(target_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)

    reports = db.query(SalesReport).filter(
        SalesReport.user_id == current_user.id,
        SalesReport.report_date >= start_date,
        SalesReport.report_date <= end_date
    ).order_by(SalesReport.report_date).all()

    daily_logs = []
    total_accumulated = 0

    for r in reports:
        total_accumulated += r.total_sales
        daily_logs.append(MonthlySalesSummary(
            date=str(r.report_date),
            total_sales=r.total_sales,
            platform_sales={
                "hall": r.hall,
                "baemin": r.baemin,
                "coupang": r.coupang,
                "yogiyo": r.yogiyo
            }
        ))

    return MonthlySalesResponse(
        month=month,
        total_accumulated=total_accumulated,
        daily_logs=daily_logs
    )


# [A5 추가] 엑셀 내보내기 (기간 지정)
@router.get("/export")
def export_sales_excel(
        start: date,
        end: date,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # [cite_start]1. 서버 최종 방어: 미래 날짜 요청 차단 [cite: 21]
    if end > date.today():
        raise HTTPException(status_code=400, detail="Cannot export future data.")

    if start > end:
        raise HTTPException(status_code=400, detail="Start date cannot be after end date.")

    # 2. 데이터 조회
    reports = db.query(SalesReport).filter(
        SalesReport.user_id == current_user.id,
        SalesReport.report_date >= start,
        SalesReport.report_date <= end
    ).order_by(SalesReport.report_date).all()

    # 3. 엑셀 생성 (In-memory)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "매출내역"
    ws.append(["날짜", "총매출", "홀", "배달의민족", "쿠팡이츠", "요기요"])

    for r in reports:
        ws.append([str(r.report_date), r.total_sales, r.hall, r.baemin, r.coupang, r.yogiyo])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"sales_{start}_{end}.xlsx"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}

    return StreamingResponse(
        output,
        headers=headers,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )