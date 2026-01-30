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

# 앱 인스턴스 생성
app = FastAPI(title="Bunyang AlphaGo API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 설정
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

# 모델 정의
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

# 스키마 정의 (응답용)
class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

# 모의 데이터 세트
MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "price": 2417, "target_price": 2750, "supply": 1816, "status": "선착순 계약 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "price": 1100, "target_price": 1300, "supply": 600, "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "category": "오피스텔", "price": 4500, "target_price": 5200, "supply": 300, "status": "잔여세대 분양 중"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "category": "아파트", "price": 1450, "target_price": 1600, "supply": 851, "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "price": 2100, "target_price": 2300, "supply": 671, "status": "미분양 잔여세대"}
]

# 부팅 속도를 위해 초기화를 최소화
@app.on_event("startup")
async def on_startup():
    # 백그라운드에서 조용히 DB 생성
    def init_db():
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            if not session.exec(select(Site)).first():
                for s in MOCK_SITES:
                    session.add(Site(**s))
                session.commit()
    
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, init_db)

# 엔드포인트: 상태 확인
@app.get("/")
async def read_root():
    return {"status": "online", "message": "API Active", "timestamp": str(datetime.datetime.now())}

# 엔드포인트: 검색
@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    with Session(engine) as session:
        all_sites = session.exec(select(Site)).all()
        return [
            SiteSearchResponse(id=s.id, name=s.name, address=s.address, brand=s.brand, status=s.status)
            for s in all_sites if q_norm in (s.name + s.address + (s.brand or "")).lower().replace(" ", "")
        ]

# 필수 엔드포인트: 상세
@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if not site: raise HTTPException(status_code=404)
        return site

if __name__ == "__main__":
    import uvicorn
    # Railway 시스템에서 주는 포트 사용
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
