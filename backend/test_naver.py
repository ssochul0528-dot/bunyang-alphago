import httpx
import json

async def test():
    search_url = "https://new.land.naver.com/api/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://new.land.naver.com/"
    }
    params = {"keyword": "힐스테이트"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(search_url, params=params, headers=headers)
            print(f"Status: {response.status_code}")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())
