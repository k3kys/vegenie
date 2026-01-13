# app/controllers/sales_controller.py
from datetime import date
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from app.models.models import User, SalesReport, SystemLog
from app.services.parser import ExcelParser
from app.services.notification import NotificationService

class SalesController:
    @staticmethod
    async def upload_sales(db: Session, current_user: User, file: UploadFile, report_date: date = None):
        # -------------------------------------------------------
        # [cite_start]Step 1) report_date 확정/검증 (서버 권위) [cite: 21]
        # -------------------------------------------------------
        server_today = date.today()

        if report_date is None:
            # 미제공 시 서버 today로 확정
            final_date = server_today
        else:
            # 제공 시 검증: 불일치 400
            if report_date != server_today:
                raise HTTPException(status_code=400, detail="Report date must match server today.")
            final_date = report_date

        # -------------------------------------------------------
        # Step 2~5) 엑셀 파싱 (기존 로직 동일)
        # -------------------------------------------------------
        try:
            parsed = await ExcelParser.parse_sales_file(file)
        except HTTPException as he:
            raise he  # 400 에러는 그대로 전달
        except Exception as e:
            db.add(SystemLog(type="UPLOAD", level="ERROR", source="SERVER", message=f"Parse Error: {str(e)}",
                             status="FAIL"))
            db.commit()
            raise HTTPException(status_code=400, detail="Excel parsing failed")

        # -------------------------------------------------------
        # [cite_start]Step 7) Total 재계산 (SSOT) [cite: 9]
        # -------------------------------------------------------
        total = parsed["hall"] + parsed["baemin"] + parsed["coupang"] + parsed["yogiyo"]

        # -------------------------------------------------------
        # [cite_start]Step 6) sales_reports upsert [cite: 21]
        # -------------------------------------------------------
        report = db.query(SalesReport).filter(
            SalesReport.user_id == current_user.id,
            SalesReport.report_date == final_date
        ).first()

        if not report:
            report = SalesReport(user_id=current_user.id, report_date=final_date)

        report.hall = parsed["hall"]
        report.baemin = parsed["baemin"]
        report.coupang = parsed["coupang"]
        report.yogiyo = parsed["yogiyo"]
        report.total_sales = total

        db.add(report)
        db.commit()
        db.refresh(report)  # ID 획득

        # -------------------------------------------------------
        # [cite_start]Step 8) report_notifications + 알림톡 발송 [cite: 16]
        # 정책: 알림 실패해도 업로드는 200 유지 (Try-Except 내부 처리)
        # -------------------------------------------------------
        NotificationService.send_daily_report(db, current_user, report)

        # -------------------------------------------------------
        # [cite_start]Step 9) System Log [cite: 21]
        # -------------------------------------------------------
        db.add(SystemLog(
            type="UPLOAD",
            level="INFO",
            source="SERVER",
            message="Upload & Parsing Success",
            status="SUCCESS",
            meta=f'{{"report_id": {report.report_id}, "total": {total}}}'
        ))
        db.commit()

        return report

    @staticmethod
    def _log(db, level, msg, user):
        # 시스템 로그 적재 헬퍼 (모델에 SystemLog가 있어야 함)
        try:
            log = SystemLog(
                type="UPLOAD",
                level=level,
                source="SERVER",
                message=msg,
                status="SUCCESS" if level == "INFO" else "FAIL",
                meta=f'{{"user_id": {user.id}}}'
            )
            db.add(log)
            # 여기서 commit은 메인 트랜잭션과 함께 처리되도록 함
        except:
            pass  # 로그 실패가 로직을 막지 않게