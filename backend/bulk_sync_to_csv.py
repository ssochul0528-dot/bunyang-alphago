import asyncio
import httpx
import csv
import os
import random
from sqlmodel import Session, select
from main import engine, Site, create_db_and_tables

async def sync_and_save_to_csv():
    print("🚀 Starting Global Site Sync & CSV Export (Weekly Update Mode)")
    create_db_and_tables()
    
    keywords = [
        "래미안", "힐스테이트", "푸르지오", "e편한세상", "자이", "더샵", "롯데캐슬", "SK뷰", "아이파크",
        "포레나", "호반", "데시앙", "하늘채", "스위첸", "리슈빌", "더플래티넘", "센트레빌", "비발디", "금호어울림", 
        "제일풍경채", "중흥", "반도유보라", "디에트르", "우미린", "두산위브", "라인건설", "양우내안애", 
        "서희스타힐스", "한신더휴", "동문굿모닝힐", "이수건설", "한림풀에버", "동일플라워", "라온프라이빗", 
        "이지더원", "삼정그린코아", "유보라", "민간임대", "공공지원", "분양중", "분양예정", "선착순", 
        "미분양", "잔여세대", "발기인모집", "지역주택조합", "지주택", "해링턴", "써밋", "디에트르", 
        "이안", "엘리움", "파라곤", "아너스빌", "수자인", "베르디움"
    ]
    
    new_count = 0
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for kw in keywords:
            try:
                print(f"Scanning: {kw}...", end=" ", flush=True)
                fake_nnb = "".join(random.choices("0123456789ABCDEF", k=16))
                h = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Cookie": f"NNB={fake_nnb}"
                }
                url = "https://isale.land.naver.com/iSale/api/complex/searchList"
                params = {
                    "keyword": kw, 
                    "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH", 
                    "salesStatus": "0:1:2:3:4:5:6:7:8:9:10:11:12", 
                    "pageSize": "100"
                }
                res = await client.get(url, params=params, headers=h, timeout=12.0)
                
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("result", {}).get("list", [])
                    with Session(engine) as session:
                        added = 0
                        for it in items:
                            sid = f"extern_isale_{it.get('complexNo')}"
                            if not session.get(Site, sid):
                                session.add(Site(
                                    id=sid, 
                                    name=it.get("complexName"), 
                                    address=it.get("address"),
                                    brand=it.get("h_name"), 
                                    category=it.get("complexTypeName", "부동산"),
                                    price=1900.0, 
                                    target_price=2200.0, 
                                    supply=500, 
                                    status=it.get("salesStatusName")
                                ))
                                new_count += 1
                                added += 1
                        session.commit()
                        print(f"Found {len(items)} items, Added {added} new.")
                else:
                    print(f"Error {res.status_code}")
                
                await asyncio.sleep(1.5) # Anti-blocking delay
            except Exception as e:
                print(f"Failed: {e}")

    # Export all sites to CSV
    print("\n📝 Exporting all data to sites_data.csv...")
    with Session(engine) as session:
        all_sites = session.exec(select(Site)).all()
        
        with open("sites_data.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "address", "brand", "category", "price", "target_price", "supply", "down_payment", "interest_benefit", "status"])
            for s in all_sites:
                writer.writerow([
                    s.id, s.name, s.address, s.brand, s.category, 
                    s.price, s.target_price, s.supply, 
                    s.down_payment or "10%", s.interest_benefit or "무이자", 
                    s.status
                ])
    
    print(f"✅ Sync Complete. Total {len(all_sites)} sites saved to CSV.")

if __name__ == "__main__":
    asyncio.run(sync_and_save_to_csv())
