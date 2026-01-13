from pydantic_settings import BaseSettings
import os # [추가]

class Settings(BaseSettings):
    PROJECT_NAME: str = "Vegenie"
    VERSION: str = "v0.2.5"
    API_V1_STR: str = "/api/v1"

    TIMEZONE: str = "Asia/Seoul"
    DATABASE_URL: str = "sqlite:///./vegenie.db"

    # 엑셀 파싱 계약
    EXCEL_PASSWORD: str = "7055"
    EXCEL_SHEET_NAME: str = "결제 합계"

    # JWT 설정
    SECRET_KEY: str = "vegenie-secret-key-change-this-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # --------------------------------------------------------
    # [G. 알림/운영 고정값] - Solapi & Kakao Real Keys
    # --------------------------------------------------------
    # Solapi API Key
    SOLAPI_KEY: str = "NCS4COIDQ681XXPL"
    SOLAPI_SECRET: str = "4IWZDH2PMMQJXBZRDRA5Z7SQUTP8VFSX"

    # Kakao AlimTalk IDs
    KAKAO_PF_ID: str = "KA01PF251225055208641PWbN0JWVOo8"
    KAKAO_TEMPLATE_ID: str = "KA01TP2512271353576383sumVHXbRGu"

    # Phone Numbers
    MANAGER_PHONE: str = "01089993264"  # 수신자
    SENDER_PHONE: str = "01021123558"  # 발신자 (Solapi에 등록된 번호여야 함)

    # [수정] 환경변수 'DATABASE_URL'이 있으면 그걸 쓰고, 없으면 기존 SQLite 사용 (로컬 테스트용)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vegenie.db")

settings = Settings()