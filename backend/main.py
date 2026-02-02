from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="Bunyang AlphaGo Final")

# CORS를 아주 넓게 엽니다 (Vercel 연결 보장)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_SITES = [
    {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "경기도 의정부시 호원동 281-21", "brand": "힐스테이트", "category": "아파트", "status": "선착순 계약 중"},
    {"id": "s12", "name": "의정부 롯데캐슬 나리벡시티", "address": "경기도 의정부시 금오동", "brand": "롯데캐슬", "category": "아파트", "status": "미분양 잔여세대"},
    {"id": "s2", "name": "e편한세상 내포 퍼스트드림", "address": "충청남도 홍성군 홍북읍", "brand": "e편한세상", "category": "아파트", "status": "선착순 분양 중"},
]

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None

@app.get("/")
def home():
    # Railway가 할당한 실제 포트 확인용
    return {"status": "online", "msg": "API is Alive", "port": os.getenv("PORT", "unknown")}

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str = ""):
    if not q: return []
    q_norm = q.lower().replace(" ", "")
    results = [SiteSearchResponse(**s) for s in MOCK_SITES 
               if q_norm in (s["name"] + s["address"]).lower().replace(" ", "")]
    
    # 🚨 테스트용: 결과가 없으면 샘플 하나를 강제로 보여줍니다 (연결 확인용)
    if not results and q:
        results = [SiteSearchResponse(id="test", name="연결됨: "+q, address="목록에 없는 현장입니다", status="준비중")]
        
    return results

if __name__ == "__main__":
    import uvicorn
    # 로컬 실행용 (서버에선 railway.json의 startCommand를 따름)
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
