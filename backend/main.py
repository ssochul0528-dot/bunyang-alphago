from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/search-sites")
def search(q: str = ""):
    return [{"id": "s1", "name": f"연결됨: {q}", "address": "의정부"}]

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    # We use 0.0.0.0 and the port from environment
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="debug")
