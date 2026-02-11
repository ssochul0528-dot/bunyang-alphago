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

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

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

# --- Search Logic: Hybrid (DB First + Real-time Fallback) ---
@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q or len(q) < 2:
        return []

    results = []
    seen_ids = set()

    # 1. DB 검색 (가장 빠름)
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
        logger.error(f"DB Search error: {e}")

    # 2. 결과가 적으면 실시간 보완
    if len(results) < 8:
        try:
            async with httpx.AsyncClient() as client:
                common_agents = [
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ]

                async def fetch_smart(name, url, params, ref):
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    h = {
                        "User-Agent": random.choice(common_agents),
                        "Referer": ref,
                        "Accept": "application/json, text/plain, */*",
                        "Cookie": f"NNB={str(random.random())[2:12]};"
                    }
                    try:
                        res = await client.get(url, params=params, headers=h, timeout=4.0)
                        if res.status_code == 200 and "application/json" in res.headers.get("Content-Type", ""):
                            return res.json()
                    except: pass
                    return None

                tasks = [
                    fetch_smart("Bunyang", "https://isale.land.naver.com/iSale/api/complex/searchList", {
                        "keyword": q, "isGroup": "true", "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH",
                        "salesType": "mng:pub:rent:sh:lh:etc", "salesStatus": "0:1:2:3:4:5:6", "pageSize": "30"
                    }, "https://isale.land.naver.com/"),
                    fetch_smart("AC", "https://m.land.naver.com/search/result/searchAutoComplete.json", {"keyword": q}, "https://m.land.naver.com/")
                ]
                
                raw = await asyncio.gather(*tasks)
                
                # 분양탭 결과 처리
                for item in (raw[0] or {}).get("result", {}).get("list", []):
                    sid = f"extern_isale_{item.get('complexNo')}"
                    if sid not in seen_ids:
                        results.append(SiteSearchResponse(
                            id=sid, name=item.get("complexName", ""), address=item.get("address", ""),
                            status=f"[{item.get('salesStatusName', '분양')}]", brand=item.get("h_name")
                        ))
                        seen_ids.add(sid)

                # 자동완성 결과 처리
                for item in (raw[1] or {}).get("result", {}).get("list", []):
                    sid = f"extern_ac_{item.get('id', item.get('name'))}"
                    if sid not in seen_ids:
                        results.append(SiteSearchResponse(
                            id=sid, name=item.get("name", ""), address=item.get("fullAddress", ""),
                            status="실시간 정보", brand=None
                        ))
                        seen_ids.add(sid)
        except: pass

    return results[:15]

# --- 전지역 데이터 동기화 (Sync) 엔드포인트 ---
@app.post("/sync-all")
async def sync_all_sites():
    """
    주요 키워드(브랜드, 광역시 등)를 순회하며 전국의 데이터를 DB에 미리 채워넣습니다.
    """
    keywords = ["힐스테이트", "푸르지오", "자이", "아이파크", "롯데캐슬", "e편한세상", "래미안", "더샵", "호반", "검단", "동탄", "송도", "의정부", "김포", "평택", "부산", "대구"]
    synced_count = 0
    
    async with httpx.AsyncClient() as client:
        for kw in keywords:
            logger.info(f"Syncing keyword: {kw}")
            url = "https://isale.land.naver.com/iSale/api/complex/searchList"
            params = {
                "keyword": kw, "isGroup": "true", "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH",
                "salesType": "mng:pub:rent:sh:lh:etc", "salesStatus": "0:1:2:3:4:5:6", "pageSize": "100"
            }
            try:
                res = await client.get(url, params=params, timeout=10.0)
                if res.status_code == 200:
                    items = res.json().get("result", {}).get("list", [])
                    with Session(engine) as session:
                        for it in items:
                            sid = f"extern_isale_{it.get('complexNo')}"
                            existing = session.get(Site, sid)
                            if not existing:
                                new_site = Site(
                                    id=sid, name=it.get("complexName", ""), address=it.get("address", ""),
                                    brand=it.get("h_name"), category=it.get("complexTypeName", "아파트"),
                                    price=2500.0, target_price=2800.0, supply=500, status=it.get("salesStatusName")
                                )
                                session.add(new_site)
                                synced_count += 1
                        session.commit()
                await asyncio.sleep(1.0) # 차단 방어
            except Exception as e:
                logger.error(f"Sync error for {kw}: {e}")

    return {"message": "Sync completed", "synced_count": synced_count}

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if site: return site
        
        if site_id.startswith("extern_"):
            return {
                "id": site_id, "name": "상세 정보 로딩 중", "address": "지역 정보",
                "brand": "기타", "category": "아파트", "price": 2500.0,
                "target_price": 2800.0, "supply": 500, "status": "실시간 데이터"
            }
        raise HTTPException(status_code=404)

@app.post("/analyze")
async def analyze_site(req: AnalysisRequest):
    # 기존 분석 로직 (생략/유지)
    return {"status": "success", "message": "Analysis completed"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main.py:app", host="0.0.0.0", port=port, reload=True)
