from datetime import datetime, timedelta, date  # date 추가
from sqlalchemy import func  # DB 날짜 비교를 위해 추가
from sqlalchemy.orm import Session
from app.models.models import User, SystemLog
from app.db import SessionLocal
from app.settings import settings
from app.services.notification import NotificationService


class MonitoringService:
    @staticmethod
    def log_event(db: Session, type: str, level: str, message: str, meta: str = None):
        """시스템 로그 적재 헬퍼 (기존 기능 유지)"""
        try:
            log = SystemLog(
                type=type,
                level=level,
                source="SERVER",
                message=message,
                status="SUCCESS",
                meta=meta
            )
            db.add(log)
        except Exception as e:
            print(f"[Log Error] {e}")

    @staticmethod
    def send_zombie_alert(db: Session, user: User):
        """실제 Solapi SMS 발송 로직 연동 (기존 기능 유지)"""
        return NotificationService.send_zombie_alert(db, user)

    @staticmethod
    def check_zombies():
        """
        주기적으로 실행되어 좀비를 감지합니다.
        개선사항: 심야 발송 제한 + 오늘 신호가 있었던 매장만 감시
        """
        db = SessionLocal()
        try:
            now = datetime.now()

            # [추가] 심야 발송 제한: 밤 10시 ~ 아침 8시 사이에는 문자를 보내지 않음
            if now.hour >= 22 or now.hour < 8:
                return

            # 기준: 현재시간 - 60분
            threshold = now - timedelta(minutes=60)
            today_date = date.today()

            # [수정] 조건:
            # 1. 감시 활성 상태(is_offline_notified=True)
            # 2. 하트비트 60분 경과
            # 3. 마지막 신호가 '오늘' 발생 (새벽/휴무일 문자 방지)
            zombies = db.query(User).filter(
                User.is_offline_notified == True,
                User.last_heartbeat < threshold,
                func.date(User.last_heartbeat) == today_date
            ).all()

            if zombies:
                print(f"[Monitoring] Detected {len(zombies)} zombies to notify today.")

            for user in zombies:
                # 1. SMS 발송 시도
                sent = MonitoringService.send_zombie_alert(db, user)

                # [수정] 사용자 요청: 문자 발송 후 False로 변경하여 오늘 더 이상 안 보냄
                user.is_offline_notified = False
                db.add(user)

                if sent:
                    MonitoringService.log_event(
                        db,
                        type="ZOMBIE_SMS",
                        level="WARN",
                        message=f"Zombie detected & Sent: {user.username} ({user.store_name})",
                        meta=f'{{"user_id": {user.id}}}'
                    )
                else:
                    print(f"[Monitoring] Failed to send SMS to {user.store_name}")
                    MonitoringService.log_event(
                        db,
                        type="ZOMBIE_SMS",
                        level="ERROR",
                        message=f"Zombie SMS Failed: {user.username}",
                        meta=f'{{"user_id": {user.id}}}'
                    )

            db.commit()

        except Exception as e:
            print(f"[Monitoring Error] {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def daily_reset():
        """
        [사용자 명세 반영] 00:05 리셋 시 모든 유저를 감시 가능 상태(True)로 변경
        """
        print("[Scheduler] Daily Reset Logic Executed at 00:05 (Set to True)")

        db = SessionLocal()
        try:
            # 모든 유저의 알림 상태를 True(감시 대기)로 초기화
            db.query(User).update({User.is_offline_notified: True})
            db.commit()
            print("[Scheduler] All users' monitoring status reset to True.")
        except Exception as e:
            print(f"[Reset Error] {e}")
            db.rollback()
        finally:
            db.close()