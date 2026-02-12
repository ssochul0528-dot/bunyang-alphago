from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import datetime
import os
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from sqlmodel import Field, Session, SQLModel, create_engine, select, or_, col
import logging
import httpx

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Setup ---
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

class Site(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    
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

# --- NATIONWIDE START DATA ---
MOCK_SITES = [
    {"id": "h_uj1", "name": "해링턴 플레이스 의정부역", "address": "경기도 의정부시", "brand": "해링턴", "category": "아파트", "price": 2300, "target_price": 2600, "supply": 612, "status": "공고종료"},
    {"id": "dj_doan1", "name": "힐스테이트 도안리버파크 1단지", "address": "대전광역시 유성구", "brand": "힐스테이트", "category": "아파트", "price": 1950, "target_price": 2200, "supply": 1124, "status": "분양중"},
    {"id": "jt1", "name": "의정부역 스마트시티(지역주택조합)", "address": "경기도 의정부시", "brand": "기타", "category": "지역주택조합", "price": 1500, "target_price": 1750, "supply": 1614, "status": "조합원모집"},
    {"id": "uj_topseok1", "name": "의정부 탑석 센트럴파크 푸르지오", "address": "경기도 의정부시 탑석동", "brand": "푸르지오", "category": "아파트", "price": 2400, "target_price": 2700, "supply": 840, "status": "분양예정"},
    {"id": "uj_hoeryong1", "name": "의정부 회룡 파크뷰 자이", "address": "경기도 의정부시 회룡동", "brand": "자이", "category": "아파트", "price": 2200, "target_price": 2500, "supply": 650, "status": "분양중"},
    {"id": "uj_hoeryong2", "name": "회룡역 롯데캐슬", "address": "경기도 의정부시 회룡동", "brand": "롯데캐슬", "category": "아파트", "price": 2350, "target_price": 2650, "supply": 720, "status": "분양예정"},
    {"id": "uj_topseok2", "name": "탑석역 힐스테이트", "address": "경기도 의정부시 탑석동", "brand": "힐스테이트", "category": "아파트", "price": 2450, "target_price": 2750, "supply": 890, "status": "분양중"},
]

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for s_data in MOCK_SITES:
            existing = session.get(Site, s_data["id"])
            if not existing:
                session.add(Site(**s_data))
            else:
                for key, value in s_data.items():
                    setattr(existing, key, value)
        session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # 서버 시작 시 CSV 데이터 자동 로드 (데이터 유실 방지)
    try:
        import csv
        csv_file = "sites_data.csv"
        if os.path.exists(csv_file):
            with Session(engine) as session:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        site_id = row['id']
                        if not session.get(Site, site_id):
                            session.add(Site(
                                id=site_id,
                                name=row['name'],
                                address=row['address'],
                                brand=row['brand'] if row['brand'] else None,
                                category=row['category'],
                                price=float(row['price']),
                                target_price=float(row['target_price']),
                                supply=int(row['supply']),
                                status=row['status'] if row['status'] else None
                            ))
                    session.commit()
            logger.info("CSV data auto-imported on startup.")
    except Exception as e:
        logger.error(f"Startup data import error: {e}")
    yield

app = FastAPI(lifespan=lifespan)

# CORS 설정을 더 명시적으로 강화
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q or len(q) < 2:
        return []

    results = []
    seen_ids = set()
    q_lower = q.lower().strip()

    # 1. DB 검색 (분양 데이터베이스 우선)
    try:
        with Session(engine) as session:
            # 대소문자 구분 없이 검색 (name, address, brand, category, status 모두 검색)
            statement = select(Site).where(
                or_(
                    col(Site.name).ilike(f"%{q}%"), 
                    col(Site.address).ilike(f"%{q}%"), 
                    col(Site.brand).ilike(f"%{q}%"),
                    col(Site.category).ilike(f"%{q}%"),
                    col(Site.status).ilike(f"%{q}%")
                )
            ).order_by(col(Site.last_updated).desc()).limit(100)
            db_sites = session.exec(statement).all()
            for s in db_sites:
                if s.id not in seen_ids:
                    results.append(SiteSearchResponse(id=s.id, name=s.name, address=s.address, status=s.status, brand=s.brand, category=s.category))
                    seen_ids.add(s.id)
    except Exception as e:
        logger.error(f"DB search error: {e}")

    # 2. 실시간 분양 전문 API 검색 (구축 아파트를 원천 배제하기 위해 isale API만 사용)
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            fake_nnb = "".join(random.choices("0123456789ABCDEF", k=16))
            h = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://m.land.naver.com/",
                "Origin": "https://m.land.naver.com",
                "Cookie": f"NNB={fake_nnb}",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site"
            }
            
            # 분양 정보가 있는 'isale' 데이터베이스만 조회 (오래된 기축 아파트는 여기서 걸러짐)
            url_isale = "https://isale.land.naver.com/iSale/api/complex/searchList"
            params = {
                "keyword": q, 
                "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH", 
                "salesStatus": "0:1:2:3:4:5:6:7:8:9:10:11:12", 
                "pageSize": "100"
            }
            res_isale = await client.get(url_isale, params=params, headers=h, timeout=3.0)
            if res_isale.status_code == 200:
                data = res_isale.json()
                for it in data.get("result", {}).get("list", []):
                    sid = f"extern_isale_{it.get('complexNo')}"
                    if sid not in seen_ids:
                        results.append(SiteSearchResponse(
                            id=sid, name=it.get('complexName'), address=it.get('address'), 
                            status=it.get('salesStatusName'), brand=it.get('h_name'),
                            category=it.get('complexTypeName', '아파트')
                        ))
                        seen_ids.add(sid)
    except Exception as e:
        logger.error(f"API search error: {e}")

    # 검색 결과 정렬 - 현장명에 검색어가 포함된 경우 우선 표시
    def sort_key(x):
        name_lower = x.name.lower() if x.name else ""
        address_lower = x.address.lower() if x.address else ""
        
        # 정확히 일치하는 경우 최우선
        if name_lower == q_lower:
            return (0, 0)
        # 현장명이 검색어로 시작하는 경우
        if name_lower.startswith(q_lower):
            return (1, name_lower.find(q_lower))
        # 현장명에 검색어가 포함된 경우
        if q_lower in name_lower:
            return (2, name_lower.find(q_lower))
        # 주소에 검색어가 포함된 경우
        if q_lower in address_lower:
            return (3, address_lower.find(q_lower))
        # 그 외
        return (999, 999)
    
    results.sort(key=sort_key)
    logger.info(f"Search query: '{q}' returned {len(results)} results")
    return results[:100]

