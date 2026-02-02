from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn
import logging
import sys

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bunyang")

app = FastAPI(title="Bunyang AlphaGo API")

# CORS 설정 - 모든 도메인 허용 (Vercel 연동용)
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
    logger.info("Application starting up...")

@app.get("/")
def home(request: Request):
    logger.info(f"Health check from {request.client.host}")
    return {
        "status": "online",
        "message": "Bunyang AlphaGo API is LIVE",
        "env_port": os.getenv("PORT", "not set"),
        "active_host": "0.0.0.0"
    }

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str = ""):
    logger.info(f"Searching for: {q}")
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    results = [SiteSearchResponse(**s) for s in MOCK_SITES 
               if q_norm in (s["name"] + s["address"]).lower().replace(" ", "")]
    
    if not results:
        results = [SiteSearchResponse(id="debug", name=f"'{q}' - 연결 확인됨", address="데이터베이스 연동 대기 중", status="OK")]
    return results

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    for s in MOCK_SITES:
        if s["id"] == site_id: return s
    return {"id": site_id, "name": "상세 데이터 연결됨", "address": "정상"}

@app.post("/analyze")
async def analyze(data: dict):
    return {"score": 90, "market_diagnosis": "연결 및 분석 시스템 가동 중"}

if __name__ == "__main__":
    # Railway 시스템에서 주는 포트를 우선적으로 사용
    # 사용자님이 8080으로 설정했더라도, 프로그램은 $PORT 변수를 보는 것이 가장 안전함
    port_str = os.getenv("PORT", "8080")
    try:
        port = int(port_str)
    except ValueError:
        port = 8080
    
    logger.info(f"Uvicorn starting on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
