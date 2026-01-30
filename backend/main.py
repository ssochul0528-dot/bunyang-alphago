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
# SQLite 연결 최적화: timeout 설정 추가로 잠김 현상 방지
engine = create_engine(
    sqlite_url, 
    echo=False, 
    connect_args={"check_same_thread": False, "timeout": 30}
)

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
    create_db_and_tables()
    seed_sites()
    # Start the daily update background task
    asyncio.create_task(update_sites_task())

def seed_sites():
    with Session(engine) as session:
        # Check if sites exist
        existing_count = session.exec(select(Site)).all()
        if len(existing_count) > 0:
            print(f"--- Database already has {len(existing_count)} sites. Skipping seed. ---")
            return
        
        print("--- Database is empty. Seeding starting... ---")
        
        for s in MOCK_SITES:
            site = Site(
                id=s["id"],
                name=s["name"],
                address=s["address"],
                brand=s["brand"],
                category=s["category"],
                price=s["price"],
                target_price=s["target_price"],
                supply=s["supply"],
                status=s["status"]
            )
            session.add(site)
        session.commit()

async def update_sites_task():
    """Simulates a daily update from Naver Land / MOLIT APIs"""
    while True:
        # Wait for 24 hours (86400 seconds)
        # For demo purposes, we can make it shorter, but let's stick to the concept
        await asyncio.sleep(86400)
        
        print(f"[{datetime.datetime.now()}] AI Engine: Syncing with Naver Realty & MOLIT Data...")
        with Session(engine) as session:
            sites = session.exec(select(Site)).all()
            for site in sites:
                # Simulate price fluctuation (±0.5% daily trend)
                change = random.uniform(-0.005, 0.005)
                site.target_price = round(site.target_price * (1 + change), 1)
                
                # Simulate status changes for unsold units
                if "미분양" in site.status or "선착순" in site.status:
                    if random.random() < 0.05: # 5% chance of progress
                         site.status = "잔여세대 마감 임박"
                
                site.last_updated = datetime.datetime.now()
                session.add(site)
            session.commit()
        print(f"[{datetime.datetime.now()}] AI Engine: Daily sync complete.")

