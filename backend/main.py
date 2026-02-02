from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="Bunyang AlphaGo Final Fix")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "status": "정상 작동 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "status": "정상 작동 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "status": "정상 작동 중"}
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

@app.get("/")
def home():
    return {"status": "online", "message": "Backend Connected Successfully", "port": "8080"}

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str = ""):
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    results = [SiteSearchResponse(**s) for s in MOCK_SITES 
               if q_norm in (s["name"] + s["address"]).lower().replace(" ", "")]
    
    # 🚨 무조건 결과를 하나는 띄우게 해서 연결 성공을 시각적으로 확인
    if not results:
        results = [SiteSearchResponse(id="debug", name=f"'{q}' 연결 성공(데이터없음)", address="시스템 정상", status="OK")]
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
    import uvicorn
    # 🚨 Railway 설정과 맞춘 8080 강제 고정
    uvicorn.run(app, host="0.0.0.0", port=8080)
