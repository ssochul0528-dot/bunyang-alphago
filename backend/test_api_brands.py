import httpx
import asyncio
import json

async def test_search(keyword):
    h = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    url = "https://isale.land.naver.com/iSale/api/complex/searchList"
    params = {
        "keyword": keyword, 
        "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH", 
        "salesStatus": "0:1:2:3:4:5:6:7:8:9:10:11:12", 
        "pageSize": "10"
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            res = await client.get(url, params=params, headers=h, timeout=5.0)
            print(f"Keyword: {keyword}, Status: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                print(f"Count: {len(data.get('complexList', []))}")
                for item in data.get('complexList', [])[:3]:
                    print(f" - {item.get('complexName')} ({item.get('salesStatusName')})")
            else:
                print(f"Error output: {res.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

async def main():
    await test_search("이안")
    await test_search("엘리움")

if __name__ == "__main__":
    asyncio.run(main())
