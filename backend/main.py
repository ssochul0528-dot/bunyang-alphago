from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import datetime

# 앱 인스턴스
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 초경량 데이터 세트 (DB 없이 메모리에서 즉시 실행) ---
MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "status": "선착순 계약 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "status": "잔여세대 분양 중"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "status": "미분양 잔여세대"}
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Railway Connection Success",
        "port": os.getenv("PORT", "unknown")
    }

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    # 메모리 내 데이터에서 즉시 검색 (DB 부하 0)
    results = [
        SiteSearchResponse(**s) for s in MOCK_SITES 
        if q_norm in (s["name"] + s["address"] + (s["brand"] or "")).lower().replace(" ", "")
    ]
    return results

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    for s in MOCK_SITES:
        if s["id"] == site_id:
            return s
    raise HTTPException(status_code=404, detail="Site not found")

# 분석 API (기본 뼈대 유지)
@app.post("/analyze")
async def analyze(data: dict):
    return {"score": 85, "market_diagnosis": "연결 성공! 분석 데이터가 정상적으로 수신되었습니다."}

if __name__ == "__main__":
    import uvicorn
    # Railway 환경 변수 포트 우선 사용
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
