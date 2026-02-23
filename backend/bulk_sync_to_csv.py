import asyncio
import httpx
import csv
import os
import random
import time
from sqlmodel import Session, select
from main import engine, Site, create_db_and_tables

async def sync_all_industrial():
    print("🚀 Starting INDUSTRIAL Full-Coverage Sync (200+ Regional Scans)")
    create_db_and_tables()
    
    # 1. More granular Regional Keywords (Si/Gun/Gu)
    seoul = ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"]
    gyeonggi = ["수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시", "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시", "의왕시", "하남시", "용인시", "파주시", "이천시", "안성시", "김포시", "화성시", "광주시", "양주시", "포천시", "여주시"]
    incheon = ["미추홀구", "연수구", "남동구", "부평구", "계양구", "인천 서구", "영종도"]
    busan = ["부산진구", "동래구", "해운대구", "사하구", "강서구", "연제구", "수영구", "기장군"]
    other_major = ["천안", "청주", "전주", "창원", "포항", "구미", "김해", "순천", "여수", "원주", "춘천", "제주", "세종"]
    
    marketing = ["분양중", "분양예정", "미분양", "선착순", "잔여세대", "민간임대"]

    keywords = sorted(list(set(seoul + gyeonggi + incheon + busan + other_major + marketing)))
    
    # 2. Random User-Agents
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
    ]
    
    print(f"Plan: {len(keywords)} keywords to scan.")
    
    new_count = 0
    total_found = 0
    
    async with httpx.AsyncClient(follow_redirects=False) as client:
        for i, kw in enumerate(keywords):
            try:
                print(f"[{i+1}/{len(keywords)}] {kw}:", end=" ", flush=True)
                
                # Randomized Delay to mimic human
                await asyncio.sleep(random.uniform(1.5, 3.5)) 
                
                fake_nnb = "".join(random.choices("0123456789abcdef", k=16))
                ua = random.choice(uas)
                h = {
                    "User-Agent": ua,
                    "Cookie": f"NNB={fake_nnb}",
                    "Referer": "https://isale.land.naver.com/"
                }
                
                url = "https://isale.land.naver.com/iSale/api/complex/searchList"
                params = {
                    "keyword": kw, 
                    "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH", 
                    "salesStatus": "0:1:2:3:4:5:6:7:8:9:10:11:12", 
                    "pageSize": "100"
                }
                
                res = await client.get(url, params=params, headers=h, timeout=10.0)
                
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("result", {}).get("list", [])
                    total_found += len(items)
                    
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
                                    price=1900.0, target_price=2200.0, supply=500, 
                                    status=it.get("salesStatusName")
                                ))
                                new_count += 1
                                added += 1
                        session.commit()
                        print(f"{len(items)} items ({added} new).")
                elif res.status_code == 302:
                    print("Blocked (302).")
                    await asyncio.sleep(10) # Heavy sleep if blocked
                else:
                    print(f"Error {res.status_code}.")
                
            except Exception as e:
                print(f"Fail: {e}")

    # Export all sites to CSV
    print(f"\n📝 Exporting {total_found} cumulative items to CSV...")
    with Session(engine) as session:
        all_sites = session.exec(select(Site)).all()
        with open("sites_data.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "address", "brand", "category", "price", "target_price", "supply", "down_payment", "interest_benefit", "status"])
            for s in all_sites:
                writer.writerow([s.id, s.name, s.address, s.brand, s.category, s.price, s.target_price, s.supply, s.down_payment or "10%", s.interest_benefit or "무이자", s.status])
    
    print(f"✅ Industrial Sync Complete. Total {len(all_sites)} unique sites in DB.")

if __name__ == "__main__":
    asyncio.run(sync_all_industrial())
