from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn
import logging
import sys

# 디버깅을 위한 강력한 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bunyang")

app = FastAPI(title="Bunyang AlphaGo Final")

# CORS를 모든 도메인에 대해 활짝 엽니다
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "status": "정상"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "status": "정상"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "status": "정상"}
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

@app.get("/")
def home():
    logger.info("Health check received at root /")
    return {"status": "online", "message": "API IS READY"}

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str = ""):
    logger.info(f"Search request for query: {q}")
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    results = [SiteSearchResponse(**s) for s in MOCK_SITES 
               if q_norm in (s["name"] + s["address"]).lower().replace(" ", "")]
    
    # 연결 성공 여부를 눈으로 확인하기 위해 결과가 없어도 가짜 데이터를 하나 보냅니다.
    if not results:
        results = [SiteSearchResponse(id="debug", name=f"'{q}' 연결 성공!", address="서버와 통신이 원활합니다", status="OK")]
    return results

if __name__ == "__main__":
    # Railway가 할당하는 동적 포트를 완벽하게 지원
    port = int(os.getenv("PORT", 8080))
    # 🚨 반드시 0.0.0.0으로 열어야 외부에서 접속 가능합니다!
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
