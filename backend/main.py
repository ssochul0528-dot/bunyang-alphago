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

# --- Initial Seed Data (전국구 스타터 팩) ---
MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "선착순"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양"},
    {"id": "s13", "name": "GTX의정부역 호반써밋", "address": "경기도 의정부시 의정부동", "brand": "호반써밋", "category": "아파트", "price": 2300, "target_price": 2600, "supply": 400, "status": "민간임대"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군", "brand": "e편한세상", "category": "아파트", "price": 1100, "target_price": 1300, "supply": 600, "status": "분양중"},
    {"id": "s5", "name": "송도 자이 풍경채 그라노블", "address": "인천광역시 연수구 송도동", "brand": "자이", "category": "아파트", "price": 2500, "target_price": 2800, "supply": 3270, "status": "선착순"},
    {"id": "s8", "name": "평택 브레인시티 중흥S-클래스", "address": "경기도 평택시", "brand": "중흥S-클래스", "category": "아파트", "price": 1500, "target_price": 1800, "supply": 1980, "status": "분양중"},
    {"id": "s14", "name": "김포 북변 우미린 파크리브", "address": "경기도 김포시 북변동", "brand": "우미린", "category": "아파트", "price": 1800, "target_price": 2100, "supply": 1200, "status": "모집공고"},
    {"id": "s15", "name": "동탄역 대방 엘리움 더시그니처", "address": "경기도 화성시 오산동", "brand": "대방", "category": "아파트", "price": 2200, "target_price": 2600, "supply": 464, "status": "청약완료"}
]

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if session.exec(select(Site)).first() is None:
            for s_data in MOCK_SITES:
                session.add(Site(**s_data))
            session.commit()
            logger.info("Seed data inserted.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

class AnalysisRequest(BaseModel):
    site_id: str
    fieldName: str
    address: str
    productCategory: str
    salesStage: str
    down_payment: str
    interest_benefit: str
    additional_benefits: List[str]
    main_concern: str
    monthly_budget: int
    sales_price: float
    target_area_price: float

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q or len(q) < 2:
        return []

    results = []
    seen_ids = set()

    # 1. DB 검색 (0.1초 소요)
    try:
        with Session(engine) as session:
            statement = select(Site).where(
                or_(
                    col(Site.name).contains(q),
                    col(Site.address).contains(q)
                )
            )
            db_sites = session.exec(statement).all()
            for s in db_sites:
                if s.id not in seen_ids:
                    results.append(SiteSearchResponse(
                        id=s.id, name=s.name, address=s.address,
                        status=s.status or "분양 정보", brand=s.brand
                    ))
                    seen_ids.add(s.id)
    except Exception as e:
        logger.error(f"DB Error: {e}")

    # 2. 결과 부족 시 실시간 보완 (차단 위험이 있으나 시도는 함)
    if len(results) < 5:
        try:
            async with httpx.AsyncClient() as client:
                h = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"}
                res = await client.get("https://m.land.naver.com/search/result/searchAutoComplete.json", params={"keyword": q}, headers=h, timeout=3.0)
                if res.status_code == 200 and "json" in res.headers.get("type", "json"):
                    for item in res.json().get("result", {}).get("list", []):
                        sid = f"extern_ac_{item.get('id', item.get('name'))}"
                        if sid not in seen_ids:
                            results.append(SiteSearchResponse(id=sid, name=item.get('name'), address=item.get('fullAddress'), status="실시간 데이터"))
                            seen_ids.add(sid)
        except: pass

    return results[:15]

@app.get("/sync-all")
async def sync_all():
    keywords = ["힐스테이트", "푸르지오", "자이", "롯데캐슬", "아이파크", "호반", "우미린", "김포", "동탄", "평택", "부산"]
    count = 0
    async with httpx.AsyncClient() as client:
        for kw in keywords:
            try:
                url = "https://isale.land.naver.com/iSale/api/complex/searchList"
                params = {"keyword": kw, "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH", "pageSize": "50"}
                res = await client.get(url, params=params, timeout=10.0)
                if res.status_code == 200:
                    items = res.json().get("result", {}).get("list", [])
                    with Session(engine) as session:
                        for it in items:
                            sid = f"extern_isale_{it.get('complexNo')}"
                            if not session.get(Site, sid):
                                session.add(Site(
                                    id=sid, name=it.get("complexName"), address=it.get("address"),
                                    brand=it.get("h_name"), category=it.get("complexTypeName", "아파트"),
                                    price=2000.0, target_price=2300.0, supply=500, status=it.get("salesStatusName")
                                ))
                                count += 1
                        session.commit()
                await asyncio.sleep(0.5)
            except: pass
    return {"status": "sync_completed", "new_items": count}

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if site: return site
        return {"id": site_id, "name": "기타 현장", "address": "지역 정보", "brand": "기타", "category": "아파트", "price": 2500, "target_price": 2800, "supply": 500, "status": "실시간"}

@app.post("/analyze")
async def analyze(req: AnalysisRequest):
    return {"status": "success"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main.py:app", host="0.0.0.0", port=port, reload=True)
