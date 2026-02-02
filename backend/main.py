from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
import logging
import sys

# 가장 상세한 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bunyang")

app = FastAPI()

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

@app.get("/")
async def health(request: Request):
    logger.info(f"Health check hit from {request.client.host}")
    return {"status": "ok", "port": os.getenv("PORT", "unknown")}

@app.get("/search-sites")
async def search(q: str = ""):
    logger.info(f"Search request: q={q}")
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    results = [s for s in MOCK_SITES 
               if q_norm in (s["name"] + s["address"]).lower().replace(" ", "")]
    
    # 연결 확인을 위한 강제 데이터 추가
    if not results:
        results = [{"id": "debug", "name": f"연결됨: {q}", "address": "데이터를 찾는 중입니다", "status": "OK"}]
    return results

if __name__ == "__main__":
    # Railway 시스템의 동적 포트를 완벽하게 지원하는 정석 코드
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting server on 0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
