from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok", "message": "Debug Final"}

@app.get("/search-sites")
def search(q: str = ""):
    # 아무것도 묻지도 따지지도 않고 데이터를 뱉습니다.
    return [
        {"id": "s1", "name": "의정부 힐스테이트 (연결성공)", "address": "의정부시", "brand": "힐스테이트", "status": "정상"}
    ]

@app.get("/site-details/{site_id}")
def details(site_id: str):
    return {"id": site_id, "name": "상세 성공"}

if __name__ == "__main__":
    import uvicorn
    # Railway는 이 PORT 변수를 매우 중요하게 생각합니다.
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