# Mock Site Database for Validation (Expanded with Unsold/Special Sites)
MOCK_SITES = [
    # --- 아파트 / 오피스텔 (분양 중 & 미분양) ---
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "선착순 계약 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "price": 1100, "target_price": 1300, "supply": 600, "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "category": "오피스텔", "price": 4500, "target_price": 5200, "supply": 300, "status": "잔여세대 분양 중"},
    {"id": "s4", "name": "동탄 레이크파크 자연앤 e편한세상", "address": "경기도 화성시 동탄동", "brand": "e편한세상", "category": "아파트", "price": 1800, "target_price": 2400, "supply": 1200, "status": "분양 완료"},
    {"id": "s5", "name": "용인 푸르지오 원클러스터", "address": "경기도 용인시 처인구", "brand": "푸르지오", "category": "아파트", "price": 1900, "target_price": 2200, "supply": 1500, "status": "청약 진행 중"},
    {"id": "s8", "name": "자이 더 헤리티지", "address": "인천광역시 미추홀구", "brand": "자이", "category": "아파트", "price": 2100, "target_price": 2500, "supply": 900, "status": "잔여세대 분양 중"},
    {"id": "s9", "name": "대구 범어 아이파크 2차", "address": "대구광역시 수성구", "brand": "아이파크", "category": "아파트", "price": 3200, "target_price": 3500, "supply": 450, "status": "미분양 관리 현장"},
    {"id": "s10", "name": "울산 문수로 푸르지오", "address": "울산광역시 남구", "brand": "푸르지오", "category": "아파트", "price": 2200, "target_price": 2100, "supply": 800, "status": "할인 분양 검토 중"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "category": "아파트", "price": 1450, "target_price": 1600, "supply": 851, "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양 잔여세대"},
    {"id": "s13", "name": "포레나 평택화양", "address": "경기도 평택시 안중읍", "brand": "포레나", "category": "아파트", "price": 1380, "target_price": 1500, "supply": 995, "status": "중도금 무이자 진행 중"},
    {"id": "s15", "name": "남양주 다산역 데시앙", "address": "경기도 남양주시 다산동", "brand": "데시앙", "category": "오피스텔", "price": 2800, "target_price": 3200, "supply": 531, "status": "회사보유분 특별분양"},
    {"id": "s16", "name": "파주 운정 힐스테이트 더 운정", "address": "경기도 파주시 와동동", "brand": "힐스테이트", "category": "오피스텔", "price": 3100, "target_price": 3500, "supply": 2669, "status": "선착순 조건변경 중"},
    {"id": "s17", "name": "고양 장항 카이브 유보라", "address": "경기도 고양시 일산동구", "brand": "유보라", "category": "아파트", "price": 2400, "target_price": 2800, "supply": 1694, "status": "청약 마감 후 잔여분"},
    {"id": "s18", "name": "안산 푸르지오 브리파크", "address": "경기도 안산시 단원구", "brand": "푸르지오", "category": "아파트", "price": 1850, "target_price": 2100, "supply": 1714, "status": "준공 후 미분양 분양"},
    {"id": "s19", "name": "수원 영통 푸르지오 트레센츠", "address": "경기도 수원시 영통구", "brand": "푸르지오", "category": "아파트", "price": 2100, "target_price": 2400, "supply": 796, "status": "선착순 계약 (잔여세대)"},
    {"id": "s21", "name": "천안 백석 센트레빌 파크디션", "address": "충청남도 천안시 서북구", "brand": "센트레빌", "category": "아파트", "price": 1400, "target_price": 1550, "supply": 358, "status": "미분양 선착순 분양"},
    {"id": "s22", "name": "청주 가경 아이파크 6차", "address": "충청북도 청주시 흥덕구", "brand": "아이파크", "category": "아파트", "price": 1280, "target_price": 1500, "supply": 946, "status": "분양 완료 (예비번호)"},
    {"id": "s31", "name": "대구 상인 푸르지오 센터파크", "address": "대구광역시 달서구 상인동", "brand": "푸르지오", "category": "아파트", "price": 1650, "target_price": 1800, "supply": 990, "status": "대구 미분양 특별분양"},
    {"id": "s32", "name": "평택 브레인시티 중흥S-클래스", "address": "경기도 평택시 도일동", "brand": "중흥S-클래스", "category": "아파트", "price": 1520, "target_price": 1700, "supply": 1980, "status": "선착순 계약 (동호지정)"},
    {"id": "s33", "name": "포항 학산 한신더휴 엘리트파크", "address": "경상북도 포항시 북구 학산동", "brand": "한신더휴", "category": "아파트", "price": 1350, "target_price": 1450, "supply": 1455, "status": "계약금 5% 정액제"},
    {"id": "s34", "name": "광양 푸르지오 센터파크", "address": "전라남도 광양시 광양읍", "brand": "푸르지오", "category": "아파트", "price": 1150, "target_price": 1250, "supply": 992, "status": "잔여세대 특별분양 중"},
    {"id": "s35", "name": "거제 아주 내진 힐스테이트", "address": "경상남도 거제시 아주동", "brand": "힐스테이트", "category": "아파트", "price": 1200, "target_price": 1350, "supply": 700, "status": "미분양 선착순 분양 중"},

    # --- 민간임대 아파트 (공공지원 / 장기임대) ---
    {"id": "s6", "name": "의왕 고천 민간임대 아파트", "address": "경기도 의왕시 고천동", "brand": "기타", "category": "민간임대", "price": 800, "target_price": 1200, "supply": 500, "status": "입주자 모집 중"},
    {"id": "s7", "name": "제주 월령 민간임대 주택", "address": "제주특별자치도 제주시", "brand": "기타", "category": "민간임대", "price": 600, "target_price": 900, "supply": 200, "status": "선착순 계약 중"},
    {"id": "s23", "name": "양주 옥정 신도시 에코뷰", "address": "경기도 양주시 옥정동", "brand": "기타", "category": "민간임대", "price": 750, "target_price": 1100, "supply": 1200, "status": "임차인 모집 및 분양전환"},
    {"id": "s27", "name": "안성 당왕지구 경남아너스빌", "address": "경기도 안성시 당왕동", "brand": "경남아너스빌", "category": "민간임대", "price": 550, "target_price": 850, "supply": 976, "status": "10년 확정 분양가 임대"},
    {"id": "s30", "name": "구리 갈매 스타힐스", "address": "경기도 구리시 갈매동", "brand": "기타", "category": "민간임대", "price": 1200, "target_price": 1450, "supply": 640, "status": "공가 세대 선착순 모집"},
    {"id": "s36", "name": "오산 세교2지구 칸타빌 더퍼스트", "address": "경기도 오산시 세교동", "brand": "칸타빌", "category": "민간임대", "price": 680, "target_price": 950, "supply": 1030, "status": "사전 임차인 모집 완료"},
    {"id": "s37", "name": "평택 화양지구 서희스타힐스 센트럴", "address": "경기도 평택시 화양지구", "brand": "서희스타힐스", "category": "민간임대", "price": 580, "target_price": 800, "supply": 1554, "status": "10년 후 분양전환형"},
    {"id": "s38", "name": "화성 비봉지구 예미지 2차", "address": "경기도 화성시 비봉면", "brand": "예미지", "category": "민간임대", "price": 620, "target_price": 880, "supply": 900, "status": "선착순 동호지정 임대"},

    # --- 타운하우스 / 단독주택 (수도권 & 제주) ---
    {"id": "s14", "name": "용인 남사 한숲시티 타운하우스", "address": "경기도 용인시 처인구 남사읍", "brand": "기타", "category": "타운하우스", "price": 1200, "target_price": 1500, "supply": 45, "status": "준공 후 분양 중"},
    {"id": "s20", "name": "용인 기흥 고매동 테라하우스", "address": "경기도 용인시 기흥구 고매동", "brand": "기타", "category": "타운하우스", "price": 1550, "target_price": 1800, "supply": 36, "status": "즉시 입주 가능"},
    {"id": "s24", "name": "인천 영종도 제이원 타운하우스", "address": "인천광역시 중구 운남동", "brand": "기타", "category": "타운하우스", "price": 980, "target_price": 1200, "supply": 18, "status": "잔여 3세대 특별공급"},
    {"id": "s26", "name": "보정역 에코메트로 타운하우스", "address": "경기도 용인시 기흥구 보정동", "brand": "기타", "category": "타운하우스", "price": 2200, "target_price": 2800, "supply": 24, "status": "상담 후 계약 진행"},
    {"id": "s29", "name": "제주 서귀포 루스톤 타운하우스", "address": "제주특별자치도 서귀포시 안덕면", "brand": "기타", "category": "타운하우스", "price": 1800, "target_price": 2100, "supply": 12, "status": "단독형 풀빌라 분양"},
    {"id": "s39", "name": "가평 설악면 로얄 타운하우스", "address": "경기도 가평군 설악면", "brand": "기타", "category": "타운하우스", "price": 1400, "target_price": 1650, "supply": 22, "status": "수도권 인접 숲세권"},
    {"id": "s40", "name": "양평 양서면 강변 테라스", "address": "경기도 양평군 양서면", "brand": "기타", "category": "타운하우스", "price": 1550, "target_price": 1900, "supply": 18, "status": "준공 완료 샘플하우스 오픈"},
    {"id": "s41", "name": "파주 야당동 어반 빌리지", "address": "경기도 파주시 야당동", "brand": "기타", "category": "타운하우스", "price": 1100, "target_price": 1400, "supply": 32, "status": "잔여 미분양 5개동 분양"},

    # --- 지식산업센터 / 상업시설 ---
    {"id": "s25", "name": "하남 미사 강변 SK V1 center", "address": "경기도 하남시 망월동", "brand": "SK V1", "category": "지식산업센터", "price": 1100, "target_price": 1400, "supply": 800, "status": "선착순 전매/임대"},
    {"id": "s28", "name": "광명 소하 테크노파크", "address": "경기도 광명시 소하동", "brand": "기타", "category": "지식산업센터", "price": 1400, "target_price": 1700, "supply": 450, "status": "잔여호실 입주지원금"},
    {"id": "s42", "name": "송도 스마트밸리 지식산업센터", "address": "인천광역시 연수구 송도동", "brand": "기타", "category": "지식산업센터", "price": 1250, "target_price": 1450, "supply": 1200, "status": "임대수익 보장제 실시"},
    {"id": "s43", "name": "판교 제2테크노밸리 메타비즈", "address": "경기도 성남시 수정구", "brand": "기타", "category": "지식산업센터", "price": 2800, "target_price": 3500, "supply": 950, "status": "청약 마감 후 부적격분"},
    {"id": "s44", "name": "동탄 테크노밸리 SH타임스퀘어", "address": "경기도 화성시 영천동", "brand": "기타", "category": "지식산업센터", "price": 1600, "target_price": 1950, "supply": 600, "status": "잔여 오피스 특별분양"},
    {"id": "s45", "name": "문정역 현대 지식산업센터", "address": "서울특별시 송파구 문정동", "brand": "현대", "category": "지식산업센터", "price": 3500, "target_price": 4200, "supply": 2100, "status": "분양 완료 (임대 전환)"}
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

