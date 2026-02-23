import httpx
import asyncio
import json

async def check_api_structure(keyword):
    fake_nnb = "1234567890ABCDEF"
    h = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://m.land.naver.com/",
        "Origin": "https://m.land.naver.com",
        "Cookie": f"NNB={fake_nnb}"
    }
    url = "https://isale.land.naver.com/iSale/api/complex/searchList"
    params = {
        "keyword": keyword, 
        "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH", 
        "salesStatus": "0:1:2:3:4:5:6:7:8:9:10:11:12", 
        "pageSize": "5"
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            res = await client.get(url, params=params, headers=h, timeout=5.0)
            print(f"Status: {res.status_code}")
            if res.status_code == 200:
                print("Raw Response Fragment:", res.text[:200])
                try:
                    data = res.json()
                    print("Keys:", data.keys())
                    if "result" in data:
                        print("result keys:", data["result"].keys())
                except:
                    print("Failed to parse JSON")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(check_api_structure("이안"))
