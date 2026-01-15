import io
import msoffcrypto
import pandas as pd
from datetime import date, datetime, timedelta
from fastapi import UploadFile, HTTPException
from app.settings import settings


class ExcelParser:
    @staticmethod
    async def parse_sales_file(file: UploadFile):
        # ---------------------------------------------------------
        # 🎯 [추가] 파일명 검증: "매출리포트" 또는 "토스POS다운로드" 포함 여부
        # ---------------------------------------------------------
        filename = file.filename or "" #
        if "매출리포트" not in filename and "토스POS다운로드" not in filename:
            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 파일명입니다. '매출리포트' 또는 '토스POS다운로드'가 포함된 파일만 처리 가능합니다."
            )

        # 1. 파일 준비 및 암호 해제 [cite: 370, 371]
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

        # 2. 엑셀 읽기 [cite: 372]
        try:
            df = pd.read_excel(decrypted, sheet_name=settings.EXCEL_SHEET_NAME, header=None)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Excel parsing error: {str(e)}")

        # 3. 메인 헤더 줄 찾기 ("결제수단별" 기준) [cite: 373]
        top_header_idx = -1
        for r_idx, row in df.iterrows():
            row_str = " ".join([str(val) for val in row if pd.notna(val)])
            if "결제수단별" in row_str:
                top_header_idx = r_idx
                break

        if top_header_idx == -1 or top_header_idx + 1 >= len(df):
            return {"hall": 0, "baemin": 0, "coupang": 0, "yogiyo": 0}

        # 날짜 검증 로직: 다음날 정오까지 허용 [cite: 376, 377, 380]
        try:
            data_row = df.iloc[top_header_idx + 2]
            raw_date = data_row[0]
            excel_date = None

            if isinstance(raw_date, (pd.Timestamp, datetime, date)):
                excel_date = raw_date.date() if isinstance(raw_date, (pd.Timestamp, datetime)) else raw_date
            elif isinstance(raw_date, str):
                clean_date_str = raw_date.strip().replace('.', '-')
                excel_date = datetime.strptime(clean_date_str, "%Y-%m-%d").date()

            if excel_date:
                now = datetime.now()
                today = now.date()
                yesterday = today - timedelta(days=1)

                if excel_date == today:
                    print(f"✅ 오늘 매출 확인: {excel_date}")
                elif excel_date == yesterday:
                    if now.hour < 12:
                        print(f"✅ 어제 매출 확인 (정오 이전): {excel_date}")
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"어제({excel_date}) 매출은 오늘 낮 12시까지만 보고 가능합니다."
                        )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"보고 가능한 날짜가 아닙니다. (엑셀 날짜: {excel_date})"
                    )
        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"⚠️ 날짜 검증 건너뜀 (파싱 실패): {e}")

        # 4. 컬럼 매핑 (부모-자식 구조)
        top_row = df.iloc[top_header_idx]
        sub_row = df.iloc[top_header_idx + 1]
        col_mapping = []
        current_parent = ""

        for col_idx in range(len(df.columns)):
            if pd.notna(top_row[col_idx]):
                current_parent = str(top_row[col_idx]).strip()
            child_name = str(sub_row[col_idx]).strip() if pd.notna(sub_row[col_idx]) else ""
            col_mapping.append({"parent": current_parent, "name": child_name})

        # 5. 데이터 합산 [cite: 385, 391]
        hall_sales = 0
        sales_baemin = 0
        sales_coupang = 0
        sales_yogiyo = 0

        baemin_keys = ["plugin_baemin", "baemin", "배민", "배달의 민족"]
        coupang_keys = ["plugin_coupang", "coupang", "쿠팡이츠", "쿠팡", "coupang eats"]
        yogiyo_keys = ["yogiyo", "plugin_yogiyo", "요기요"]

        for i in range(top_header_idx + 2, len(df)):
            curr_row = df.iloc[i]
            if not "".join([str(v) for v in curr_row if pd.notna(v)]).strip(): continue

            for col_idx in range(len(curr_row)):
                info = col_mapping[col_idx]
                parent = info["parent"]
                name = info["name"]
                val = curr_row[col_idx]

                if pd.isna(val): continue
                try:
                    amount = int(float(str(val).replace(",", "").replace("원", "").strip()))
                except:
                    continue
                if amount == 0: continue

                if parent == "결제수단별":
                    if name in ["현금", "카드", "QR결제", "계좌이체"]:
                        hall_sales += amount
                elif parent == "매입사별":
                    low_name = name.lower()
                    if any(k in low_name for k in baemin_keys):
                        sales_baemin += amount
                    elif any(k in low_name for k in coupang_keys):
                        sales_coupang += amount
                    elif any(k in low_name for k in yogiyo_keys):
                        sales_yogiyo += amount

        return {
            "hall": hall_sales,
            "baemin": sales_baemin,
            "coupang": sales_coupang,
            "yogiyo": sales_yogiyo
        }