class AnalysisRequest(BaseModel):
    # 1. 현장 기본 정보
    field_name: str
    address: str
    product_category: str # 아파트, 오피스텔, 지식산업센터, 상가, 숙박시설, 타운하우스
    sales_stage: str # 사전 의향서, 정당 계약, 선착순, 회사 보유분

    # 2. 분양 조건
    down_payment: str # 5%, 10%, 정액제
    interest_benefit: str # 무이자, 이자 후불제, 이자 지원
    additional_benefits: List[str] # 풀옵션 무상, 경품 이벤트, 전매 제한 해제 등
    
    # 3. 현재 마케팅 상황
    main_concern: str # DB 수량 부족, DB 질 저하, 방문객 없음
    monthly_budget: float # 만원 단위
    existing_media: List[str] # 인스타그램, 블로그, 현수막, 유튜브 등

    # 4. 연산용 데이터
    sales_price: float # 평당 분양가
    target_area_price: float # 주변 신축 평당가
    down_payment_amount: float = 0 # 계약금 금액 (만원 단위)
    supply_volume: int = 0
    field_keypoints: str = "" # New: User provided field highlights
    user_email: Optional[str] = None # Added for History association

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
    media_mix: List[MediaRecommendation] # New: Derived from Google Sheet learning
    copywriting: str
    price_data: List[dict]
    radar_data: List[RadarItem]
    market_gap_percent: float
    
    # New Rich Content
    target_audience: List[str]
    target_persona: str
    competitors: List[CompetitorInfo]
    roi_forecast: ROIForecast
    keyword_strategy: List[str]
    weekly_plan: List[str]
    lms_copy_samples: List[str]
    channel_talk_samples: List[str] # New: Hogangnono ChannelTalk variants

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
    if not q or len(q.strip().lower()) < 1: 
        return []
    
    # 검색어 하나만 들어와도 다 찾을 수 있게 정규화
    q_norm = q.lower().replace(" ", "")
    
    try:
        with Session(engine) as session:
            all_sites = session.exec(select(Site)).all()
            
            results = []
            for s in all_sites:
                # 현장명, 주소, 브랜드, 카테고리 전체 통합 검색
                search_pool = (s.name + s.address + (s.brand or "") + s.category).lower().replace(" ", "")
                
                if q_norm in search_pool:
                    results.append(SiteSearchResponse(
                        id=s.id, name=s.name, address=s.address, brand=s.brand, status=s.status
                    ))
            return results
    except Exception as e:
        print(f"Search Error: {e}")
        return []

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        return site

@app.get("/history")
async def get_history(email: Optional[str] = None):
    with Session(engine) as session:
        statement = select(AnalysisHistory)
        if email:
            statement = statement.where(AnalysisHistory.user_email == email)
        statement = statement.order_by(AnalysisHistory.created_at.desc())
        results = session.exec(statement).all()
        return results

