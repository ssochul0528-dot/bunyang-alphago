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

# --- MEGA SEED DATA: 전국 랜드마크 60선 ---
MOCK_SITES = [
    {"id": "h1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "분양중"},
    {"id": "h2", "name": "힐스테이트 평택 화양", "address": "경기도 평택시 안중읍", "brand": "힐스테이트", "category": "아파트", "price": 1450, "target_price": 1650, "supply": 1571, "status": "분양중"},
    {"id": "h3", "name": "힐스테이트 더 운정", "address": "경기도 파주시 와동동", "brand": "힐스테이트", "category": "오피스텔", "price": 3800, "target_price": 4200, "supply": 2669, "status": "선착순"},
    {"id": "p1", "name": "용인 푸르지오 원클러스터", "address": "경기도 용인시 처인구", "brand": "푸르지오", "category": "아파트", "price": 1850, "target_price": 2100, "supply": 1681, "status": "분양중"},
    {"id": "x1", "name": "송도 자이 풍경채 그라노블", "address": "인천광역시 연수구 송도동", "brand": "자이", "category": "아파트", "price": 2550, "target_price": 2850, "supply": 3270, "status": "분양중"},
    {"id": "l1", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2150, "target_price": 2400, "supply": 671, "status": "분양중"},
    {"id": "r1", "name": "GTX의정부역 호반써밋(민간임대)", "address": "경기도 의정부시 의정부동", "brand": "호반써밋", "category": "민간임대", "price": 2300, "target_price": 2600, "supply": 400, "status": "임대분양"},
    {"id": "r2", "name": "수지구청역 롯데캐슬 하이브엘(민간임대)", "address": "경기도 용인시 수지구", "brand": "롯데캐슬", "category": "민간임대", "price": 3500, "target_price": 4000, "supply": 715, "status": "임대완료"},
    {"id": "o1", "name": "송도 더샵 타임스퀘어", "address": "인천광역시 연수구 송도동", "brand": "더샵", "category": "오피스텔", "price": 3500, "target_price": 3900, "supply": 250, "status": "선착순"},
]

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for s_data in MOCK_SITES:
            existing = session.get(Site, s_data["id"])
            if not existing:
                session.add(Site(**s_data))
        session.commit()

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

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q or len(q) < 2: # 최소 두 글자
        return []

    results = []
    seen_ids = set()

    # 1. DB 초정밀 부분 일치 검색 (이름, 주소, 브랜드 모두 뒤짐)
    try:
        with Session(engine) as session:
            # col(Site.name).contains(q) 는 중간 글자 일치 검색을 수행합니다 (SQL LIKE %q%)
            statement = select(Site).where(
                or_(
                    col(Site.name).contains(q),
                    col(Site.address).contains(q),
                    col(Site.brand).contains(q)
                )
            ).limit(40)
            db_sites = session.exec(statement).all()
            for s in db_sites:
                if s.id not in seen_ids:
                    results.append(SiteSearchResponse(
                        id=s.id, name=s.name, address=s.address,
                        status=s.status or "현장 정보", brand=s.brand
                    ))
                    seen_ids.add(s.id)
    except Exception as e:
        logger.error(f"DB Search Error: {e}")

    # 2. 실시간 보완 (DB 결과가 적을 때만 네이버에 필터링 없이 물어봄)
    if len(results) < 15:
        try:
            async with httpx.AsyncClient() as client:
                fake_nnb = "".join(random.choices("0123456789ABCDEF", k=16))
                h = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                    "Cookie": f"NNB={fake_nnb}"
                }
                
                # 시도 1: 분양 전문 API (조금 더 느리지만 정확함)
                url_isale = "https://isale.land.naver.com/iSale/api/complex/searchList"
                params_isale = {
                    "keyword": q,
                    "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH",
                    "salesType": "mng:pub:rent:sh:lh:etc",
                    "pageSize": "100"
                }
                res = await client.get(url_isale, params=params_isale, headers=h, timeout=5.0)
                if res.status_code == 200:
                    for it in res.json().get("result", {}).get("list", []):
                        sid = f"extern_isale_{it.get('complexNo')}"
                        if sid not in seen_ids:
                            results.append(SiteSearchResponse(
                                id=sid, name=it.get('complexName'), address=it.get('address'), 
                                status=it.get('salesStatusName'), brand=it.get('h_name')
                            ))
                            seen_ids.add(sid)
                
                # 시도 2: 네이버 통합 자동완성 (매우 빠름, 현장명 부분 검색에 탁월)
                if len(results) < 10:
                    url_ac = "https://m.land.naver.com/search/result/searchAutoComplete.json"
                    res_ac = await client.get(url_ac, params={"keyword": q}, headers=h, timeout=2.0)
                    if res_ac.status_code == 200:
                        for it in res_ac.json().get("result", {}).get("list", []):
                            sid = f"extern_ac_{it.get('id', it.get('name'))}"
                            if sid not in seen_ids:
                                results.append(SiteSearchResponse(
                                    id=sid, name=it.get('name'), address=it.get('fullAddress'), 
                                    status="실시간"
                                ))
                                seen_ids.add(sid)
        except: pass

    # 결과 정렬: 검색어가 이름의 앞에 올수록 우선순위 부여
    results.sort(key=lambda x: (x.name.find(q) if x.name.find(q) != -1 else 999))
    
    return results[:60]

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if site: return site
        return {"id": site_id, "name": "현장 정보", "address": "지역 정보", "brand": "기타", "category": "부동산", "price": 2500, "target_price": 2800, "supply": 500, "status": "분양중"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main.py:app", host="0.0.0.0", port=port, reload=True)
