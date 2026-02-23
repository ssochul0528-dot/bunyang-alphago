import httpx
import asyncio
import datetime

async def test_webhook():
    url = "https://script.google.com/macros/s/AKfycbzZLa5HVuEdHpoD3ip6908XGyagJFsfsfJAmlfxLOekrqad0625QbYV4TLai4xHswwDfw/exec"
    payload = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": "연결 테스트",
        "phone": "010-0000-0000",
        "rank": "시스템",
        "site": "서버 테스트 현장",
        "source": "시스템 테스트"
    }
    
    print(f"Sending test payload to: {url}")
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(url, json=payload, timeout=10.0)
            print(f"Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")
            if "Success" in response.text or response.status_code == 200:
                print("✅ 성공: 구글 시트와 정상적으로 연결되었습니다!")
            else:
                print("❌ 실패: 응답은 왔으나 내용이 예상과 다릅니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(test_webhook())
