from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import datetime
import os
import uvicorn
import asyncio
from sqlmodel import Field, Session, SQLModel, create_engine, select

app = FastAPI(title="Bunyang AlphaGo API Full")

# CORS 설정 (Vercel 연동을 위해 모든 통로 개방)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database & Models ---
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

class Site(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    address: str
    brand: Optional[str] = None
    category: str
    price: float
    target_price: float
    supply: int
    status: Optional[str] = None
    last_updated: datetime.datetime = Field(default_factory=datetime.datetime.now)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if not session.exec(select(Site)).first():
            for s in MOCK_SITES:
                session.add(Site(**s))
            session.commit()

@app.on_event("startup")
async def on_startup():
    # 서버 기동 직후 백그라운드에서 DB 초기화 (503 방지)
    asyncio.create_task(init_data())

async def init_data():
    await asyncio.sleep(0.5)
    create_db_and_tables()

# --- Mock Data ---
MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "선착순 계약 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양 잔여세대"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "price": 1100, "target_price": 1300, "supply": 600, "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "category": "오피스텔", "price": 4500, "target_price": 5200, "supply": 300, "status": "잔여세대 분양 중"}
]

# --- Schema Definition ---
class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

class AnalysisRequest(BaseModel):
    field_name: str
    address: str
    sales_price: float
    target_area_price: float
    # 기타 필드는 분석 로직에서 유연하게 처리

@app.get("/")
def home():
    return {"status": "online", "message": "All Systems Go", "port": 8080}

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str = ""):
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    with Session(engine) as session:
        all_sites = session.exec(select(Site)).all()
        results = [SiteSearchResponse(**s.dict()) for s in all_sites 
                   if q_norm in (s.name + s.address).lower().replace(" ", "")]
        
        # 연결 확인을 위한 디버그 데이터
        if not results:
            results = [SiteSearchResponse(id="debug", name=f"연결 성공: {q}", address="데이터를 불러오고 있습니다", status="OK")]
        return results

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if not site: raise HTTPException(status_code=404)
        return site

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    gap = (request.target_area_price - request.sales_price) / (request.target_area_price or 1)
    gap_percent = round(gap * 100, 1)
    
    return {
        "score": 88,
        "score_breakdown": {"price_score": 45, "location_score": 20, "benefit_score": 23, "total_score": 88},
        "market_diagnosis": "주변 시세 대비 매우 강력한 경쟁력을 갖추고 있습니다.",
        "media_mix": [{"media": "메타(인스타그램)", "feature": "릴스 영상 광고", "reason": "3040 실거주자 타겟팅", "strategy_example": "현장 방문 브이로그"}],
        "copywriting": f"계약금만으로 입주까지! 시세 대비 {abs(gap_percent)}% 더 저렴한 완벽한 기회",
        "market_gap_percent": gap_percent,
        "roi_forecast": {"expected_leads": 120, "expected_cpl": 35000, "conversion_rate": 4.5},
        "lms_copy_samples": [f"[광고] {request.field_name} 특별분양\n지금 바로 확인하세요!", "잔여세대 마감임박!"],
        "channel_talk_samples": ["🔥 조건변경 확정!", "💎 로열층 선점 기회"]
    }

if __name__ == "__main__":
    # Railway 포트 8080과 코드 일치화
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
