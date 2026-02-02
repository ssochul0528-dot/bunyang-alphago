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

app = FastAPI(title="Bunyang AlphaGo API Official")

# --- CORS 설정: Vercel과 완벽 연동 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Setup ---
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
    # 백그라운드에서 안전하게 데이터 초기화 (503 방어)
    asyncio.create_task(init_db())

async def init_db():
    await asyncio.sleep(1)
    create_db_and_tables()

# --- Mock Data ---
MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "선착순 계약 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양 잔여세대"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "price": 1100, "target_price": 1300, "supply": 600, "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "category": "오피스텔", "price": 4500, "target_price": 5200, "supply": 300, "status": "잔여세대 분양 중"}
]

# --- API Models ---
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

@app.get("/")
def home():
    return {"status": "online", "sync": "final_v1"}

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str = ""):
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    with Session(engine) as session:
        all_sites = session.exec(select(Site)).all()
        results = [SiteSearchResponse(**s.dict()) for s in all_sites 
                   if q_norm in (s.name + s.address).lower().replace(" ", "")]
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
        "market_diagnosis": f"주변 시세 대비 {abs(gap_percent)}% 가격 경쟁력을 확보하고 있습니다.",
        "media_mix": [
            {"media": "유튜브 쇼츠", "feature": "30초 현장 브리핑", "strategy_example": "입지/가격 강점 압축 전달"},
            {"media": "네이버 카페", "feature": "지역 맘카페 바이럴", "strategy_example": "실거주 장점 중심 소통"}
        ],
        "copywriting": f"의정부의 새로운 중심! 시세보다 {abs(gap_percent)}% 가벼운 내집마련의 꿈",
        "market_gap_percent": gap_percent,
        "roi_forecast": {"expected_leads": 150, "expected_cpl": 40000, "conversion_rate": 5.2},
        "lms_copy_samples": [f"[광고] {request.field_name} 긴급 조건변경\n상담 문의 폭주!", "선착순 로열층 마감임박!"],
        "channel_talk_samples": ["🏠 현장 분위기 생생 리포트", "🎯 지금 바로 전화예약 하세요"]
    }

if __name__ == "__main__":
    # Railway 8080 포트 고정 실행
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
