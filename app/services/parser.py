import io
import msoffcrypto
import pandas as pd
import openpyxl
from datetime import date, datetime  # [추가] 날짜 비교용
from fastapi import UploadFile, HTTPException
from app.settings import settings


class ExcelParser:
    @staticmethod
    async def parse_sales_file(file: UploadFile):
        # 1. 파일 준비
        file_content = await file.read()
        file_io = io.BytesIO(file_content)
        decrypted = io.BytesIO()
        try:
            office_file = msoffcrypto.OfficeFile(file_io)
            office_file.load_key(password=settings.EXCEL_PASSWORD)
            office_file.decrypt(decrypted)
            decrypted.seek(0)
        except Exception:
            file_io.seek(0)
            decrypted = file_io

        # 2. 엑셀 읽기
        try:
            df = pd.read_excel(decrypted, sheet_name=settings.EXCEL_SHEET_NAME, header=None)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Excel parsing error: {str(e)}")

        # 3. 헤더 찾기 (키워드 기반)
        header_row_idx = -1
        keywords = ["카드", "현금", "배민", "배달", "쿠팡", "요기요", "이체", "KB국민카드", "신한카드", "비씨카드"]

        for r_idx, row in df.iterrows():
            row_str = " ".join([str(val) for val in row if pd.notna(val)])
            if any(k in row_str for k in keywords):
                header_row_idx = r_idx
                break

        if header_row_idx == -1:
            for r_idx, row in df.iterrows():
                if "매입사별" in " ".join([str(val) for val in row if pd.notna(val)]):
                    if r_idx + 1 < len(df):
                        header_row_idx = r_idx + 1
                        break
            if header_row_idx == -1:
                raise HTTPException(status_code=400, detail="Cannot find header row.")

        # 4. 데이터 행 추출
        if header_row_idx + 1 >= len(df):
            return {"hall": 0, "baemin": 0, "coupang": 0, "yogiyo": 0}

        header_row = df.iloc[header_row_idx]

        # [NEW] 데이터 날짜 검증 로직 시작 =================================
        # 헤더 바로 아랫줄이 데이터라고 가정하고, 첫 번째 컬럼(0번)을 날짜로 확인
        data_row = df.iloc[header_row_idx + 1]

        try:
            raw_date = data_row[0]  # 첫 번째 칸 가져오기
            excel_date = None

            # 1) 이미 날짜 형식이면 그대로 사용
            if isinstance(raw_date, (pd.Timestamp, datetime, date)):
                excel_date = raw_date.date() if isinstance(raw_date, (pd.Timestamp, datetime)) else raw_date

            # 2) 문자열이면 파싱 시도 ("2026-01-12" or "2026.01.12")
            elif isinstance(raw_date, str):
                clean_date_str = raw_date.strip().replace('.', '-')
                excel_date = datetime.strptime(clean_date_str, "%Y-%m-%d").date()

            # 3) 검증: 엑셀 날짜 vs 오늘 날짜
            if excel_date:
                server_today = date.today()
                if excel_date != server_today:
                    print(f"❌ 날짜 불일치 차단! 엑셀: {excel_date}, 서버: {server_today}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Report date mismatch. File date: {excel_date}, Today: {server_today}"
                    )
                else:
                    print(f"✅ 날짜 검증 통과: {excel_date}")

        except HTTPException as he:
            raise he  # 불일치 에러는 그대로 던짐
        except Exception as e:
            # 날짜 파싱 실패 시: 일단 경고만 하고 넘어가거나, 정책에 따라 막을 수도 있음
            # 여기서는 안전하게 로그만 찍고 넘어갑니다. (양식이 다를 수 있으므로)
            print(f"⚠️ 날짜 파싱 실패 (검증 건너뜀): {e}")
        # =================================================================

        # 5. 데이터 파싱 및 합산
        result = {"hall": 0, "baemin": 0, "coupang": 0, "yogiyo": 0}

        for i in range(header_row_idx + 1, len(df)):
            data_row = df.iloc[i]
            row_str = " ".join([str(v) for v in data_row if pd.notna(v)])
            if not row_str or "합계" in row_str or "소계" in row_str: continue

            for col_idx in range(len(header_row)):
                col_name = str(header_row[col_idx]).strip()
                raw_val = data_row[col_idx]

                if pd.isna(col_name) or pd.isna(raw_val) or col_name == 'nan': continue

                # 중복 컬럼 블랙리스트
                if col_name in ["카드", "QR결제", "신용카드", "결제합계"]: continue
                if "금액" in col_name or "건수" in col_name or "총계" in col_name: continue

                # 금액 변환
                amount = 0
                try:
                    if isinstance(raw_val, (int, float)):
                        amount = int(raw_val)
                    else:
                        clean_str = str(raw_val).replace(",", "").replace("원", "").strip()
                        if clean_str.lstrip('-').isdigit():
                            amount = int(clean_str)
                except:
                    continue

                if amount == 0: continue

                # 분류 로직
                if "배달의민족" in col_name or "배민" in col_name:
                    result["baemin"] += amount
                elif "쿠팡" in col_name or "coupang" in col_name:
                    result["coupang"] += amount
                elif "요기요" in col_name or "yogiyo" in col_name:
                    result["yogiyo"] += amount
                else:
                    result["hall"] += amount

        return result