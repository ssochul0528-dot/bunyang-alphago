from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "status": "선착순 계약 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "status": "잔여세대 분양 중"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "status": "미분양 잔여세대"},
    {"id": "s13", "name": "푸르지오 라디우스 파크", "address": "서울특별시 성북구", "brand": "푸르지오", "status": "청약 접수 중"}
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

@app.get("/")
def home():
    return {"status": "online", "message": "API is live", "count": len(MOCK_SITES)}

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q: return []
    # 검색어 정규화 (소문자, 공백제거)
    q_norm = q.replace(" ", "").lower()
    results = []
    for s in MOCK_SITES:
        # 이름, 주소, 브랜드에서 모두 검색
        text = (s["name"] + s["address"] + (s["brand"] or "")).replace(" ", "").lower()
        if q_norm in text:
            results.append(SiteSearchResponse(**s))
    
    print(f"Search for '{q}' returned {len(results)} results")
    return results

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    for s in MOCK_SITES:
        if s["id"] == site_id: return s
    raise HTTPException(status_code=404)

@app.post("/analyze")
async def analyze(data: dict):
    return {"score": 88, "market_diagnosis": "분석 성공", "media_mix": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