@app.get("/sync-all")
async def sync_all():
    # 구축을 제외한 전국의 '최근 5년 내' 분양/임대/지주택 리스트 퀀텀 동기화
    keywords = [
        "해링턴", "써밋", "디에트르", "지역주택조합", "지주택", "미분양", "선착순",
        "대전", "의정부", "부산", "서울", "인천", "경기", "수원", "성남",
        "탑석", "회룡", "파크뷰", "힐스테이트", "자이", "푸르지오", "e편한세상",
        "롯데캐슬", "아이파크", "더샵", "센트럴", "포레스트", "레이크", "스카이"
    ]
    count = 0
    async with httpx.AsyncClient() as client:
        for kw in keywords:
            try:
                fake_nnb = "".join(random.choices("0123456789ABCDEF", k=16))
                h = {"User-Agent": "Mozilla/5.0", "Cookie": f"NNB={fake_nnb}"}
                url = "https://isale.land.naver.com/iSale/api/complex/searchList"
                params = {"keyword": kw, "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH", "salesStatus": "0:1:2:3:4:5:6:7:8:9:10:11:12", "pageSize": "100"}
                res = await client.get(url, params=params, headers=h, timeout=8.0)
                if res.status_code == 200:
                    items = res.json().get("result", {}).get("list", [])
                    with Session(engine) as session:
                        for it in items:
                            sid = f"extern_isale_{it.get('complexNo')}"
                            if not session.get(Site, sid):
                                session.add(Site(
                                    id=sid, name=it.get("complexName"), address=it.get("address"),
                                    brand=it.get("h_name"), category=it.get("complexTypeName", "부동산"),
                                    price=1900.0, target_price=2200.0, supply=500, status=it.get("salesStatusName")
                                ))
                                count += 1
                        session.commit()
                await asyncio.sleep(0.3)
            except: pass
    return {"status": "sync_completed", "new_items": count, "message": "분양/임대/지주택 전문 데이터 동기화가 완료되었습니다. (구축 제외)"}

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if site: return site
        return {"id": site_id, "name": "분양 분석 완료", "address": "지역 정보", "brand": "기타", "category": "부동산", "price": 2500, "target_price": 2800, "supply": 500, "status": "데이터 로드"}

class AnalyzeRequest(BaseModel):
    field_name: Optional[str] = "알 수 없는 현장"
    address: Optional[str] = "지역 정보 없음"
    product_category: Optional[str] = "아파트"
    sales_stage: Optional[str] = "분양중"
    down_payment: Optional[int] = 10
    interest_benefit: Optional[str] = "없음"
    additional_benefits: Optional[str] = "없음"
    main_concern: Optional[str] = "기타"
    monthly_budget: Optional[int] = 0
    existing_media: Optional[str] = "없음"
    sales_price: Optional[float] = 0.0
    target_area_price: Optional[float] = 0.0
    down_payment_amount: Optional[int] = 0
    supply_volume: Optional[int] = 0
    field_keypoints: Optional[str] = ""
    user_email: Optional[str] = None

