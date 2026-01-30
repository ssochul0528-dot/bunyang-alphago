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

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

class AnalysisHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: Optional[str] = Field(default=None, index=True)
    field_name: str
    address: str
    score: float
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    response_json: str # Complete result as JSON

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

@app.on_event("startup")
async def on_startup():
    # Railway 503 에러 방지를 위한 즉시 부팅 구조
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
    {"id": "s8", "name": "자이 더 헤리티지", "address": "인천광역시 미추홀구", "brand": "자이", "category": "아파트", "price": 2100, "target_price": 2500, "supply": 900, "status": "잔여세대 분양 중"},
    {"id": "s9", "name": "대구 범어 아이파크 2차", "address": "대구광역시 수성구", "brand": "아이파크", "category": "아파트", "price": 3200, "target_price": 3500, "supply": 450, "status": "미분양 관리 현장"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "category": "아파트", "price": 1450, "target_price": 1600, "supply": 851, "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양 잔여세대"},
    {"id": "s25", "name": "하남 미사 강변 SK V1 center", "address": "경기도 하남시 망월동", "brand": "SK V1", "category": "지식산업센터", "price": 1100, "target_price": 1400, "supply": 800, "status": "선착순 전매/임대"},
    {"id": "s31", "name": "대구 상인 푸르지오 센터파크", "address": "대구광역시 달서구 상인동", "brand": "푸르지오", "category": "아파트", "price": 1650, "target_price": 1800, "supply": 990, "status": "대구 미분양 특별분양"},
    {"id": "s41", "name": "파주 야당동 어반 빌리지", "address": "경기도 파주시 야당동", "brand": "기타", "category": "타운하우스", "price": 1100, "target_price": 1400, "supply": 32, "status": "잔여 미분양 5개동 분양"},
    {"id": "s45", "name": "문정역 현대 지식산업센터", "address": "서울특별시 송파구 문정동", "brand": "현대", "category": "지식산업센터", "price": 3500, "target_price": 4200, "supply": 2100, "status": "분양 완료 (임대 전환)"}
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

class RegenerateCopyResponse(BaseModel):
    lms_copy_samples: List[str]
    channel_talk_samples: List[str]

class LeadForm(BaseModel):
    name: str
    phone: str
    rank: str
    site: str

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    with Session(engine) as session:
        all_sites = session.exec(select(Site)).all()
        results = [SiteSearchResponse(id=s.id, name=s.name, address=s.address, brand=s.brand, status=s.status) 
                   for s in all_sites if q_norm in (s.name + s.address + (s.brand or "")).lower().replace(" ", "")]
        return results

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if not site: raise HTTPException(status_code=404)
        return site

@app.get("/history")
async def get_history(email: Optional[str] = None):
    with Session(engine) as session:
        statement = select(AnalysisHistory)
        if email: statement = statement.where(AnalysisHistory.user_email == email)
        results = session.exec(statement.order_by(AnalysisHistory.created_at.desc())).all()
        return results

@app.get("/")
def read_root():
    return {"status": "online", "message": "Bunyang AlphaGo API Active"}

@app.post("/submit-lead")
async def submit_lead(lead: LeadForm):
    return {"status": "success", "message": "Lead submitted successfully"}

def generate_lms_variants(req: AnalysisRequest, gap_percent: float):
    region = req.address.split(" ")[0] + " " + req.address.split(" ")[1] if len(req.address.split(" ")) > 1 else req.address
    v1 = f"(광고) 💎 {req.field_name} | {region} 프리미엄 선착순 분양\n\n- 주변 시세 대비 {int(abs(gap_percent))}% 합리적 분양가\n- 계약금 {req.down_payment}로 입주까지\n\n▶ 상담: 1600-1234"
    v2 = f"(광고) 💰 {req.field_name} 파격 조건 변경!\n\n현재 로열층 잔여세대 선착순 마감 임박. 계약금 정액제 실시.\n\n▶ 예약: 1600-1234"
    return [v1, v2, v1, v2, v1]

def generate_channel_talk_variants(req: AnalysisRequest, gap_percent: float):
    v1 = f"🔥 {req.field_name} 조건 파격변경 🔥\n\n💰 {int(abs(gap_percent))}% 낮은 분양가로 시세차익 확보 완료!"
    v2 = f"🚨 {req.field_name} 로열층 선착순 마감임박 🚨\n\n지금 바로 문의하셔서 잔여 세대를 선점하세요."
    return [v1, v2, v1, v2, v1]

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_field(request: AnalysisRequest):
    gap = (request.target_area_price - request.sales_price) / (request.target_area_price or 1)
    gap_percent = round(gap * 100, 1)
    
    response = AnalysisResponse(
        score=85,
        score_breakdown=ScoreBreakdown(price_score=40, location_score=25, benefit_score=20, total_score=85),
        market_diagnosis=f"{request.address} 주변 시세 대비 매우 경쟁력 있는 분석 결과입니다.",
        ad_recommendation="인스타그램/릴스 광고 비중을 60% 이상 추천합니다.",
        media_mix=[MediaRecommendation(media="메타 릴스", feature="숏폼 영상 광고", reason="초집중 타겟팅 가능", strategy_example="릴스 홍보")],
        copywriting=f"{request.field_name} - {request.interest_benefit} 혜택 놓치지 마세요!",
        price_data=[{"name":"우리", "price":request.sales_price}, {"name":"비교군", "price":request.target_area_price}],
        radar_data=[RadarItem(subject="가격", A=90, B=70, fullMark=100), RadarItem(subject="입지", A=80, B=65, fullMark=100)],
        market_gap_percent=gap_percent,
        target_audience=["신혼부부", "투자자"], target_persona="3040 세대",
        competitors=[CompetitorInfo(name="인근 단지 A", price=request.target_area_price * 1.05, gap_label="비쌈")],
        roi_forecast=ROIForecast(expected_leads=150, expected_cpl=35000, conversion_rate=4.5),
        keyword_strategy=["분양", "신축"], weekly_plan=["1주차 마케팅 세팅"],
        lms_copy_samples=generate_lms_variants(request, gap_percent),
        channel_talk_samples=generate_channel_talk_variants(request, gap_percent)
    )
    return response

@app.post("/regenerate-copy", response_model=RegenerateCopyResponse)
async def regenerate_copy(req: AnalysisRequest):
    gap = (req.target_area_price - req.sales_price) / (req.target_area_price or 1)
    return RegenerateCopyResponse(
        lms_copy_samples=generate_lms_variants(req, gap * 100),
        channel_talk_samples=generate_channel_talk_variants(req, gap * 100)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
