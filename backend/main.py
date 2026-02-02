from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bunyang")

app = FastAPI(title="Bunyang AlphaGo API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터
MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "status": "정상 작동 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "status": "정상 작동 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "status": "정상 작동 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "status": "정상 작동 중"}
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    logger.info("서버가 시작되었습니다!")

@app.get("/")
def home(request: Request):
    logger.info(f"Root request from {request.client.host}")
    return {"status": "online", "message": "Bunyang AlphaGo API is LIVE", "port": os.getenv("PORT", "unknown")}

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str = ""):
    logger.info(f"Search request: q='{q}'")
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    results = [SiteSearchResponse(**s) for s in MOCK_SITES 
               if q_norm in (s["name"] + s["address"]).lower().replace(" ", "")]
    
    # 디버깅용: 결과가 없으면 샘플 하나 제공
    if not results:
        results = [SiteSearchResponse(id="debug", name=f"'{q}' 검색됨 (연결확인)", address="시스템 정상 작동 중", status="OK")]
    return results

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    logger.info(f"Details request: id={site_id}")
    for s in MOCK_SITES:
        if s["id"] == site_id: return s
    return {"id": site_id, "name": "상세 데이터 연결됨", "address": "정상"}

@app.post("/analyze")
async def analyze(data: dict):
    logger.info("Analysis request received")
    return {"score": 90, "market_diagnosis": "연결 및 분석 시스템 가동 중"}

if __name__ == "__main__":
    # Railway 시스템에서 주는 포트를 우선적으로 사용
    # 사용자님이 8080으로 설정했더라도, 프로그램은 $PORT 변수를 보는 것이 가장 안전함
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
