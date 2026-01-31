from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn

app = FastAPI(title="Bunyang AlphaGo API Recovery")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "status": "선착순 계약 중"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "status": "선착순 분양 중"},
    {"id": "s3", "name": "마포 에피트 어바닉", "address": "서울특별시 마포구 아현동", "brand": "에피트", "category": "오피스텔", "status": "잔여세대 분양 중"},
    {"id": "s11", "name": "평택 푸르지오 센터파인", "address": "경기도 평택시 화양지구", "brand": "푸르지오", "category": "아파트", "status": "선착순 동호지정 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "status": "미분양 잔여세대"}
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
    results = [SiteSearchResponse(**s) for s in MOCK_SITES 
               if q_norm in (s["name"] + s["address"]).lower().replace(" ", "")]
    return results

@app.get("/")
def home():
    # 현재 서버가 인식하고 있는 포트 정보를 보여줍니다.
    port = os.getenv("PORT", "Unknown")
    return {"status": "online", "message": "API Sync Complete", "assigned_port": port}

if __name__ == "__main__":
    # 이 부분은 로컬 테스트용이며, 서버에서는 railway.json의 명령어를 따릅니다.
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
