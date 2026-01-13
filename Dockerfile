# 1. 가볍고 안정적인 Python 3.10 버전 사용
FROM python:3.10-slim

# 2. 타임존 설정 (한국 시간) - 좀비 감지 로직 필수!
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 전체 복사
COPY . .

# 6. 실행 명령어 (Uvicorn 실행)
# host 0.0.0.0은 컨테이너 외부 접속 허용을 위해 필수
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]