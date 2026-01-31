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
    seed_sites()

@app.on_event("startup")
async def on_startup():
    # Railway 503 방지: 부팅 즉시 완료 신호를 보내고 데이터는 백그라운드에서 채움
    asyncio.create_task(run_startup_tasks())

async def run_startup_tasks():
    await asyncio.sleep(0.5)
    create_db_and_tables()

def seed_sites():
    with Session(engine) as session:
        if session.exec(select(Site)).first():
            return
        for s in MOCK_SITES:
            session.add(Site(**s))
        session.commit()

MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "선착순 계약 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "price": 1100, "target_price": 1300, "supply": 600, "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "category": "오피스텔", "price": 4500, "target_price": 5200, "supply": 300, "status": "잔여세대 분양 중"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "category": "아파트", "price": 1450, "target_price": 1600, "supply": 851, "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양 잔여세대"}
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

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

@app.get("/")
def home():
    return {"status": "online", "message": "Bunyang AlphaGo API is ready"}

if __name__ == "__main__":
    import uvicorn
    # Railway가 준 포트를 우선적으로 사용, 없으면 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
