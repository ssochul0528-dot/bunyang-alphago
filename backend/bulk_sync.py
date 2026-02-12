#!/usr/bin/env python3
"""
전국 분양 데이터 대량 수집 스크립트
네이버 부동산 API에서 전국의 분양 현장 데이터를 수집하여 DB에 저장
"""

import asyncio
import httpx
import random
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

class Site(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    
    id: str = Field(primary_key=True)
    name: str
    address: str
    brand: Optional[str] = None
    category: str
    price: float
    target_price: float
    supply: int
    status: Optional[str] = None
    last_updated: datetime.datetime = Field(default_factory=datetime.datetime.now)

# 전국 주요 지역 키워드
REGIONS = [
    # 서울
    "강남", "서초", "송파", "강동", "마포", "용산", "성동", "광진", "동대문", "중랑",
    "성북", "강북", "도봉", "노원", "은평", "서대문", "종로", "중구", "영등포", "동작",
    "관악", "서초", "강서", "양천", "구로", "금천",
    
    # 경기
    "수원", "성남", "고양", "용인", "부천", "안산", "안양", "남양주", "화성", "평택",
    "의정부", "시흥", "파주", "김포", "광명", "광주", "군포", "하남", "오산", "양주",
    "구리", "안성", "포천", "의왕", "여주", "동두천", "과천",
    
    # 인천
    "인천", "부평", "계양", "서구", "남동", "연수", "중구", "동구", "미추홀",
    
    # 대전/세종/충청
    "대전", "세종", "청주", "천안", "충주", "제천", "아산", "공주", "보령", "서산",
    
    # 대구/경북
    "대구", "포항", "경주", "구미", "영천", "경산", "안동", "김천",
    
    # 부산/울산/경남
    "부산", "울산", "창원", "김해", "양산", "진주", "거제", "통영", "사천", "밀양",
    
    # 광주/전라
    "광주", "전주", "익산", "군산", "목포", "여수", "순천", "나주",
    
    # 강원
    "춘천", "원주", "강릉", "동해", "속초", "삼척"
]

# 주요 건설사/브랜드
BRANDS = [
    "힐스테이트", "자이", "푸르지오", "e편한세상", "롯데캐슬", "아이파크",
    "더샵", "래미안", "센트럴", "SK뷰", "호반베르디움", "포레나",
    "디에트르", "써밋", "해링턴", "위브", "꿈에그린", "한화포레나",
    "두산위브", "코오롱하늘채", "현대", "대우", "GS건설", "포스코"
]

# 기타 검색 키워드
KEYWORDS = [
    "아파트", "오피스텔", "지식산업센터", "상가", "분양", "미분양",
    "선착순", "지역주택조합", "재개발", "재건축", "신축", "입주"
]

async def fetch_with_retry(client, url, params, headers, max_retries=3):
    """재시도 로직이 포함된 HTTP 요청"""
    for attempt in range(max_retries):
        try:
            response = await client.get(url, params=params, headers=headers, timeout=15.0)
            if response.status_code == 200:
                return response
            elif response.status_code == 302:
                logger.warning(f"Redirect detected for keyword: {params.get('keyword')}")
                await asyncio.sleep(1 + attempt)
            else:
                logger.warning(f"Status {response.status_code} for keyword: {params.get('keyword')}")
        except Exception as e:
            logger.error(f"Request failed (attempt {attempt + 1}): {e}")
            await asyncio.sleep(1 + attempt)
    return None

async def collect_data():
    """전국 분양 데이터 수집"""
    SQLModel.metadata.create_all(engine)
    
    total_count = 0
    new_count = 0
    
    # 모든 검색 키워드 조합
    all_keywords = REGIONS + BRANDS + KEYWORDS
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for idx, keyword in enumerate(all_keywords):
            try:
                logger.info(f"[{idx+1}/{len(all_keywords)}] Searching: {keyword}")
                
                # 랜덤 쿠키 생성
                fake_nnb = "".join(random.choices("0123456789ABCDEF", k=16))
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Referer": "https://m.land.naver.com/",
                    "Origin": "https://m.land.naver.com",
                    "Cookie": f"NNB={fake_nnb}",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site"
                }
                
                url = "https://isale.land.naver.com/iSale/api/complex/searchList"
                params = {
                    "keyword": keyword,
                    "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH",
                    "salesStatus": "0:1:2:3:4:5:6:7:8:9:10:11:12",
                    "pageSize": "100"
                }
                
                response = await fetch_with_retry(client, url, params, headers)
                
                if response and response.status_code == 200:
                    try:
                        data = response.json()
                        items = data.get("result", {}).get("list", [])
                        
                        if items:
                            logger.info(f"  Found {len(items)} items for '{keyword}'")
                            
                            with Session(engine) as session:
                                for item in items:
                                    total_count += 1
                                    site_id = f"extern_isale_{item.get('complexNo')}"
                                    
                                    existing = session.get(Site, site_id)
                                    if not existing:
                                        new_site = Site(
                                            id=site_id,
                                            name=item.get("complexName", ""),
                                            address=item.get("address", ""),
                                            brand=item.get("h_name"),
                                            category=item.get("complexTypeName", "부동산"),
                                            price=1900.0,
                                            target_price=2200.0,
                                            supply=item.get("totalHouseholdCount", 500),
                                            status=item.get("salesStatusName")
                                        )
                                        session.add(new_site)
                                        new_count += 1
                                    else:
                                        # 기존 데이터 업데이트
                                        existing.status = item.get("salesStatusName")
                                        existing.last_updated = datetime.datetime.now()
                                
                                session.commit()
                        else:
                            logger.info(f"  No results for '{keyword}'")
                    except Exception as e:
                        logger.error(f"  Error processing data for '{keyword}': {e}")
                
                # API 호출 간격 (너무 빠르면 차단될 수 있음)
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
            except Exception as e:
                logger.error(f"Error with keyword '{keyword}': {e}")
                continue
    
    logger.info(f"\n{'='*60}")
    logger.info(f"수집 완료!")
    logger.info(f"총 발견: {total_count}개")
    logger.info(f"신규 추가: {new_count}개")
    logger.info(f"{'='*60}")
    
    return {"total": total_count, "new": new_count}

if __name__ == "__main__":
    print("전국 분양 데이터 수집을 시작합니다...")
    print("이 작업은 5-10분 정도 소요될 수 있습니다.\n")
    
    result = asyncio.run(collect_data())
    
    print(f"\n완료! 총 {result['new']}개의 새로운 현장이 추가되었습니다.")
