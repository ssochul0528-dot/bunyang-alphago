import httpx
import json

async def test_search(q):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://new.land.naver.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        # Try new.land API
        print(f"--- Searching [{q}] on new.land.naver.com/api/search ---")
        try:
            res1 = await client.get("https://new.land.naver.com/api/search", params={"keyword": q}, timeout=5.0)
            print(f"Status: {res1.status_code}")
            if res1.status_code == 200:
                data = res1.json()
                complexes = data.get("complexes", [])
                print(f"Found {len(complexes)} complexes")
                for c in complexes[:3]:
                    print(f" - {c.get('complexName')} ({c.get('provinceName')} {c.get('cityName')})")
            else:
                print(f"Error Body: {res1.text[:200]}")
        except Exception as e:
            print(f"Error res1: {e}")

        # Try ac.land API
        print(f"\n--- Searching [{q}] on ac.land.naver.com/ac ---")
        try:
            ac_params = {"q": q, "st": "10", "r_format": "json", "t_nm": "land", "q_enc": "utf-8", "r_enc": "utf-8"}
            res2 = await client.get("https://ac.land.naver.com/ac", params=ac_params, timeout=5.0)
            print(f"Status: {res2.status_code}")
            if res2.status_code == 200:
                data = res2.json()
                items = data.get("items", [])
                if items and items[0]:
                    print(f"Found {len(items[0])} items")
                    for i in items[0][:3]:
                        print(f" - {i[0]} ({i[1][0] if i[1] else ''})")
            else:
                print(f"Error Body: {res2.text[:200]}")
        except Exception as e:
            print(f"Error res2: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search("강남"))
    print("\n" + "="*50 + "\n")
    asyncio.run(test_search("힐스테이트"))
