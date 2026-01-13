# app/schemas/sales_schema.py
from pydantic import BaseModel
from datetime import date
from typing import List, Dict

class SalesReportResponse(BaseModel):
    report_id: int
    report_date: date
    hall: int
    baemin: int
    coupang: int
    yogiyo: int
    total_sales: int

    class Config:
        from_attributes = True

# [A5 추가] 월별 조회용
class MonthlySalesSummary(BaseModel):
    date: str       # "2025-01-01"
    total_sales: int
    platform_sales: Dict[str, int] # {"baemin": 1000, ...}

class MonthlySalesResponse(BaseModel):
    month: str      # "2025-01"
    total_accumulated: int
    daily_logs: List[MonthlySalesSummary]