@app.get("/")
def read_root():
    port = os.getenv("PORT", "8000")
    return {"message": "Welcome to Bunyang AlphaGo API", "active_port": port}

@app.post("/submit-lead")
async def submit_lead(lead: LeadForm):
    import httpx
    import datetime
    
    # 🚨 중요: 환경 변수에서 URL을 불러옵니다. 없을 경우를 대비한 기본값(예시)입니다.
    APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL", "https://script.google.com/macros/s/AKfycbyi6DkI9itI08mK8Xf68N_VpE-7WcWn1L9z_u_f6f6f6f6f6f6f6f6f6f/exec")
    
    data = {
        "name": lead.name,
        "phone": lead.phone,
        "rank": lead.rank,
        "site": lead.site,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print(f"Submitting Lead to GS: {data}")
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.post(APPS_SCRIPT_URL, json=data)
            print(f"GS Response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                return {"status": "success", "message": "Lead submitted successfully"}
            else:
                return {"status": "error", "message": f"GS Error: {response.status_code}"}
        except Exception as e:
            print(f"GS Submission Failed: {e}")
            return {"status": "error", "message": str(e)}
    #     req = urllib.request.Request(APPS_SCRIPT_URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    #     urllib.request.urlopen(req)
    # except:
    #     pass

    return {"status": "success", "message": "Lead submitted successfully"}

# --- Reusable Copywriting Engines ---
    
def generate_lms_variants(req: AnalysisRequest, gap_percent: float):
    region = req.address.split(" ")[0] + " " + req.address.split(" ")[1] if len(req.address.split(" ")) > 1 else req.address
    variants = []
    
    # Common shared components with randomization
    fin_hook = f"- 계약금 {req.down_payment} ({req.down_payment_amount/10000 if req.down_payment_amount else 1000}만원)로 입주까지!" if req.down_payment != "정액제" else "- 계약금 1,000만원 정액제 (추가 자금 無)"
    interest_hook = random.choice(["- 중도금 전액 무이자 혜택 적용", "- 중도금 60% 전액 무이자 대출 지원", "✅ 중도금 무이자! 자금 부담 제로 솔루션"])
    resale_hook = random.choice(["- 입주 전 전매 가능 / 실거주의무 없음", "🚩 즉시 전매 가능 (분양권 프리미엄 기대)", "- 전매 제한 해제 현장 (투자성 극대화)"]) if "전매 제한 해제" in req.additional_benefits else ""
    gift_list = random.choice([
        "- 선착순 방문 이벤트: 스타벅스 기프트카드 & 고급 와인 증정",
        "- 계약 축하 이벤트: 황금열쇠(1돈) 또는 가전제품 풀패키지 증정",
        "- [특별이벤트] 다이슨 에어랩 / LG 오브제 청소기 추첨 기회"
    ])

    raw_kp = [k.strip() for k in req.field_keypoints.replace(',', '\n').replace(';', '\n').split('\n') if k.strip()]
    def get_kp_text(count=3, prefix="✨"):
        if not raw_kp: return f"{prefix} 전 세대 남향 위주 배치 및 혁신 평면 설계\n{prefix} 단지 내 스트리트형 상업시설 입점\n{prefix} 초등학교 도보 통학 안심 학세권"
        selected = random.sample(raw_kp, min(count, len(raw_kp)))
        return "\n".join([f"{prefix} {k}" for k in selected])

    # 1. 신뢰/종합형 (Standard & Brand)
    v1_head = f"💎 {req.field_name} | {region} 프리미엄 랜드마크 공식 선착순 분양"
    v1_body = f"안녕하세요, {region}의 주거 가치를 새롭게 증명할 '{req.field_name}' 공식 홍보관입니다.\n\n주변 구축 아파트 시세 대비 약 {int(abs(gap_percent))}% 합리적으로 책정된 분양가로, 입주와 동시에 압도적인 시세 차익이 기대되는 현장입니다. 대단지 브랜드가 선사하는 고품격 라이프스타일을 지금 바로 소유하십시오."
    v1 = f"(광고) {v1_head}\n\n{v1_body}\n\n■ FINANCE PREMIUM\n{fin_hook}\n{interest_hook}\n{resale_hook}\n\n■ LOCATION KEYPOINTS\n{get_kp_text(3)}\n\n■ SPECIAL BENEFITS\n- {gift_list}\n- 모델하우스 방문 전 실시간 호실 확인 필수\n\n▶ 방문 예약 및 상세 정보:\nhttps://bunyang-alpha.go\n☎ 대표번호: 1600-1234"
    variants.append(v1)

    # 2. 혜택집중형 (Financial/ROI Focus)
    v2_head = f"💰 내 집 마련 골든타임! {req.down_payment_amount/10000 if req.down_payment_amount else 1000}만원으로 입주까지 OK"
    v2_body = f"자금 부담 때문에 주저하셨다면 주목하십시오. {req.field_name}가 제안하는 파격적인 금융 솔루션은 금리 인상기에도 흔들림 없는 확실한 기회를 제공합니다.\n\n현재 중도금 전액 무이자와 계약금 정액제가 적용되어 초기 자본 {req.down_payment_amount/10000 if req.down_payment_amount else 1000}만원이면 입주 시점까지 추가 자금 투입이 전혀 없습니다. {region}의 미래 가치를 가장 저렴한 비용으로 선점할 마지막 찬스입니다."
    v2 = f"(광고) {v2_head}\n\n{v2_body}\n\n📢 현장 핵심 포인트\n{get_kp_text(3, '✅')}\n\n📢 MONEY POINT 총괄 안내\n{fin_hook}\n{interest_hook}\n- 발코니 확장 비용 무상 지원 및 유상옵션 품목 제공\n- {region} 핵심 주거지 평당 {int(abs(gap_percent))}% 낮은 파격가\n\n🎁 계약 축하 사은 행사\n{gift_list}\n\n▶ 금융 혜택 상세 확인하기:\nhttps://bunyang-alpha.go/benefit\n☎ 상담본부: 1600-1234"
    variants.append(v2)

    # 3. 마감임박형 (Urgency/FOMO Focus)
    v3_head = f"🚨 [긴급] {req.field_name} 로열층 잔여세대 급소진! 금주 내 마감 예정"
    v3_body = f"기회는 오래 머무르지 않습니다. 파격적인 조건 변경 공지 이후 홍보관 방문객이 최근 3일간 평소 대비 3배 이상 폭증하고 있습니다.\n\n가장 선호도가 높은 로열층과 판상형 타입은 이제 한 자릿수 잔여량만을 남겨두고 있습니다. 망설이면 늦습니다. 지금 바로 전문 상담사와 연결하여 실시간 호실을 확보하십시오."
    v3 = f"(광고) {v3_head}\n\n{v3_body}\n\n⚠️ 계약 현황 리포트\n- 로열동/호수 잔여 세대 선착순 지정 계약 중\n- 당일 방문 고객 로열층 우선 배정 혜택 제공\n{interest_hook}\n{resale_hook}\n\n🎯 현장 주요 특장점\n{get_kp_text(2, '📍')}\n\n🎁 예약 방문객 대상 100% 사은품 증정\n\n▶ 실시간 잔여 호실 현황:\nhttps://bunyang-alpha.go/fast\n☎ 빠른상세상담: 1600-1234"
    variants.append(v3)

    return variants

def generate_channel_talk_variants(req: AnalysisRequest, gap_percent: float):
    region = req.address.split(" ")[0] + " " + req.address.split(" ")[1] if len(req.address.split(" ")) > 1 else req.address
    variants = []
    
    raw_kp = [k.strip() for k in req.field_keypoints.replace(',', '\n').replace(';', '\n').split('\n') if k.strip()]
    def get_kp_short(count=3):
        if not raw_kp: return "✅역세권 프리미엄\n✅학세권 압도적 입지\n✅합리적 분양가"
        selected = random.sample(raw_kp, min(count, len(raw_kp)))
        return "\n".join([f"✅{k}" for k in selected])

    def finalize_ct(text):
        # Detailed decorations to ensure 250~300 characters
        decorations = [
            "\n\n💎 주변 시세 대비 확실한 저평가 구간입니다. 지금 바로 문의하셔서 남들보다 한발 앞서 로열 호실을 선점해보세요. 전문 상담사가 실시간으로 최상의 동호수 선택을 도와드리겠습니다.",
            "\n\n🚀 미래 가치가 검증된 압도적 입지, 실시간 잔여세대 확인이 필수인 시점입니다. 24시간 언제든 상담 가능하니 부담 없이 편하게 하단 번호로 연락주셔서 마지막 기회를 잡으세요.",
            "\n\n🎁 이번 주말 모델하우스 방문 고객님께만 드리는 특별한 추가 사은품과 계약 혜택도 내방 시 즉시 확인하실 수 있습니다. 선착순 마감 전 지금 바로 방문을 예약하세요!"
        ]
        
        # Add decoration until it hits at least 250 chars or cap at 300
        if len(text) < 250:
            text += random.choice(decorations)
        
        return text[:300]

    # 1. 조건/혜택 (Extreme Benefit)
    v1_raw = f"🔥 {req.field_name} 계약조건 파격변경 소식 🔥\n\n💰 {req.down_payment_amount/10000 if req.down_payment_amount else 1000}만원으로 내집 마련의 꿈을 실현하세요! 중도금 전액 무이자 혜택과 발코니 확장 무상 지원까지 제공됩니다.\n\n💎 현장 핵심 가치 요약\n{get_kp_short(3)}\n\n📈 인근 단지 대비 {int(abs(gap_percent))}% 낮은 분양가로 시세 차익을 즉시 확보하세요!"
    variants.append(finalize_ct(v1_raw))

    # 2. 긴급/속보 (Real-time Urgency)
    v2_raw = f"🚨 {req.field_name} 로열층 선착순 지정계약 개시 🚨\n\n지금 이 순간에도 로열층 잔여 세대가 급격히 소진되고 있습니다! 조건변경 소식 이후 홍보관 방문 예약이 평소의 3배 이상 폭주하고 있어 빠른 확인이 필요합니다.\n\n❗ 남은 평형 및 타입 실시간 확인 필수\n❗ {req.sales_stage} 특별 한정 혜택 일괄 적용\n{get_kp_short(3)}"
    variants.append(finalize_ct(v2_raw))

    # 3. 프리미엄/가치 (Value/Brand)
    v3_raw = f"💎 {region}의 중심, 하이엔드 랜드마크 【{req.field_name}】 💎\n\n미래 가치가 이미 검증된 압도적 입지와 고품격 설계의 완성! 당신의 라이프스타일을 한 단계 높여줄 최고의 선택입니다.\n\n{get_kp_short(3)}\n🏙️ 풍부한 생활 인프라와 안심 교육환경\n📈 데이터로 증명된 시세 우위 {int(abs(gap_percent))}%의 확신"
    variants.append(finalize_ct(v3_raw))

    return variants

    return variants

    return variants

@app.post("/regenerate-copy", response_model=RegenerateCopyResponse)
async def regenerate_copy(req: AnalysisRequest):
    gap = (req.target_area_price - req.sales_price) / req.target_area_price
    gap_pct = round(gap * 100, 1)
    return RegenerateCopyResponse(
        lms_copy_samples=generate_lms_variants(req, gap_pct),
        channel_talk_samples=generate_channel_talk_variants(req, gap_pct)
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_field(request: AnalysisRequest):
    # 1. Price Attractiveness (40 points)
    gap = (request.target_area_price - request.sales_price) / request.target_area_price
    gap_percent = round(gap * 100, 1)
    
    if gap_percent >= 15: price_score = 40
    elif gap_percent >= 5: price_score = 30 + (gap_percent - 5)
    else: price_score = max(0, 20 + (gap_percent * 2))

    # 2. Location & Supply (30 points)
    if request.supply_volume < 300: location_score = 30
    elif request.supply_volume < 1000: location_score = 20
    else: location_score = 10

    # 3. Benefits & Conditions (30 points)
    benefit_score = 15 # Base
    if request.interest_benefit == "무이자": benefit_score += 10
    if request.down_payment == "5%": benefit_score += 5
    if "전매 제한 해제" in request.additional_benefits: benefit_score += 5
    benefit_score = min(30, benefit_score)

    total_score = round(price_score + location_score + benefit_score, 1)

    # --- Advanced Market Diagnosis (Simulating Search Engine Analysis) ---
    region = request.address.split(" ")[0] + " " + request.address.split(" ")[1] if len(request.address.split(" ")) > 1 else request.address
    
    # Simulate search metrics based on score and supply
    est_search_vol = int(request.supply_volume * 12.5 + random.randint(1000, 5000))
    est_blog_count = int(request.supply_volume * 0.4 + random.randint(50, 200))
    competitor_count = random.randint(3, 8)
    
    diagnosis_intro = f"🔍 [Google/Naver 빅데이터 기반 현장 진단]\n\n"
    
    diagnosis_1 = f"1. 검색 트렌드 및 관심도 분석\n"
    diagnosis_1 += f" - '{request.field_name}' 및 '{region}' 관련 월간 검색량: 약 {est_search_vol:,}건\n"
    diagnosis_1 += f" - 최근 30일간 관심도 추이: {'상승세 📈' if total_score > 70 else '보합세 ➖'}\n"
    diagnosis_1 += f" - 주요 유입 키워드: '{request.interest_benefit}', '{request.product_category}', '미분양'\n\n"
    
    diagnosis_2 = f"2. 온라인 경쟁 환경 (Share of Voice)\n"
    diagnosis_2 += f" - '{region}' 내 경쟁 단지 수: {competitor_count}개\n"
    diagnosis_2 += f" - 경쟁사 블로그/카페 콘텐츠 발행량: 약 {est_blog_count:,}건\n"
    if total_score >= 80:
        diagnosis_2 += f" - 진단: 경쟁 단지 대비 압도적인 가격 경쟁력과 '{request.down_payment}' 조건으로 상위 노출 시 클릭률(CTR)이 매우 높을 것으로 예상됩니다.\n\n"
    else:
        diagnosis_2 += f" - 진단: 온라인 경쟁 강도가 '매우 높음' 수준입니다. 단순 홍보보다는 '{request.additional_benefits[0] if request.additional_benefits else '특별 혜택'}' 소구점을 활용한 차별화 콘텐츠가 필수적입니다.\n\n"
        
    diagnosis_3 = f"3. AI 최적화 솔루션\n"
    if request.main_concern == "DB 수량 부족":
        diagnosis_3 += f" - 전략: 잠재 고객의 파이(Pie)를 키워야 합니다. 타겟 고객이 밀집한 맘카페, 부동산 커뮤니티 침투 마케팅과 메타(페이스북/인스타그램) 광고 예산 비중을 6:4로 설정하여 도달률을 극대화하십시오."
    elif request.main_concern == "DB 질 저하":
        diagnosis_3 += f" - 전략: 허수 DB를 걸러내는 '필터링 퍼널'이 필요합니다. 구글/유튜브 리타겟팅 광고를 통해 관심도가 높은 고객을 재유입시키고, 호갱노노와 같은 고관여 플랫폼 비중을 높여 진성 DB를 확보하십시오."
    else:
        diagnosis_3 += f" - 전략: '우리 동네 아파트'라는 인식이 부족합니다. 당근마켓 지역 광고와 카카오 비즈보드를 활용하여 '{region}' 생활권 거주자에게 반복 노출하는 '지역 밀착형 세뇌 마케팅'을 제안합니다."

    diagnosis = diagnosis_intro + diagnosis_1 + diagnosis_2 + diagnosis_3

    # --- Media Stats derived from Google Sheet (Basis: Budget 100만원) ---
    MEDIA_STATS = {
        "메타 릴스": {
            "leads_per_100": 24,
            "feature": "인스타그램/페이스북 릴스 노출",
            "reason": "폭발적인 문의(Call) 유도 및 참여",
            "strategy": "{product_category}의 세련된 인테리어와 {benefit} 조건을 강조한 숏폼 영상으로 도파민을 자극하는 광고 집행 추천"
        },
        "당근마켓": {
            "leads_per_100": 9,
            "feature": "생활권 밀착 타겟팅(0~3km), 높은 신뢰도",
            "reason": "홍보관 인근 거주 실수요자 공략",
            "strategy": "'{address} 주민분들만 아는 입지 비밀!'과 같은 로컬 키워드로 친근함을 소구하고, 홍보관 방문 사은품 이벤트를 지역 피드에 노출하세요."
        },
        "분양의신": {
            "leads_per_100": 7,
            "feature": "구글 GDN을 통한 적극적인 gdn광고",
            "reason": "미분양현장 특화",
            "strategy": "{address} 인근의 타 단지 대비 우위점과 {benefit} 혜택을 비교 분석하는 카드뉴스 형태로 유저들의 관심을 유도하면 좋습니다."
        },
        "호갱노노": {
            "leads_per_100": 6,
            "feature": "아파트 실거래 정보 기반, 고관여 실수요자",
            "reason": "전환율 높은 실입주 희망 DB 확보",
            "strategy": "실시간 거래량이 많은 단지 리스트에 '{fieldName}'을 노출하고, '{benefit}' 금융 혜택을 썸네일에 노출하여 고관여자를 유입시키세요."
        },
        "LMS 문자 광고": {
            "leads_per_100": 5,
            "feature": "90% 이상의 높은 도달률, DB 직접 접촉",
            "reason": "이벤트/청약 일정 등 급박한 정보 전달",
            "strategy": "{fieldName}만의 단독 조건변경 안내를 LMS로 발송하고, {benefit} 혜택과 '마감임박' 문구를 섞어 즉각적인 전화 문의를 유도하세요."
        },
        "카카오": {
            "leads_per_100": 4,
            "feature": "카톡 알림톡/오픈채팅 등 모바일 접점 강력",
            "reason": "즉각적인 모바일 상담 유도",
            "strategy": "관심 고객 대상 오픈채팅 프로모션을 운영하고, {fieldName}의 내부 평면도와 모델하우스 직캠 영상을 공유하며 비대면 신뢰를 쌓고 방문을 예약시키세요."
        },
        "구글 (GDN/유튜브)": {
            "leads_per_100": 4,
            "feature": "최대 노출망, 정교한 타겟 세분화",
            "reason": "신규/대형 현장 인지도 확산",
            "strategy": "부동산 관심층 및 {region} 거주자 대상 배너 광고를 무차별 노출하여 {fieldName}의 브랜드 인지도를 획기적으로 올리는 전략이 필요합니다."
        },
        "네이버": {
            "leads_per_100": 2,
            "feature": "검색 기반, 블로그 콘텐츠 연계 시너지",
            "reason": "실수요자 타겟, 지역 키워드 중심",
            "strategy": "'{address} 미분양/분양가' 키워드 검색 시 파워링크 상단 노출과 함께, {benefit} 내용을 담은 블로그 리뷰 20건 이상으로 신뢰도를 구축하세요."
        },
        "리치고": {
            "leads_per_100": 2,
            "feature": "피로도가 높지 않은 앱충성고객",
            "reason": "전환율 높은 실입주 희망 DB 확보",
            "strategy": "전통적인 광고보다는 중립적인 데이터 분석 리포트 형식으로 {fieldName}의 저평가 요인과 {benefit}의 실질적 이득을 소구하는 것이 효과적입니다."
        }
    }

    # Use the provided budget (minimum 100만원 safety check removed here as it should be handled by frontend)
    baseline_budget = max(100.0, request.monthly_budget)

    # --- Allocating Strategies based on Concern ---
    # Baseline: LMS is mandatory for all projects (15% allocation)
    lms_base_weight = 0.15
    
    if request.main_concern == "DB 수량 부족":
        allocations = {"메타 릴스": 0.55, "분양의신": 0.15, "당근마켓": 0.15, "LMS 문자 광고": lms_base_weight}
    elif request.main_concern == "DB 질 저하":
        allocations = {"호갱노노": 0.35, "네이버": 0.25, "구글 (GDN/유튜브)": 0.25, "LMS 문자 광고": lms_base_weight}
    elif request.main_concern == "방문객 없음":
        # Boost LMS even more for foot traffic
        allocations = {"당근마켓": 0.35, "카카오": 0.25, "LMS 문자 광고": 0.40}
    else:
        # Default / Balanced
        allocations = {"메타 릴스": 0.35, "네이버": 0.25, "구글 (GDN/유튜브)": 0.25, "LMS 문자 광고": lms_base_weight}

    # Normalize weights to ensure they sum to exactly 1.0
    total_w = sum(allocations.values())
    for k in allocations:
        allocations[k] = round(allocations[k] / total_w, 2)

    # Calculate Expected Leads based on weighted efficiency
    total_leads = 0
    media_mix = []
    
    for media_name, weight in allocations.items():
        if media_name in MEDIA_STATS:
            stat = MEDIA_STATS[media_name]
            # leads = stat['leads_per_100'] * (baseline_budget / 100) * weight
            leads = stat["leads_per_100"] * (baseline_budget / 100) * weight
            total_leads += leads
            
            # Add to recommendation list
            media_mix.append(MediaRecommendation(
                media=media_name,
                feature=stat["feature"],
                reason=stat["reason"],
                strategy_example=stat["strategy"].format(
                    fieldName=request.field_name,
                    address=region,
                    product_category=request.product_category,
                    benefit=f"{request.interest_benefit} / {request.down_payment}",
                    region=region.split(' ')[0]
                )
            ))

    expected_leads = int(total_leads)

    # Calculate implied Avg CPL
    avg_cpl = 0
    if expected_leads > 0:
        avg_cpl = int((baseline_budget * 10000) / expected_leads)

    # Add other contextual recommendations if needed (e.g., from supply volume)
    # Just appending one more specific high-volume channel if the project is huge
    if request.supply_volume >= 800 and "구글 (GDN/유튜브)" not in allocations:
         stat = MEDIA_STATS["구글 (GDN/유튜브)"]
         media_mix.append(MediaRecommendation(
             media="구글 (GDN/유튜브)", 
             feature=stat["feature"], 
             reason=stat["reason"],
             strategy_example=stat["strategy"].format(
                fieldName=request.field_name,
                address=region,
                product_category=request.product_category,
                benefit=f"{request.interest_benefit} / {request.down_payment}",
                region=region.split(' ')[0]
             )
         ))

    roi = ROIForecast(
        expected_leads=expected_leads,
        expected_cpl=avg_cpl,
        conversion_rate=4.2 if total_score > 80 else 3.5
    )

    # Keywords
    keywords = [f"{request.field_name} 분양가", f"{request.address} 신축", f"{request.interest_benefit} 현장"]
    if "전매 제한 해제" in request.additional_benefits: keywords.append("수도권 전매 가능 단지")

    # Weekly Plan
    weekly_plan = [
        "1주차: 메타/인스타 타겟팅 티징 광고 (관심고객 DB 30% 확보)",
        "2주차: 유튜브 인플루언서 리뷰 및 리서치 블로그 20개 일괄 노출",
        "3주차: 선별 DB 대상 모델하우스 프라이빗 투어 및 혜택 집중 소구",
        "4주차: 잔여 세대 클로징 타겟 리마케팅 및 SMS 자동화 발송"
    ]

    lms_variants = generate_lms_variants(request, gap_percent)
    channel_talk_variants = generate_channel_talk_variants(request, gap_percent)



    # --- Restore Missing Data for Response ---
    target_audience = ["3040 신혼부부", "지역내 갈아타기 수요", "소액 투자자"]
    persona = f"{region} 거주, 자녀 교육과 {request.product_category} 투자를 동시에 고려하는 30대 후반 가장"
    
    # Generate mock competitors based on location and price
    competitors = []
    comp_names = ["자이", "푸르지오", "이편한세상", "더샵", "롯데캐슬"]
    for i in range(3):
        comp_price = request.target_area_price * (1 + random.uniform(-0.1, 0.1))
        gap = (comp_price - request.sales_price) / comp_price * 100
        gap_label = "가격 우위" if gap > 0 else "가격 열위"
        competitors.append(CompetitorInfo(
            name=f"{region} {comp_names[i]}",
            price=int(comp_price),
            gap_label=gap_label
        ))

    # --- Generate Radar Data (Hexagon Balance) ---
    # Subject: Price, Brand, Scale, Location, Benefits, Product
    brand_power = 90 if any(b in request.field_name for b in ["힐스테이트", "자이", "푸르지오", "e편한세상", "레미안", "더샵"]) else 65
    scale_score = min(100, (request.supply_volume / 1500) * 100)
    
    radar_data = [
        RadarItem(subject="분양가", A=price_score * 2.5, B=70, fullMark=100),
        RadarItem(subject="브랜드", A=brand_power, B=75, fullMark=100),
        RadarItem(subject="단지규모", A=scale_score, B=60, fullMark=100),
        RadarItem(subject="입지", A=location_score * 3.3, B=65, fullMark=100),
        RadarItem(subject="분양조건", A=benefit_score * 3.3, B=50, fullMark=100),
        RadarItem(subject="상품성", A=85 if total_score > 75 else 70, B=70, fullMark=100)
    ]

    return AnalysisResponse(
        score=total_score,
        score_breakdown=ScoreBreakdown(
            price_score=price_score,
            location_score=location_score,
            benefit_score=benefit_score,
            total_score=total_score
        ),
        market_diagnosis=diagnosis,
        ad_recommendation=f"월 {int(baseline_budget):,}만 원 예산 기준, '{request.main_concern}' 해결을 위한 최적 믹스 제안",
        media_mix=media_mix,
        copywriting=f"{request.field_name} - {request.interest_benefit} & 계약금 {request.down_payment}!",
        price_data=[
            {"name": "우리 현장", "price": request.sales_price},
            {"name": "지역 신축", "price": request.target_area_price},
            {"name": "지역 대장주", "price": request.target_area_price * 1.15},
        ],
        radar_data=radar_data,
        market_gap_percent=gap_percent,
        target_audience=target_audience,
        target_persona=persona,
        competitors=competitors,
        roi_forecast=roi,
        keyword_strategy=keywords,
        weekly_plan=weekly_plan,
        lms_copy_samples=lms_variants,
        channel_talk_samples=channel_talk_variants
    )

    # --- Save to History ---
    try:
        with Session(engine) as session:
            history_item = AnalysisHistory(
                user_email=request.user_email,
                field_name=request.field_name,
                address=request.address,
                score=total_score,
                response_json=json.dumps(response.dict(), ensure_ascii=False)
            )
            session.add(history_item)
            session.commit()
    except Exception as e:
        print(f"Failed to save history: {e}")

    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
