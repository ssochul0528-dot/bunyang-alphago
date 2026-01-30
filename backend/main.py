from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Bunyang AlphaGo Debug Server",
        "port": os.getenv("PORT", "unknown")
    }

@app.get("/search-sites")
def search(q: str = ""):
    # 테스트용 데이터
    return [
        {"id": "test1", "name": "테스트 현장 (서버 연결됨)", "address": "서울특별시 강남구", "brand": "테스트", "status": "정상"}
    ]

# 상세 데이터 요청도 일단 빈 데이터로 응답하게 함
@app.get("/site-details/{site_id}")
def details(site_id: str):
    return {"id": site_id, "name": "테스트 상세", "address": "테스트 주소"}
