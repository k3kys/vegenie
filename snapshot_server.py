import os

# ==========================================================
# [설정] 스냅샷을 찍을 규칙 정의
# ==========================================================
OUTPUT_FILE = "vegenie_server_snapshot.txt"

# 1. 무시할 폴더 (이 안의 내용은 보지 않음)
IGNORE_DIRS = [
    "venv", ".venv", "env", ".env",  # 가상환경
    ".git", ".idea", ".vscode",  # IDE 및 설정
    "__pycache__", "migrations",  # 파이썬 캐시 및 마이그레이션 파일
    "logs", "build", "dist",  # 로그 및 빌드 부산물
    "static", "media"  # 정적 파일 (용량 큼)
]

# 2. 무시할 파일 (파일명이 정확히 일치하면 제외)
IGNORE_FILES = [
    ".DS_Store", "db.sqlite3",  # 시스템 파일 및 DB 파일
    "poetry.lock", "package-lock.json",  # 락 파일 (너무 김)
    "snapshot_server.py",  # 자기 자신
    OUTPUT_FILE  # 결과 파일
]

# 3. 포함할 확장자 (이 확장자만 읽음)
INCLUDE_EXTENSIONS = [
    ".py",  # 파이썬 코드
    ".html",  # 템플릿 (필요 시)
    ".yaml", ".yml",  # 설정 파일
    ".json",  # 설정 파일
    ".md",  # 문서
    ".txt",  # requirements.txt 등
    ".sh",  # 쉘 스크립트
    "Dockerfile", "docker-compose.yml"  # 도커 관련
]


def is_ignored(path, names):
    # 무시할 폴더가 포함되어 있으면 해당 리스트 반환 (os.walk용)
    return {name for name in names if name in IGNORE_DIRS}


def create_snapshot():
    current_dir = os.getcwd()
    print(f"📸 서버 코드 스냅샷 생성 시작: {current_dir}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f"VEGENIE SERVER SNAPSHOT\n")
        out.write(f"====================================\n\n")

        for root, dirs, files in os.walk(current_dir):
            # 무시할 폴더 제거 (하위 탐색 방지)
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                # 1. 무시할 파일명 체크
                if file in IGNORE_FILES:
                    continue

                # 2. 확장자 체크
                _, ext = os.path.splitext(file)
                # Dockerfile 같은 건 확장자가 없으므로 파일명 자체도 체크
                if ext not in INCLUDE_EXTENSIONS and file not in INCLUDE_EXTENSIONS:
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, current_dir)

                print(f"Processing: {relative_path}")

                # 파일 내용 쓰기
                try:
                    out.write(f"\n{'=' * 50}\n")
                    out.write(f"[File Path]: {relative_path}\n")
                    out.write(f"{'=' * 50}\n")

                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        out.write(content + "\n")

                except Exception as e:
                    out.write(f"\n[Error reading file]: {e}\n")

    print(f"\n✅ 완료! '{OUTPUT_FILE}' 파일이 생성되었습니다.")


if __name__ == "__main__":
    create_snapshot()