import requests
import json
import datetime
import hmac
import hashlib
import uuid
from sqlalchemy.orm import Session

# 프로젝트 내부 모듈 임포트
from app.models.models import ReportNotification, User, SalesReport, SystemLog
from app.settings import settings


class NotificationService:
    # ------------------------------------------------------------------
    # [공통] Solapi API 인증 헤더 생성기
    # ------------------------------------------------------------------
    @staticmethod
    def _get_solapi_header():
        """알림톡 및 SMS 발송을 위한 HMAC-SHA256 인증 헤더 생성"""
        date_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        salt = str(uuid.uuid4())
        data = date_str + salt
        signature = hmac.new(
            key=settings.SOLAPI_SECRET.encode("utf-8"),
            msg=data.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        return {
            "Authorization": f"HMAC-SHA256 apiKey={settings.SOLAPI_KEY}, date={date_str}, salt={salt}, signature={signature}",
            "Content-Type": "application/json"
        }

    # ------------------------------------------------------------------
    # [1] 알림톡 관련 로직 (일일 매출 보고 -> 관리자에게 전송)
    # ------------------------------------------------------------------
    @staticmethod
    def send_daily_report(db: Session, user: User, report: SalesReport):
        """
        [일일 매출 보고] -> 알림톡
        수신자: settings.MANAGER_PHONE (관리자)
        """
        body = (
            f"[{user.store_name}] {report.report_date} 일일매출\n"
            f"총 : {report.total_sales:,}\n\n"
            f"홀 : {report.hall:,}\n"
            f"배민 : {report.baemin:,}\n"
            f"쿠팡 : {report.coupang:,}\n"
            f"요기요 : {report.yogiyo:,}\n"
            f"입니다."
        )

        # 이미 보낸 이력이 있는지 확인
        notif = db.query(ReportNotification).filter(
            ReportNotification.user_id == user.id,
            ReportNotification.report_date == report.report_date
        ).first()

        if not notif:
            notif = ReportNotification(
                user_id=user.id,
                report_date=report.report_date,
                upload_status="RECEIVED",
                primary_channel="ALIMTALK"
            )
            db.add(notif)

        try:
            url = "https://api.solapi.com/messages/v4/send"
            headers = NotificationService._get_solapi_header()
            data = {
                "message": {
                    "to": settings.MANAGER_PHONE,
                    "from": settings.SENDER_PHONE,
                    "text": body,
                    "kakaoOptions": {
                        "pfId": settings.KAKAO_PF_ID,
                        "templateId": settings.KAKAO_TEMPLATE_ID,
                        "disableSms": True
                    }
                }
            }
            resp = requests.post(url, headers=headers, json=data).json()

            notif.primary_status = "SENT"
            notif.primary_body = body
            notif.provider_message_id = resp.get("messageId")
            notif.updated_at = datetime.datetime.now()

            db.add(SystemLog(type="ALIMTALK", level="INFO", source="SERVER", message="Daily report sent",
                             status="SUCCESS"))
            print(f"[ALIMTALK SUCCESS] MessageId: {resp.get('messageId')}")

        except Exception as e:
            error_msg = str(e)
            notif.primary_status = "FAIL"
            notif.error_message = error_msg
            notif.updated_at = datetime.datetime.now()

            db.add(
                SystemLog(type="ALIMTALK", level="ERROR", source="SERVER", message=f"Fail: {error_msg}", status="FAIL"))
            print(f"[ALIMTALK FAIL] {error_msg}")

        db.commit()

    # ------------------------------------------------------------------
    # [2] 좀비 알림 로직 (PC 꺼짐 감지 -> 사장님에게 전송)
    # ------------------------------------------------------------------
    @staticmethod
    def send_zombie_alert(db: Session, user: User):
        """
        [좀비 와쳐 알림]
        수신자: user.phone (해당 매장 사장님)
        """
        print(f"\n=== 🧟 좀비 알림 발송 시작 (To Owner) ===")

        if not user.phone:
            error_msg = f"User {user.username} ({user.store_name}) has no phone number."
            print(f"[ZOMBIE FAIL] {error_msg}")
            db.add(SystemLog(type="ZOMBIE_SMS", level="ERROR", source="SERVER", message=error_msg, status="FAIL"))
            db.commit()
            return False

        text_body = f"[{user.store_name}] 베지나이가 종료되었습니다. 다시 켜주세요."

        try:
            url = "https://api.solapi.com/messages/v4/send"
            headers = NotificationService._get_solapi_header()
            body = {
                "message": {
                    "to": user.phone,
                    "from": settings.SENDER_PHONE,
                    "text": text_body,
                    "type": "SMS"
                }
            }

            res = requests.post(url, headers=headers, json=body)

            if res.status_code != 200:
                raise Exception(f"Solapi API Error: {res.text}")

            resp = res.json()
            db.add(SystemLog(
                type="ZOMBIE_SMS",
                level="WARN",
                source="SERVER",
                message=f"Zombie Alert sent to {user.store_name}",
                status="SUCCESS",
                meta=f'{{"user_id": {user.id}, "phone": "{user.phone}"}}'
            ))
            db.commit()
            print(f"[ZOMBIE SMS SUCCESS] MessageId: {resp.get('messageId')}")
            return True

        except Exception as e:
            print(f"[ZOMBIE SMS FAIL] {str(e)}")
            db.add(SystemLog(type="ZOMBIE_SMS", level="ERROR", source="SERVER", message=str(e), status="FAIL"))
            db.commit()
            return False

    # ------------------------------------------------------------------
    # [3] 공통 SMS 발송 함수 (아이디/비번 찾기용)
    # ------------------------------------------------------------------
    @staticmethod
    def send_generic_sms(phone: str, text: str) -> bool:
        """
        아이디 찾기나 임시 비밀번호 발급과 같은 일반 SMS 발송을 처리합니다.
        """
        try:
            url = "https://api.solapi.com/messages/v4/send"
            headers = NotificationService._get_solapi_header()
            body = {
                "message": {
                    "to": phone,
                    "from": settings.SENDER_PHONE,
                    "text": text,
                    "type": "SMS"
                }
            }

            res = requests.post(url, headers=headers, json=body)
            return res.status_code == 200

        except Exception as e:
            print(f"[GENERIC SMS FAIL] {str(e)}")
            return False