# app/services/monitoring.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import User, SystemLog
from app.db import SessionLocal
from app.settings import settings
from app.services.notification import NotificationService  # [추가] 실제 발송을 위해 임포트


class MonitoringService:
    @staticmethod
    def log_event(db: Session, type: str, level: str, message: str, meta: str = None):
        """시스템 로그 적재 헬퍼"""
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
            # 여기서 commit 하지 않음 (호출자가 일괄 commit 하도록)
        except Exception as e:
            print(f"[Log Error] {e}")

    @staticmethod
    def send_zombie_alert(db: Session, user: User):
        """
        실제 Solapi SMS 발송 로직 연동
        """
        # NotificationService에 구현된 '안전한 패턴'의 SMS 발송 로직을 호출합니다.
        # 성공 시 True, 실패 시 False 반환
        return NotificationService.send_zombie_alert(db, user)

    @staticmethod
    def check_zombies():
        """
        주기적으로 실행되어 5분 이상 하트비트가 없는 유저를 감지합니다.
        """
        db = SessionLocal()
        try:
            # 기준: 현재시간 - 5분
            threshold = datetime.now() - timedelta(minutes=60)

            # 디버깅: 서버 시간 확인
            # print(f"[Monitoring] Checking at {datetime.now()} (Threshold: {threshold})")

            # 조건: 하트비트가 5분 전이고 + 아직 알림을 안 보낸(is_offline_notified=False) 유저
            zombies = db.query(User).filter(
                User.last_heartbeat < threshold,
                User.is_offline_notified == False
            ).all()

            if zombies:
                print(f"[Monitoring] Detected {len(zombies)} zombies.")

            for user in zombies:
                # 1. SMS 발송 시도 (NotificationService 위임)
                # db 세션을 같이 넘겨서 시스템 로그를 남길 수 있게 함
                sent = MonitoringService.send_zombie_alert(db, user)

                if sent:
                    # 2. 성공 시 상태 업데이트 (중복 발송 방지)
                    user.is_offline_notified = True
                    db.add(user)

                    # 3. 추가 로그 적재 (A3 요구사항)
                    MonitoringService.log_event(
                        db,
                        type="ZOMBIE_SMS",
                        level="WARN",
                        message=f"Zombie detected & Sent: {user.username} ({user.store_name})",
                        meta=f'{{"user_id": {user.id}}}'
                    )
                else:
                    # 실패 시 로그만 남기고, is_offline_notified는 False 유지 (다음 주기에 재시도)
                    print(f"[Monitoring] Failed to send SMS to {user.store_name}")

            # 변경사항 일괄 저장
            db.commit()

        except Exception as e:
            print(f"[Monitoring Error] {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def daily_reset():
        """
        [명세] 하루 1회 Zombie SMS + 00:05 리셋
        00:05에 실행되어 알림 상태를 초기화합니다.
        """
        print("[Scheduler] Daily Reset Logic Executed at 00:05")

        db = SessionLocal()
        try:
            # 모든 유저의 알림 상태를 초기화 (내일 다시 알림 받을 수 있게)
            db.query(User).update({User.is_offline_notified: False})
            db.commit()
            print("[Scheduler] All users' offline status reset to False.")
        except Exception as e:
            print(f"[Reset Error] {e}")
            db.rollback()
        finally:
            db.close()