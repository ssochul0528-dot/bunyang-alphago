from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import datetime
import json
import os
import asyncio
from sqlmodel import Field, Session, SQLModel, create_engine, select

app = FastAPI(title="Bunyang AlphaGo API")

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

class AnalysisHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: Optional[str] = Field(default=None, index=True)
    field_name: str
    address: str
    score: float
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    response_json: str

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

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(run_startup_tasks())

async def run_startup_tasks():
    await asyncio.sleep(1)
    create_db_and_tables()
    seed_sites()
    asyncio.create_task(update_sites_task())

def seed_sites():
    with Session(engine) as session:
        if session.exec(select(Site)).first():
            return
        for s in MOCK_SITES:
            site = Site(**s)
            session.add(site)
        session.commit()

async def update_sites_task():
    while True:
        await asyncio.sleep(86400)
        with Session(engine) as session:
            sites = session.exec(select(Site)).all()
            for site in sites:
                change = random.uniform(-0.005, 0.005)
                site.target_price = round(site.target_price * (1 + change), 1)
                site.last_updated = datetime.datetime.now()
                session.add(site)
            session.commit()

MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "선착순 계약 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "price": 1100, "target_price": 1300, "supply": 600, "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "category": "오피스텔", "price": 4500, "target_price": 5200, "supply": 300, "status": "잔여세대 분양 중"},
    {"id": "s4", "name": "동탄 레이크파크 자연앤 e편한세상", "address": "경기도 화성시 동탄동", "brand": "e편한세상", "category": "아파트", "price": 1800, "target_price": 2400, "supply": 1200, "status": "분양 완료"},
    {"id": "s5", "name": "용인 푸르지오 원클러스터", "address": "경기도 용인시 처인구", "brand": "푸르지오", "category": "아파트", "price": 1900, "target_price": 2200, "supply": 1500, "status": "청약 진행 중"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "category": "아파트", "price": 1450, "target_price": 1600, "supply": 851, "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양 잔여세대"}
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

class AnalysisRequest(BaseModel):
    field_name: str
    address: str
    product_category: str
    sales_stage: str
    down_payment: str
    interest_benefit: str
    additional_benefits: List[str]
    main_concern: str
    monthly_budget: float
    existing_media: List[str]
    sales_price: float
    target_area_price: float
    down_payment_amount: float = 0
    supply_volume: int = 0
    field_keypoints: str = ""
    user_email: Optional[str] = None

class ScoreBreakdown(BaseModel):
    price_score: float
    location_score: float
    benefit_score: float
    total_score: float

class CompetitorInfo(BaseModel):
    name: str
    price: float
    gap_label: str

class MediaRecommendation(BaseModel):
    media: str
    feature: str
    reason: str
    strategy_example: str

class ROIForecast(BaseModel):
    expected_leads: int
    expected_cpl: int
    conversion_rate: float

class RadarItem(BaseModel):
    subject: str
    A: float
    B: float
    fullMark: float

class AnalysisResponse(BaseModel):
    score: float
    score_breakdown: ScoreBreakdown
    market_diagnosis: str
    ad_recommendation: str
    media_mix: List[MediaRecommendation]
    copywriting: str
    price_data: List[dict]
    radar_data: List[RadarItem]
    market_gap_percent: float
    target_audience: List[str]
    target_persona: str
    competitors: List[CompetitorInfo]
    roi_forecast: ROIForecast
    keyword_strategy: List[str]
    weekly_plan: List[str]
    lms_copy_samples: List[str]
    channel_talk_samples: List[str]

def generate_lms_variants(req: AnalysisRequest, gap_percent: float):
    v1 = f"(광고) 💎 {req.field_name}\n\n시세 대비 {int(abs(gap_percent))}% 합리적 분양가! 계약금 {req.down_payment}로 내 집 마련 기회.\n\n▶ 대표: 1600-1234"
    return [v1, v1, v1]

def generate_channel_talk_variants(req: AnalysisRequest, gap_percent: float):
    return [f"🔥 {req.field_name} 계약조건 변경", f"🚨 {req.field_name} 로열층 마감임박", f"💎 {req.field_name} 특별분양"]

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    with Session(engine) as session:
        all_sites = session.exec(select(Site)).all()
        return [SiteSearchResponse(**s.dict()) for s in all_sites if q_norm in (s.name + s.address).lower().replace(" ", "")]

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if not site: raise HTTPException(status_code=404)
        return site

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_field(request: AnalysisRequest):
    gap = (request.target_area_price - request.sales_price) / (request.target_area_price or 1)
    gap_percent = round(gap * 100, 1)
    return AnalysisResponse(
        score=88, score_breakdown=ScoreBreakdown(price_score=45, location_score=20, benefit_score=23, total_score=88),
        market_diagnosis="경쟁력 있는 분양가입니다.", ad_recommendation="SNS 광고 60% 비중 추천",
        media_mix=[MediaRecommendation(media="인스타그램", feature="릴스", reason="3040 타겟팅", strategy_example="현장 스케치")],
        copywriting="최고의 입지!", price_data=[{"name":"우리", "price":request.sales_price}], radar_data=[], market_gap_percent=gap_percent,
        target_audience=["3040"], target_persona="실거주자", competitors=[], roi_forecast=ROIForecast(expected_leads=100, expected_cpl=30000, conversion_rate=5),
        keyword_strategy=[], weekly_plan=[], 
        lms_copy_samples=generate_lms_variants(request, gap_percent),
        channel_talk_samples=generate_channel_talk_variants(request, gap_percent)
    )

@app.get("/")
def home():
    return {"status": "online", "message": "Bunyang AlphaGo Active"}

if __name__ == "__main__":
    import uvicorn
    # 🚨 Railway 환경에 맞게 포트 설정을 가장 유연하게 처리
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
