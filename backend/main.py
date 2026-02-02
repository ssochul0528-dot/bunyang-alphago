from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
import logging

# Extreme logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("railway_test")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health(request: Request):
    logger.info(f"Health check from {request.client.host}")
    return {"status": "ok", "port": os.getenv("PORT", "unknown")}

@app.get("/search-sites")
async def search(q: str = ""):
    logger.info(f"Search request for: {q}")
    # Very simple response to avoid any serialization issues
    return [
        {"id": "s1", "name": "힐스테이트 회룡역 파크뷰", "address": "의정부", "status": "연결됨"},
        {"id": "debug", "name": f"'{q}' 검색 성공", "address": "시스템 정상"}
    ]

# If Railway uses Nixpacks, it might try to run uvicorn main:app directly.
# If it uses our Procfile 'python main.py', it runs this:
if __name__ == "__main__":
    # Get port from environment, or default to 8080 (Railway default)
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