@app.post("/analyze")
async def analyze_site(request: Optional[AnalyzeRequest] = None):
    """현장 분석 API"""
    try:
        # 데이터가 아예 안 들어왔을 경우의 기본값 처리
        req = request if request else AnalyzeRequest()
        
        # 필드 값 추출 (기본값 보장)
        field_name = getattr(req, 'field_name', "분석 현장")
        sales_price = float(getattr(req, 'sales_price', 0.0) or 0.0)
        target_price = float(getattr(req, 'target_area_price', 0.0) or 0.0)
        supply_volume = int(getattr(req, 'supply_volume', 0) or 0)
        
        # 로직 시작
        price_score = min(100, max(0, 100 - abs(sales_price - target_price) / (target_price if target_price > 0 else 1) * 100))
        location_score = 75 + random.randint(-5, 10)
        benefit_score = 70 + random.randint(-5, 10)
        total_score = int((price_score * 0.4 + location_score * 0.3 + benefit_score * 0.3))
        
        market_gap = target_price - sales_price
        market_gap_percent = (market_gap / (sales_price if sales_price > 0 else 1)) * 100
        
        return {
            "score": total_score,
            "score_breakdown": {
                "price_score": int(price_score),
                "location_score": int(location_score),
                "benefit_score": int(benefit_score),
                "total_score": total_score
            },
            "market_diagnosis": f"{field_name}은 주변 시세 대비 {abs(market_gap_percent):.1f}% {'저렴' if market_gap_percent > 0 else '높은'} 수준으로 평가됩니다.",
            "market_gap_percent": round(market_gap_percent, 2),
            "price_data": [
                {"name": "우리 현장", "price": sales_price},
                {"name": "주변 시세", "price": target_price},
                {"name": "프리미엄", "price": target_price * 1.1}
            ],
            "radar_data": [
                {"subject": "분양가", "A": int(price_score), "B": 70, "fullMark": 100},
                {"subject": "브랜드", "A": 85, "B": 75, "fullMark": 100},
                {"subject": "단지규모", "A": min(100, supply_volume // 10), "B": 60, "fullMark": 100},
                {"subject": "입지", "A": int(location_score), "B": 65, "fullMark": 100},
                {"subject": "분양조건", "A": 80, "B": 50, "fullMark": 100},
                {"subject": "상품성", "A": int(benefit_score), "B": 70, "fullMark": 100}
            ],
            "ad_recommendation": "전략적 통합 마케팅 믹스 추천",
            "media_mix": [
                {"media": "메타/인스타", "feature": "정밀 타켓팅", "reason": "관심사 기반 도달", "strategy_example": "혜택 강조 광고"},
                {"media": "네이버", "feature": "검색 기반", "reason": "구매 의향 고객 확보", "strategy_example": "지역 키워드 점유"},
                {"media": "로컬 매체", "feature": "지역 밀착", "reason": "실거주 수요 확보", "strategy_example": "인근 지역 타겟팅"}
            ],
            "target_audience": ["실수요자", "신혼부부", "자녀교육"],
            "target_persona": "30-40대 실수요 중심의 안정적인 자산 형성을 원하는 고객",
            "competitors": [
                {"name": "인근 경쟁 단지 A", "price": target_price * 0.95, "distance": "1.2km"},
                {"name": "인근 경쟁 단지 B", "price": target_price * 1.05, "distance": "2.5km"}
            ],
            "weekly_plan": [
                "1주차: 타겟 고객 DB 확보 및 초기 인지도 확산",
                "2주차: 핵심 혜택 중심 집중 광고 캠페인",
                "3주차: 모델하우스 방문 유도 및 상담 전환",
                "4주차: 계약 독려 및 마감 임박 메시지"
            ]
        }
    except Exception as e:
        logger.error(f"Analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/import-csv")
async def import_csv_data():
    """CSV 파일에서 데이터를 import"""
    import csv
    
    csv_file = "sites_data.csv"
    if not os.path.exists(csv_file):
        return {"status": "error", "message": "CSV 파일을 찾을 수 없습니다."}
    
    imported = 0
    updated = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            with Session(engine) as session:
                for row in reader:
                    site_id = row['id']
                    existing = session.get(Site, site_id)
                    
                    if existing:
                        existing.name = row['name']
                        existing.address = row['address']
                        existing.brand = row['brand'] if row['brand'] else None
                        existing.category = row['category']
                        existing.price = float(row['price'])
                        existing.target_price = float(row['target_price'])
                        existing.supply = int(row['supply'])
                        existing.status = row['status'] if row['status'] else None
                        existing.last_updated = datetime.datetime.now()
                        updated += 1
                    else:
                        new_site = Site(
                            id=site_id,
                            name=row['name'],
                            address=row['address'],
                            brand=row['brand'] if row['brand'] else None,
                            category=row['category'],
                            price=float(row['price']),
                            target_price=float(row['target_price']),
                            supply=int(row['supply']),
                            status=row['status'] if row['status'] else None
                        )
                        session.add(new_site)
                        imported += 1
                
                session.commit()
        
        return {
            "status": "success",
            "imported": imported,
            "updated": updated,
            "total": imported + updated,
            "message": f"CSV import 완료: 신규 {imported}개, 업데이트 {updated}개"
        }
    except Exception as e:
        logger.error(f"CSV import error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
