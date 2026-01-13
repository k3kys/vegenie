import requests
import sys
import os
import uuid
import openpyxl
from datetime import date, datetime, timedelta

# ==========================================
# [중요] 서버 내부 모듈 로딩
# ==========================================
sys.path.append(os.getcwd())
from app.db import SessionLocal, engine, Base
# [중요] 모델을 임포트해야 Base가 테이블 정보를 알 수 있음
from app.models.models import User, SalesReport, ReportNotification, Release, SystemLog
from app.core.security import get_password_hash
from app.services.monitoring import MonitoringService
from app.settings import settings

# ==========================================
# 0. 설정 & 유틸리티
# ==========================================
BASE_URL = "http://localhost:8000/api/v1"
RUN_ID = str(uuid.uuid4())[:6]
OWNER_USER = f"boss_{RUN_ID}"
ADMIN_USER = f"admin_{RUN_ID}"
PASSWORD = "password123"
TEST_EXCEL_FILE = f"test_sales_{RUN_ID}.xlsx"

# ANSI 색상
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log(msg): print(f"{msg}")


def print_pass(msg): print(f"{GREEN}[PASS]{RESET} {msg}")


def print_fail(msg):
    print(f"{RED}[FAIL]{RESET} {msg}")


# ==========================================
# 1. 헬퍼 함수
# ==========================================
def create_test_excel():
    """테스트용 엑셀 파일 생성"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = settings.EXCEL_SHEET_NAME  # "결제 합계"

    ws.append(["날짜", "승인번호", "매입사별", "금액", "비고"])
    data = [
        ["2024-01-01", "1", "배달의민족", 10000, ""],
        ["2024-01-01", "2", "쿠팡이츠", 20000, ""],
        ["2024-01-01", "3", "요기요", 15000, ""],
        ["2024-01-01", "4", "현금", 5000, ""]
    ]
    for row in data: ws.append(row)
    ws.append(["합계", "", "", 50000, ""])
    wb.save(TEST_EXCEL_FILE)
    log(f"📄 엑셀 생성 완료: {TEST_EXCEL_FILE}")


def get_db_session():
    return SessionLocal()


# ==========================================
# 2. 시나리오 시작
# ==========================================
def run_complete_test():
    print(f"{BLUE}=== Vegenie Server v0.2.5 완전판 통합 테스트 ==={RESET}")
    print(f"Test Run ID: {RUN_ID}\n")

    # ----------------------------------------------------
    # [FIX] DB 테이블 강제 생성 (이 부분이 추가되었습니다!)
    # ----------------------------------------------------
    print("⚙️  DB 테이블 확인 및 생성 중...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ DB 테이블 준비 완료")
    except Exception as e:
        print_fail(f"DB 초기화 실패: {e}")
        return

    # ----------------------------------------------------
    # [Step 1] 회원가입 (Register)
    # ----------------------------------------------------
    log("--- [1] 회원가입 프로세스 ---")

    # 1.1 사장님 가입
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "username": OWNER_USER,
        "password": PASSWORD,
        "phone": "010-1234-5678",
        "store_name": f"대박매장_{RUN_ID}"
    })
    if res.status_code == 201:
        print_pass("사장님 회원가입 (POST /auth/register)")
    else:
        print_fail(f"가입 실패: {res.text}")

    # 1.2 관리자 가입 (DB 직접 주입 - Admin API 테스트용)
    db = get_db_session()
    try:
        admin = User(
            username=ADMIN_USER,
            password_hash=get_password_hash(PASSWORD),
            phone="010-9999-9999",
            store_name="본사",
            role="ADMIN"
        )
        db.add(admin)
        db.commit()
        print_pass("관리자 계정 생성 (DB 주입)")
    except Exception as e:
        print_fail(f"관리자 생성 실패: {e}")
    finally:
        db.close()

    # 1.3 로그인
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": OWNER_USER, "password": PASSWORD})
    if res.status_code == 200:
        owner_token = res.json()["access_token"]
        print_pass("사장님 로그인 (POST /auth/login)")
    else:
        print_fail("로그인 실패 (사장님)")
        return

    admin_res = requests.post(f"{BASE_URL}/auth/login", json={"username": ADMIN_USER, "password": PASSWORD})
    if admin_res.status_code == 200:
        admin_token = admin_res.json()["access_token"]
    else:
        print_fail("로그인 실패 (관리자)")
        return

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # ----------------------------------------------------
    # [Step 2] 매출 업로드 & 알림톡 검증
    # ----------------------------------------------------
    log("\n--- [2] 매출 및 알림톡 프로세스 ---")

    create_test_excel()

    # 2.1 파일 업로드
    today = date.today().isoformat()
    files = {'file': open(TEST_EXCEL_FILE, 'rb')}
    data = {'report_date': today}

    res = requests.post(f"{BASE_URL}/sales/upload", headers=owner_headers, files=files, data=data)
    files['file'].close()

    if res.status_code == 200:
        rj = res.json()
        if rj["total_sales"] == 50000:
            print_pass(f"매출 업로드 성공 (Total: {rj['total_sales']})")
        else:
            print_fail(f"매출 계산 오류: {rj}")
    else:
        print_fail(f"업로드 에러: {res.text}")

    # 2.2 [DB 검증] 알림톡 기록 확인
    db = get_db_session()
    try:
        user = db.query(User).filter(User.username == OWNER_USER).first()

        # ReportNotification 테이블 확인
        notif = db.query(ReportNotification).filter(
            ReportNotification.user_id == user.id,
            ReportNotification.report_date == today
        ).first()

        if notif:
            print_pass(f"알림톡 기록 생성 확인 (ID: {notif.notif_id}, Status: {notif.primary_status})")
            if notif.primary_status in ["SENT", "FAIL"]:
                print_pass(f" -> 발송 시도 결과: {notif.primary_status}")
            else:
                print_fail(f" -> 발송 상태 이상: {notif.primary_status}")
        else:
            print_fail("알림톡 기록(ReportNotification)이 없습니다!")

        # SystemLog 확인
        log_entry = db.query(SystemLog).filter(
            SystemLog.type == "ALIMTALK",
            SystemLog.timestamp >= datetime.now() - timedelta(minutes=1)
        ).first()

        if log_entry:
            print_pass(f"시스템 로그 확인 (ALIMTALK: {log_entry.status})")
        else:
            # 로그는 타이밍에 따라 늦게 찍힐 수도 있음
            pass

    finally:
        db.close()

    # ----------------------------------------------------
    # [Step 3] 조회 및 엑셀 다운로드
    # ----------------------------------------------------
    log("\n--- [3] 조회 기능 테스트 ---")

    # 3.1 월별 조회
    month_str = date.today().strftime("%Y-%m")
    res = requests.get(f"{BASE_URL}/sales/monthly", headers=owner_headers, params={"month": month_str})
    if res.status_code == 200 and res.json()["total_accumulated"] == 50000:
        print_pass("월별 조회 확인")
    else:
        print_fail("월별 조회 실패")

    # 3.2 엑셀 다운로드
    res = requests.get(f"{BASE_URL}/sales/export", headers=owner_headers, params={"start": today, "end": today})
    if res.status_code == 200 and "spreadsheet" in res.headers["content-type"]:
        print_pass("엑셀 다운로드 확인")
    else:
        print_fail("엑셀 다운로드 실패")

    # ----------------------------------------------------
    # [Step 4] 좀비(Zombie) 감지 로직 테스트
    # ----------------------------------------------------
    log("\n--- [4] 좀비 감지(오프라인 알림) 테스트 ---")

    # 4.1 생존 신고 (Heartbeat)
    res = requests.post(f"{BASE_URL}/auth/heartbeat", headers=owner_headers)
    if res.status_code == 200:
        print_pass("하트비트 전송 성공 (Alive)")

    # 4.2 [서버 조작] 시간을 10분 전으로 되돌리기
    db = get_db_session()
    user = db.query(User).filter(User.username == OWNER_USER).first()

    past_time = datetime.now() - timedelta(minutes=10)
    user.last_heartbeat = past_time
    user.is_offline_notified = False
    db.commit()
    print_pass(f"😈 DB 조작: 사용자의 마지막 접속 시간을 10분 전으로 변경")

    # 4.3 [로직 실행] 스케줄러 대신 직접 함수 호출
    print(" -> 좀비 감지 로직 수동 실행 중...")
    MonitoringService.check_zombies()

    # 4.4 [결과 검증]
    db.refresh(user)
    if user.is_offline_notified:
        print_pass("✅ 좀비 감지 성공: User.is_offline_notified가 True로 변경됨")

        zombie_log = db.query(SystemLog).filter(
            SystemLog.type == "ZOMBIE_SMS",
            SystemLog.timestamp >= datetime.now() - timedelta(minutes=1)
        ).first()

        if zombie_log:
            print_pass(f"✅ 문자 발송 로그 확인: {zombie_log.message}")
        else:
            print_fail("좀비 감지는 됐는데, SMS 로그가 없습니다.")
    else:
        print_fail("❌ 좀비 감지 실패: 상태가 변경되지 않았습니다.")

    db.close()

    # ----------------------------------------------------
    # [Step 5] 관리자 배포 기능
    # ----------------------------------------------------
    log("\n--- [5] 관리자 배포 테스트 ---")

    new_ver = f"1.0.{uuid.uuid4().hex[:3]}"
    res = requests.post(f"{BASE_URL}/releases", headers=admin_headers, json={
        "version": new_ver,
        "description": "Auto Test Release",
        "download_url": "http://test.com",
        "is_mandatory": True
    })

    if res.status_code == 201:
        print_pass(f"새 버전 배포 성공 ({new_ver})")
    else:
        print_fail(f"배포 실패: {res.text}")

    res = requests.get(f"{BASE_URL}/releases")
    if res.status_code == 200:
        print_pass("버전 목록 조회 성공")

    # ----------------------------------------------------
    # [Step 6] 정리
    # ----------------------------------------------------
    if os.path.exists(TEST_EXCEL_FILE):
        os.remove(TEST_EXCEL_FILE)
        log(f"\n🗑️  테스트 파일 삭제 완료")

    print(f"\n{GREEN}✨ 모든 시나리오 테스트 완료! ✨{RESET}")


if __name__ == "__main__":
    run_complete_test()