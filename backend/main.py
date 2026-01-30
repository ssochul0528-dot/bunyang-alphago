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

# 가장 기본적이고 안전한 설정으로 복구
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # 앱 시작 시 데이터를 채웁니다.
    seed_sites()

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
    # 백그라운드 태스크 시작
    asyncio.create_task(update_sites_task())

def seed_sites():
    with Session(engine) as session:
        # 데이터가 있는지 확인
        statement = select(Site)
        existing = session.exec(statement).first()
        if existing:
            return
        
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
    while True:
        await asyncio.sleep(86400) # 하루에 한 번
        with Session(engine) as session:
            sites = session.exec(select(Site)).all()
            for site in sites:
                change = random.uniform(-0.005, 0.005)
                site.target_price = round(site.target_price * (1 + change), 1)
                site.last_updated = datetime.datetime.now()
                session.add(site)
            session.commit()

# Mock Data
MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "선착순 계약 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "price": 1100, "target_price": 1300, "supply": 600, "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "category": "오피스텔", "price": 4500, "target_price": 5200, "supply": 300, "status": "잔여세대 분양 중"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "category": "아파트", "price": 1450, "target_price": 1600, "supply": 851, "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양 잔여세대"}
]
# ... (다른 MOCK_SITES 데이터는 생략하되 실제 파일엔 유지됩니다)

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
        results = []
        for s in all_sites:
            search_pool = (s.name + s.address + (s.brand or "") + s.category).lower().replace(" ", "")
            if q_norm in search_pool:
                results.append(SiteSearchResponse(id=s.id, name=s.name, address=s.address, brand=s.brand, status=s.status))
        return results

@app.get("/")
def read_root():
    return {"status": "online", "message": "Bunyang AlphaGo API"}

# (기타 엔드포인트 생략 방지 - 실제 파일 전체 내용 유지 필요)
