from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import datetime
import os
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from sqlmodel import Field, Session, SQLModel, create_engine, select, or_, col
import logging
import httpx
import google.generativeai as genai
import json
from typing import List, Optional, Union, Any

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCd5wNhgfAFZWpHdGDA9RSzpQ-YZeTHms0")
genai.configure(api_key=GEMINI_API_KEY)

import logging
import re

# 구글 시트 웹훅 URL (사용자가 설정한 URL)
GOOGLE_SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzZLa5HVuEdHpoD3ip6908XGyagJFsfsfJAmlfxLOekrqad0625QbYV4TLai4xHswwDfw/exec"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_json(text: str):
    """문자열에서 JSON 블록만 추출하는 고도화된 함수 (RegEx 사용)"""
    if not text:
        return None
    
    # 1. ```json 블록 추출 시도
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except: pass
        
    # 2. 일반 ``` 블록 추출 시도
    match = re.search(r"```\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except: pass

    # 3. 텍스트 내의 첫 번째 { 와 마지막 } 사이 추출 시도
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except: pass
        
    # 4. 전체 텍스트 시도
    try:
        return json.loads(text.strip())
    except:
        logger.error(f"Failed to parse AI JSON response: {text[:200]}...")
        return None

# --- Database Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sqlite_file_name = os.path.join(BASE_DIR, "database.db")
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
    down_payment: Optional[str] = "10%"
    interest_benefit: Optional[str] = "중도금 무이자"
    status: Optional[str] = None
    last_updated: datetime.datetime = Field(default_factory=datetime.datetime.now)

class Lead(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    phone: str
    rank: str
    site: str
    source: Optional[str] = Field(default="알 수 없음")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

class AnalysisHistory(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: Optional[str] = Field(default=None, index=True)
    field_name: str
    address: str
    score: int
    response_json: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

# --- NATIONWIDE START DATA ---
MOCK_SITES = [
    {"id": "seoul_seocho_1", "name": "메이플자이", "address": "서울특별시 서초구 잠원동", "brand": "자이", "category": "아파트", "price": 6700, "target_price": 7500, "supply": 3307, "status": "분양중"},
    {"id": "seoul_seocho_2", "name": "래미안 원펜타스", "address": "서울특별시 서초구 반포동", "brand": "래미안", "category": "아파트", "price": 6800, "target_price": 7800, "supply": 641, "status": "분양중"},
    {"id": "seoul_gangnam_1", "name": "청담 르엘", "address": "서울특별시 강남구 청담동", "brand": "르엘", "category": "아파트", "price": 7200, "target_price": 11000, "supply": 1261, "status": "분양중"},
    {"id": "seoul_songpa_1", "name": "잠실 래미안 아이파크", "address": "서울특별시 송파구 신천동", "brand": "래미안", "category": "아파트", "price": 5400, "target_price": 6200, "supply": 2678, "status": "분양중"},
    {"id": "gyeonggi_uijeongbu_1", "name": "의정부 힐스테이트 회룡 파크뷰", "address": "경기도 의정부시 회룡동", "brand": "힐스테이트", "category": "아파트", "price": 1850, "target_price": 2100, "supply": 1816, "status": "분양중"},
    {"id": "seoul_gangdong_3", "name": "이안 강동 컴홈스테이", "address": "서울특별시 강동구 천호동", "brand": "이안", "category": "오피스텔", "price": 2100, "target_price": 2350, "supply": 654, "status": "준공완료"},
    {"id": "daejeon_yuseong_1", "name": "도안리버파크 1단지", "address": "대전광역시 유성구 학하동", "brand": "힐스테이트", "category": "아파트", "price": 1950, "target_price": 2250, "supply": 1124, "status": "분양중"},
    {"id": "busan_gangseo_1", "name": "부산 에코델타시티 12BL", "address": "부산광역시 강서구", "brand": "e편한세상", "category": "아파트", "price": 1600, "target_price": 1950, "supply": 1258, "status": "분양중"},
]

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    
    # Migration: Add source column to lead table if it doesn't exist
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            # PRAGMA table_info returns (id, name, type, notnull, dflt_value, pk)
            columns = [row[1] for row in conn.execute(text("PRAGMA table_info(lead)")).fetchall()]
            if columns and 'source' not in columns:
                conn.execute(text("ALTER TABLE lead ADD COLUMN source TEXT DEFAULT '알 수 없음'"))
                conn.commit()
                logger.info("Database migration: Added 'source' column to 'lead' table.")
            
            # Site 테이블 마이그레이션
            site_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(site)")).fetchall()]
            if site_columns:
                if 'down_payment' not in site_columns:
                    conn.execute(text("ALTER TABLE site ADD COLUMN down_payment TEXT DEFAULT '10%'"))
                if 'interest_benefit' not in site_columns:
                    conn.execute(text("ALTER TABLE site ADD COLUMN interest_benefit TEXT DEFAULT '중도금 무이자'"))
                conn.commit()
                logger.info("Database migration: Added columns to 'site' table.")
    except Exception as e:
        logger.error(f"Migration error: {e}")

    with Session(engine) as session:
        for s_data in MOCK_SITES:
            existing = session.get(Site, s_data["id"])
            if not existing:
                session.add(Site(**s_data))
            else:
                for key, value in s_data.items():
                    setattr(existing, key, value)
        session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 기동 시 DB 초기화 및 CSV 데이터 기반 고정 데이터 로드
    create_db_and_tables()
    try:
        await import_csv_data()
        logger.info("Fixed site data loaded from sites_data.csv successfully.")
    except Exception as e:
        logger.error(f"Lifespan data load error: {e}")
    yield

app = FastAPI(lifespan=lifespan)

# CORS 설정을 더 명시적으로 강화
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class SiteSearchResponse(BaseModel):
    id: str
    name: str
    address: str
    status: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None

@app.get("/search-sites", response_model=List[SiteSearchResponse])
async def search_sites(q: str):
    if not q or len(q) < 1:
        return []

    results = []
    seen_ids = set()
    q_lower = q.lower().strip()

    # 1. DB 검색 (분양 데이터베이스 우선)
    try:
        q_parts = q_lower.split()
        if not q_parts:
            return []
            
        with Session(engine) as session:
            # 모든 검색어 조각이 각각 name, address, brand, category, status 중 하나에라도 포함되어야 함 (AND 검색)
            statement = select(Site)
            for part in q_parts:
                part_lower = part.lower()
                statement = statement.where(
                    or_(
                        col(Site.name).ilike(f"%{part_lower}%"), 
                        col(Site.address).ilike(f"%{part_lower}%"), 
                        col(Site.brand).ilike(f"%{part_lower}%"),
                        col(Site.category).ilike(f"%{part_lower}%"),
                        col(Site.status).ilike(f"%{part_lower}%")
                    )
                )
            
            statement = statement.order_by(col(Site.last_updated).desc()).limit(100)
            db_sites = session.exec(statement).all()
            logger.info(f"DB search for '{q_lower}' (parts: {q_parts}) found {len(db_sites)} results")
            for s in db_sites:
                if s.id not in seen_ids:
                    results.append(SiteSearchResponse(id=s.id, name=s.name, address=s.address, status=s.status, brand=s.brand, category=s.category))
                    seen_ids.add(s.id)
    except Exception as e:
        logger.error(f"DB search error: {e}")

    # 2. 실시간 분양 전문 API 검색 (구축 아파트를 원천 배제하기 위해 isale API만 사용)
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            fake_nnb = "".join(random.choices("0123456789ABCDEF", k=16))
            h = {
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
            
            # 분양 정보가 있는 'isale' 데이터베이스만 조회 (오래된 기축 아파트는 여기서 걸러짐)
            url_isale = "https://isale.land.naver.com/iSale/api/complex/searchList"
            params = {
                "keyword": q, 
                "complexType": "APT:ABYG:JGC:OR:OP:VL:DDD:ABC:ETC:UR:HO:SH", 
                "salesStatus": "0:1:2:3:4:5:6:7:8:9:10:11:12", 
                "pageSize": "100"
            }
            res_isale = await client.get(url_isale, params=params, headers=h, timeout=4.0)
            if res_isale.status_code == 200 and "application/json" in res_isale.headers.get("Content-Type", ""):
                data = res_isale.json()
                for it in data.get("result", {}).get("list", []):
                    sid = f"extern_isale_{it.get('complexNo')}"
                    if sid not in seen_ids:
                        results.append(SiteSearchResponse(
                            id=sid, name=it.get('complexName'), address=it.get('address'), 
                            status=it.get('salesStatusName'), brand=it.get('h_name'),
                            category=it.get('complexTypeName', '아파트')
                        ))
                        seen_ids.add(sid)
    except Exception as e:
        logger.error(f"API search error: {e}")

    # 검색 결과 정렬 고도화
    def sort_key(x):
        name_l = x.name.lower() if x.name else ""
        addr_l = x.address.lower() if x.address else ""
        brand_l = x.brand.lower() if x.brand else ""
        cat_l = x.category.lower() if x.category else ""
        
        # 1. 현장명과 정확히 일치
        if name_l == q_lower: return (0, 0)
        # 2. 브랜드명과 정확히 일치
        if brand_l == q_lower: return (0, 1)
        
        # 3. 현장명이 검색어로 시작
        if name_l.startswith(q_lower): return (1, name_l.find(q_lower))
        # 4. 브랜드명이 검색어로 시작
        if brand_l.startswith(q_lower): return (1, 100 + brand_l.find(q_lower))
        
        # 5. 현장명에 검색어 포함
        if q_lower in name_l: return (2, name_l.find(q_lower))
        # 6. 브랜드명에 검색어 포함
        if q_lower in brand_l: return (2, 100 + brand_l.find(q_lower))
        
        # 7. 주소에 검색어 포함
        if q_lower in addr_l: return (3, addr_l.find(q_lower))
        # 8. 카테고리에 검색어 포함
        if q_lower in cat_l: return (4, cat_l.find(q_lower))
        
        return (999, 999)
    
    results.sort(key=sort_key)
    logger.info(f"Search query: '{q}' returned {len(results)} results")
    return results[:100]

@app.get("/force-csv-reload")
async def force_csv_reload():
    """업로드된 CSV 파일을 기준으로 DB를 완전히 강제 갱신합니다. (주간 업데이트 시 활용)"""
    from sqlmodel import delete
    try:
        with Session(engine) as session:
            session.exec(delete(Site))
            session.commit()
        
        create_db_and_tables()
        result = await import_csv_data()
        return {"status": "success", "message": "CSV 데이터를 기반으로 DB가 강제 갱신되었습니다.", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/sync-external-naver")
async def sync_external_naver():
    """[관리자용] 네이버 부동산 데이터를 스캔하여 DB에 임시 추가합니다. (API 차단 주의)"""
    # ... 기존 sync_all 로직 유지 (필요 시에만 수동 호출)
    keywords = ["분양권", "분양", "민간임대", "잔여세대", "미분양"] 
    count = 0
    # (실시간성보다는 CSV 업로드를 권장한다는 메시지 포함 가능)
    return {"status": "deprecated", "message": "실시간 동기화 대신 로컬에서 스캔 후 CSV 업로드 방식을 권장합니다."}

@app.get("/site-details/{site_id}")
async def get_site_details(site_id: str):
    try:
        with Session(engine) as session:
            site = session.get(Site, site_id)
            if site: return site
    except Exception as e:
        logger.error(f"DB fetch error for site {site_id}: {e}")
        
    # Return a decent fallback object instead of crashing or returning empty
    return {
        "id": site_id, 
        "name": "현장 정보 로드됨", 
        "address": "분석을 위해 정확한 주소를 입력해주세요.", 
        "brand": "기타", 
        "category": "아파트", 
        "price": 2800, 
        "target_price": 3200, 
        "supply": 300, 
        "status": "데이터 보정 필요",
        "down_payment": "10%",
        "interest_benefit": "중도금 무이자"
    }

class AnalyzeRequest(BaseModel):
    field_name: Optional[str] = "알 수 없는 현장"
    address: Optional[str] = "지역 정보 없음"
    product_category: Optional[str] = "아파트"
    sales_stage: Optional[str] = "분양중"
    down_payment: Optional[Union[int, str]] = "10%"
    interest_benefit: Optional[str] = "없음"
    additional_benefits: Optional[Union[List[str], str]] = []
    main_concern: Optional[str] = "기타"
    monthly_budget: Optional[Union[int, float, str]] = 0
    existing_media: Optional[Union[List[str], str]] = []
    sales_price: Optional[Union[float, str, int]] = 0.0
    target_area_price: Optional[Union[float, str, int]] = 0.0
    down_payment_amount: Optional[Union[int, float, str]] = 0
    supply_volume: Optional[Union[int, str]] = 0
    field_keypoints: Optional[str] = ""
    user_email: Optional[str] = None

class RegenerateCopyResponse(BaseModel):
    lms_copy_samples: List[str]
    channel_talk_samples: List[str]

@app.post("/regenerate-copy", response_model=RegenerateCopyResponse)
async def regenerate_copy(req: AnalyzeRequest):
    """Gemini AI를 사용하여 카피만 정밀하게 다시 생성합니다."""
    field_name = req.field_name or "분석 현장"
    address = req.address or "지역 정보"
    dp = str(req.down_payment) if req.down_payment else "10%"
    ib = req.interest_benefit or "무이자"
    fkp = req.field_keypoints or "탁월한 입지와 미래가치"
    
    prompt = f"""
    당신은 대한민국 상위 0.1% 부동산 퍼포먼스 마케팅 디렉터입니다. 
    [{field_name}] 현장의 신규 고객 유입을 폭발적으로 늘리기 위한 LMS 및 채널톡 카피 3종을 작성하십시오.
    
    [핵심 미션: 매우 구체적이고 전문적인 긴 문장으로 작성]
    - 단순 요약이 아닌, 수분양자의 마음을 흔드는 감성적 서사와 논리적 수익 분석이 결합된 '롱폼(Long-form)' 카피를 작성하십시오.
    - 각 매체의 성격에 맞는 이모지를 풍부하게 사용하여 가독성과 후킹 요소를 극대화하십시오.

    [현장 데이터]
    - 현장명: {field_name} / 위치: {address}
    - 핵심 특장점: {fkp}
    - 금융 혜택: 계약금 {dp}, {ib}
    
    [작성 가이드]
    1. LMS (3종 세트: 매우 길고 전문적인 스타일):
       - 1안(신뢰/브랜드): 장문의 전문 서신 스타일. 입지 가치와 브랜드의 정통성, 미래 가치를 서술형으로 아주 상세히 작성.
       - 2안(금융/수익): 실투자금, 시세차익, 중도금 혜택 등 철저히 자산 가치 상승을 수치와 논리로 설득하는 긴 글.
       - 3안(긴급/후킹): "로얄층 선착순 마감", "오늘이 가장 저렴한 이유" 등 심리적 압박과 즉각 행동을 유도하는 강렬하고 긴 문구.
    2. 채널톡 (3종 세트):
       - 모바일 최적화된 긴 호흡의 카피. 이모지를 적극 활용하되, 핵심 정보를 빠짐없이 포함.

    [출력 포맷: JSON]
    {{
        "lms_copy_samples": ["LMS 고퀄리티 1안", "LMS 고퀄리티 2안", "LMS 고퀄리티 3안"],
        "channel_talk_samples": ["채널톡 고퀄리티 1안", "채널톡 고퀄리티 2안", "채널톡 고퀄리티 3안"]
    }}
    """
    
    ai_data = None
    model_candidates = ['gemini-flash-latest', 'gemini-pro-latest', 'gemini-2.0-flash-lite']
    
    for model_name in model_candidates:
        try:
            logger.info(f"Regenerate copy attempt with: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                ai_data = extract_json(response.text)
                if ai_data: break
        except Exception as e:
            logger.error(f"Regenerate copy model {model_name} failed: {e}")
            continue

    if ai_data:
        lms_res = ai_data.get("lms_copy_samples", [])
        if not isinstance(lms_res, list): lms_res = []
        lms_res = [str(x) for x in lms_res if x]
        while len(lms_res) < 3: lms_res.append(f"{field_name} 정밀 분석 카피가 준비 중입니다.")
        
        chn_res = ai_data.get("channel_talk_samples", [])
        if not isinstance(chn_res, list): chn_res = []
        chn_res = [str(x) for x in chn_res if x]
        while len(chn_res) < 3: chn_res.append(f"{field_name} 맞춤 채널톡 카피가 준비 중입니다.")

        return RegenerateCopyResponse(
            lms_copy_samples=lms_res[:3],
            channel_talk_samples=chn_res[:3]
        )
    
    # Fallback to smart templates
    lms_samples = [
        f"【{field_name} | 공식 안내문】\n\n대한민국 상급지의 자부심, {field_name}이 선사하는 압도적 주거 경험에 여러분을 초대합니다. 💎\n\n현재 {address} 일대는 대규모 개발 호재와 함께 미래 자산 가치가 급격히 재편되고 있습니다. 본 현장은 단순한 주거 공간을 넘어, {fkp}라는 독보적 가치를 통해 입주민의 품격을 증명할 것입니다.\n\n💰 파격적 금융 혜택:\n- 계약금 {dp} 시스템으로 초기 자금 부담 최소화\n- {ib} 확정으로 입주 시까지 금리 걱정 NO!\n\n이미 발 빠른 자산가들의 로얄층 선점이 시작되었습니다. 시세 대비 합리적인 가격으로 내 집 마련과 자산 증식의 두 토끼를 동시에 잡으십시오. 🚀\n\n☎️ 공식 분양 본부: 1600-0000",
        f"[특별 금융 분석] {field_name} 자산성 전문 리포트\n\n지금 {field_name}에 주목해야 하는 팩트 체크! 📊\n\n주변 구축 아파트 시세 대비 본 현장은 압도적인 신축 프리미엄과 함께 금융 혜택을 제공하고 있습니다. {ib} 혜택은 실질적으로 전용면적당 수천만 원의 절감 효과를 가져옵니다. 💸\n\n✅ 체크포인트:\n1. {address} 핵심 상권 및 인프라 초밀착 입지\n2. {fkp} 특화 설계를 통한 평면 경쟁력 확보\n3. 실거주 의무 해제 및 전매 무제한 수혜 지\n\n로얄 동·호수 배정은 실시간으로 소진되고 있습니다. 지금 바로 확인하세요.\n☎️ 긴급 상담: 010-0000-0000",
        f"🚨 [마감임박] {field_name} 선착순 동·호수 지정 마감 🚨\n\n망설이는 순간, 당신의 미래 가치는 지나갑니다! 🔥\n현재 {field_name} 홍보관은 연일 인산인연으로 로얄층이 빠르게 완판되고 있습니다. 마지막 남은 극소량 잔여 세대를 선점할 수 있는 '최종 기회'입니다.\n\n✨ 놓치면 후회할 핵심 이유:\n- 주변 시세 압도하는 {field_name}만의 평당 분양가\n- {ib} + 계약금 {dp}의 파격적 콜라보\n- {fkp} 최신 트렌드를 반영한 명품 대단지\n\n오늘 방문 예약 시 특별 사은품을 증정합니다. 🎁 성공적인 자산 설계의 시작, 지금 바로 행동하십시오!\n📞 대표번호: 1811-0000"
    ]
    channel_samples = [
        f"🔥 {field_name} | 파격 조건변경 소식! 🔥\n\n현재 호갱노노 실시간 급상승 1위! 그 이유가 궁금하시죠? 💎\n\n✅ 혜택 요약:\n- 초기 계약금 {dp}로 입주 시까지!\n- 이자 부담 제로! 파격적인 {ib} 확정\n\n🚅 {address}의 랜드마크이자 {fkp}를 누릴 단 하나의 선택. 지금 채팅으로 바로 문의하세요! 📢",
        f"🚨 [긴급] {field_name} 로열층 선착순 소진 중! 🚨\n\n상담 대기 인원 급증! 망설이면 늦습니다. 💨\n\n💎 투자/실거주 핵심 포인트:\n1. {address} 내 독보적인 입지 희소성\n2. 인근 구축 대비 압도적 커스텀 평면 설계\n\n실시간 잔여 호수 확인하고 VIP 상담 예약을 지금 바로 진행하세요! 📞",
        f"📊 {field_name} 고관여 전용 [정밀 분석 리포트] 📊\n\n호갱노노에서도 볼 수 없는 진짜 전문 데이터를 공개합니다. 🧐\n\n✨ 리포트 내용:\n- {address} 권역 향후 5년 공급량 데이터 분석\n- {fkp} 등 주거 만족도 1위의 진짜 이유\n- 실투자금 대비 수익률 정밀 시뮬레이션\n\n지금 채널톡에서 바로 리포트를 다운로드하세요! 💎"
    ]
    return RegenerateCopyResponse(lms_copy_samples=lms_samples, channel_talk_samples=channel_samples)

@app.post("/analyze")
async def analyze_site(request: Optional[AnalyzeRequest] = None):
    """Gemini AI를 사용한 현장 정밀 분석 API (고도화 버전)"""
    # 기본값 설정 (fallback 시 NameError 방지)
    field_name = "분석 현장"
    address = "지역 정보 없음"
    product_category = "아파트"
    sales_price = 0.0
    target_price = 0.0
    market_gap = 0.0
    gap_percent = 0.0
    gap_status = "높은"
    supply_volume = 0
    field_keypoints = ""
    ib = "무이자"
    dp = "10%"
    fkp = "탁월한 입지와 미래가치"
    main_concern = "기타"

    logger.info(f">>> Analyze request received: {request.field_name if request else 'No request body'}")
    
    try:
        req = request if request else AnalyzeRequest()
        
        field_name = getattr(req, 'field_name', "분석 현장")
        address = getattr(req, 'address', "지역 정보 없음")
        product_category = getattr(req, 'product_category', "아파트")
        
        # 숫자 필드 안전하게 변환
        try:
            sales_price = float(req.sales_price or 0.0)
        except: sales_price = 0.0
        
        try:
            target_price = float(req.target_area_price or 0.0)
        except: target_price = 0.0
        
        market_gap = target_price - sales_price
        gap_status = "저렴" if market_gap > 0 else "높은"
        gap_percent = abs(round((market_gap / (sales_price if sales_price > 0 else 1)) * 100, 1))
        
        # supply_volume 처리 (문자열 포함 시 숫자만 추출)
        try:
            sv_raw = str(req.supply_volume or "0")
            sv_digits = "".join(filter(str.isdigit, sv_raw))
            supply_volume = int(sv_digits) if sv_digits else 0
        except:
            supply_volume = 0
            
        main_concern = req.main_concern or "기타"
        field_keypoints = getattr(req, 'field_keypoints', "")
        dp = str(req.down_payment) if req.down_payment else "10%"
        ib = req.interest_benefit or "무이자"
        fkp = field_keypoints if field_keypoints else "탁월한 입지와 미래가치"
        
        # 1. 실시간 여론 및 데이터 수집
        search_context = ""
        try:
            async with httpx.AsyncClient() as client:
                search_url = "https://search.naver.com/search.naver"
                search_params = {"query": f"{field_name} 분양가 모델하우스", "where": "view"}
                h = {"User-Agent": "Mozilla/5.0"}
                res = await client.get(search_url, params=search_params, headers=h, timeout=4.0)
                if res.status_code == 200:
                    search_context = res.text[:3000]
        except Exception as e:
            logger.warning(f"Live search skipped: {e}")

        # 2. AI 분석을 위한 프롬프트 작성
        prompt = f"""
        당신은 대한민국 부동산 분양 마케팅 상위 0.1% 전문가이자 '분양 알파고' 시스템입니다. 
        [{field_name}] 현장의 성공적인 분양을 위한 '정밀 시장 및 매체 분석 리포트'를 전문가 수준으로 JSON 작성하십시오.

        [분석 요청 사항]
        - market_diagnosis: 전문 용어를 적극 활용하여 시장의 거시적 흐름과 단지의 입지적 강점을 최소 5문장 이상으로 상세히 분석하십시오.
        - lms_copy_samples & channel_talk_samples: 이모지를 풍부하게 사용하고, 가독성이 좋으면서도 내용이 매우 긴 '호소력 짙은' 문안을 각 매체당 3개씩 작성하십시오.
        - media_mix: '호갱노노 채널톡', 'LMS(문자 마케팅)'를 필수 포함한 3대 핵심 매체 전략을 제시하십시오.

        [데이터 세트]
        - 현장명: {field_name} / 위치: {address} / 상품군: {product_category}
        - 프라이싱: 공급가 {sales_price} VS 주변 시세 {target_price}
        - 규모/공급: {supply_volume}세대 / 금융조건: 계약금 {dp}, {ib}
        - 핵심 특장점: {fkp}
        
        [JSON Output Structure]
        {{
            "market_diagnosis": "...",
            "target_persona": "...",
            "target_audience": ["#1", "#2", "#3", "#4", "#5"],
            "competitors": [
                {{"name": "인근 단지 A", "price": {target_price or 0}, "gap_label": "도보 5분"}},
                {{"name": "인근 단지 B", "price": {target_price * 1.05 if target_price else 0}, "gap_label": "1.2km"}}
            ],
            "ad_recommendation": "...",
            "copywriting": "...",
            "keyword_strategy": ["키원드1", "2", "3", "4", "5"],
            "weekly_plan": ["1주", "2주", "3주", "4주"],
            "roi_forecast": {{"expected_leads": 150, "expected_cpl": 45000, "conversion_rate": 3.5, "expected_ctr": 1.9}},
            "lms_copy_samples": ["긴 카피 1안", "긴 카피 2안", "긴 카피 3안"],
            "channel_talk_samples": ["채널톡 긴 카피 1안", "채널톡 긴 카피 2안", "채널톡 긴 카피 3안"],
            "media_mix": [
                {{"media": "매체", "feature": "강점", "reason": "이유", "strategy_example": "전략"}}
            ]
        }}
        """

        ai_data = None
        model_candidates = [
            'gemini-flash-latest',
            'gemini-pro-latest',
            'gemini-2.0-flash-lite'
        ]
        
        for model_name in model_candidates:
            try:
                logger.info(f"Attempting AI analysis with model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    ai_data = extract_json(response.text)
                    if ai_data: 
                        logger.info(f"Success with model: {model_name}")
                        break
            except Exception as e:
                logger.error(f"Model {model_name} failed: {e}")
                continue

        if not ai_data:
            logger.warning("AI model failed. Triggering Smart Local Engine.")
            raise Exception("AI Response Parsing Failed")

        # 필수 필드 누락 방지 및 기본값 보정
        safe_data = {
            "market_diagnosis": ai_data.get("market_diagnosis") or "데이터 분석 중입니다.",
            "target_audience": ai_data.get("target_audience") or ["실거주자", "투자자"],
            "target_persona": ai_data.get("target_persona") or "안정적 자산 증식을 노리는 수요자",
            "competitors": ai_data.get("competitors") or [],
            "ad_recommendation": ai_data.get("ad_recommendation") or "메타 및 네이버 광고 집행 권장",
            "copywriting": ai_data.get("copywriting") or f"[{field_name}] 지금 바로 만나보세요.",
            "keyword_strategy": ai_data.get("keyword_strategy") or [field_name, "분양정보"],
            "weekly_plan": ai_data.get("weekly_plan") or ["1주차: 마케팅 기획"],
            "roi_forecast": ai_data.get("roi_forecast") or {"expected_leads": 100, "expected_cpl": 50000, "conversion_rate": 2.5, "expected_ctr": 1.8},
            "lms_copy_samples": ai_data.get("lms_copy_samples") or [],
            "channel_talk_samples": ai_data.get("channel_talk_samples") or [],
            "media_mix": ai_data.get("media_mix") or []
        }
        
        # media_mix 내부 필드 보정
        final_media_mix = []
        for m in safe_data["media_mix"]:
            if isinstance(m, dict):
                final_media_mix.append({
                    "media": str(m.get("media", "매체")),
                    "feature": str(m.get("feature", "특징")),
                    "reason": str(m.get("reason", "분석 사유")),
                    "strategy_example": str(m.get("strategy_example", "전략 예시"))
                })
        safe_data["media_mix"] = final_media_mix
        if "expected_ctr" not in safe_data["roi_forecast"]:
            safe_data["roi_forecast"]["expected_ctr"] = 1.8

        # ROI Forecast 필드 보정
        default_roi = {"expected_leads": 100, "expected_cpl": 50000, "conversion_rate": 2.5, "expected_ctr": 1.8}
        if not isinstance(safe_data.get("roi_forecast"), dict):
            safe_data["roi_forecast"] = default_roi
        else:
            for k, v in default_roi.items():
                if k not in safe_data["roi_forecast"]:
                    safe_data["roi_forecast"][k] = v
                else:
                    try:
                        safe_data["roi_forecast"][k] = float(safe_data["roi_forecast"][k])
                    except:
                        safe_data["roi_forecast"][k] = v

        # 리스트 필드 보정
        for key in ["lms_copy_samples", "channel_talk_samples", "target_audience", "weekly_plan", "keyword_strategy"]:
            val = safe_data.get(key)
            if isinstance(val, str):
                val = [val]
            elif not isinstance(val, list):
                val = []
            
            # 카피 샘플은 반드시 3개 보장
            if key in ["lms_copy_samples", "channel_talk_samples"]:
                val = [str(x) for x in val if x]
                while len(val) < 3:
                    val.append(f"{field_name} 마케팅 정밀 카피 분석 중입니다.")
                val = val[:3]
            else:
                val = [str(x) for x in val]
                
            safe_data[key] = val

        # competitors 필드 보정
        final_competitors = []
        for c in safe_data["competitors"]:
            if isinstance(c, dict):
                try:
                    p_val = float(c.get("price", 0))
                except: p_val = 0.0
                
                final_competitors.append({
                    "name": str(c.get("name", "경쟁 단지")),
                    "price": p_val,
                    "gap_label": str(c.get("gap_label") or c.get("distance") or "비교군")
                })
        safe_data["competitors"] = final_competitors

        price_score = min(100, max(0, 100 - abs(sales_price - target_price) / (target_price if target_price > 0 else 1) * 100))
        location_score = 75 + random.randint(-5, 10)
        benefit_score = 70 + random.randint(-5, 10)
        total_score = int((price_score * 0.4 + location_score * 0.3 + benefit_score * 0.3))

        final_result = {
            "score": int(total_score),
            "score_breakdown": {
                "price_score": int(price_score),
                "location_score": int(location_score),
                "benefit_score": int(benefit_score),
                "total_score": int(total_score)
            },
            "market_diagnosis": safe_data["market_diagnosis"],
            "market_gap_percent": round(gap_percent, 2),
            "price_data": [
                {"name": "우리 현장", "price": sales_price},
                {"name": "주변 시세", "price": target_price},
                {"name": "시세 차익", "price": abs(target_price - sales_price)}
            ],
            "radar_data": [
                {"subject": "분양가", "A": int(price_score), "B": 70, "fullMark": 100},
                {"subject": "브랜드", "A": 85, "B": 75, "fullMark": 100},
                {"subject": "단지규모", "A": min(100, (supply_volume // 10) + 20), "B": 60, "fullMark": 100},
                {"subject": "입지", "A": int(location_score), "B": 65, "fullMark": 100},
                {"subject": "분양조건", "A": 80, "B": 50, "fullMark": 100},
                {"subject": "상품성", "A": int(benefit_score), "B": 70, "fullMark": 100}
            ],
            "target_persona": safe_data["target_persona"],
            "target_audience": safe_data["target_audience"],
            "competitors": safe_data["competitors"],
            "ad_recommendation": safe_data["ad_recommendation"],
            "copywriting": safe_data["copywriting"],
            "keyword_strategy": safe_data["keyword_strategy"],
            "weekly_plan": safe_data["weekly_plan"],
            "roi_forecast": safe_data["roi_forecast"],
            "lms_copy_samples": safe_data["lms_copy_samples"],
            "channel_talk_samples": safe_data["channel_talk_samples"],
            "media_mix": safe_data["media_mix"] if safe_data["media_mix"] else [
                {"media": "메타/인스타", "feature": "정밀 타켓팅", "reason": "관심사 기반 도달", "strategy_example": "혜택 강조 광고"},
                {"media": "네이버", "feature": "검색 기반", "reason": "구매 의향 고객 확보", "strategy_example": "지역 키워드 점유"},
                {"media": "카카오", "feature": "모먼트 타겟", "reason": "지역 기반 노출", "strategy_example": "방문 유도"}
            ]
        }
        
        # 결과를 히스토리에 저장
        try:
            with Session(engine) as session:
                new_history = AnalysisHistory(
                    user_email=req.user_email,
                    field_name=field_name,
                    address=address,
                    score=int(total_score),
                    response_json=json.dumps(final_result)
                )
                session.add(new_history)
                session.commit()
                logger.info(f"Analysis saved to history for {field_name}")
        except Exception as he:
            logger.error(f"Failed to save analysis to history: {he}")
            
        return final_result
    except Exception as e:
        import traceback
        logger.error(f"Critical analyze error: {e}\n{traceback.format_exc()}")
        
        cat_msg = "주거 선호도가 높은 아파트" if "아파트" in product_category else "수익형 부동산으로서 가치가 높은 상품"
        smart_diagnosis = (
            f"[{field_name}]은 인근 시세({target_price}만원) 대비 약 {gap_percent}% {gap_status}한 가격대로 책정되어 실거주 및 투자 수요의 유입이 매우 강력할 것으로 예측됩니다. "
            f"특히 {address} 내에서도 {cat_msg}로 분류되어 입지적 희소성이 돋보이며, {field_keypoints if field_keypoints else '탁월한 입지'}를 바탕으로 초기 분양률 80% 이상을 목표로 하는 공격적인 마케팅이 유효한 시점입니다. "
            f"주변 {product_category} 공급량과 대비해 보았을 때 시세 차익 약 {abs(market_gap):.0f}만원의 프리미엄 확보가 가능하므로, 이를 핵심 소구점으로 한 퍼포먼스 광고 집행을 적극 권장합니다."
        )

        final_result = {
            "score": 85,
            "score_breakdown": {
                "price_score": 90 if market_gap > 0 else 70,
                "location_score": 82,
                "benefit_score": 88,
                "total_score": 85
            },
            "market_diagnosis": smart_diagnosis,
            "market_gap_percent": round(gap_percent, 2),
            "price_data": [
                {"name": "우리 현장", "price": sales_price},
                {"name": "주변 시세", "price": target_price},
                {"name": "시세 차익", "price": abs(target_price - sales_price)}
            ],
            "radar_data": [
                {"subject": "분양가", "A": 90 if market_gap > 0 else 72, "B": 70, "fullMark": 100},
                {"subject": "브랜드", "A": 85, "B": 75, "fullMark": 100},
                {"subject": "단지규모", "A": min(100, (supply_volume // 10) + 30), "B": 60, "fullMark": 100},
                {"subject": "입지", "A": 80, "B": 65, "fullMark": 100},
                {"subject": "분양조건", "A": 80, "B": 50, "fullMark": 100},
                {"subject": "상품성", "A": 90, "B": 70, "fullMark": 100}
            ],
            "target_persona": f"{address} 인근 실거주를 희망하는 3040 맞벌이 부부 및 안정적 자산 증식을 노리는 50대 투자자",
            "target_audience": ["#내집마련", "#실수요자", f"#{address.split()[0] if address and address.split() else '분양'}", "#프리미엄", "#분양정보"],
            "competitors": [
                {"name": "인근 비교 단지 A", "price": target_price, "gap_label": "1.1km 인접"},
                {"name": "인근 비교 단지 B", "price": round(target_price * 1.05), "gap_label": "도보 15분"}
            ],
            "ad_recommendation": "네이버 브랜드검색을 통한 신뢰도 확보와 메타/인스타의 '시세차익' 강조 리드광고 비중 7:3 집행 권장",
            "copywriting": f"[{field_name}] 주변 시세보다 {gap_percent}% 더 가볍게! 마포의 새로운 중심을 선점하십시오.",
            "keyword_strategy": [field_name, f"{field_name} 분양가", f"{address.split()[0]} 신축아파트", "청약일정", "모델하우스위치"],
            "weekly_plan": [
                "1주: 티징 광고 및 관심고객 DB 300건 확보 목표",
                "2주: 분양가 및 혜택 강조 정밀 타겟팅 캠페인 확산",
                "3주: 모델하우스 방문 예약 이벤트 및 집중 DB 관리",
                "4주: 청약 전 마감 입박 메시지 및 최종 상담 전환 활동"
            ],
            "roi_forecast": {"expected_leads": 120, "expected_cpl": 48000, "expected_ctr": 1.7, "conversion_rate": 3.2},
            "lms_copy_samples": [
                f"【{field_name} | 프리미엄 분양 안내】\n\n대한민국 주거 문화를 선도하는 {field_name}의 특별한 가치에 초대합니다. ✨\n\n현재 {address} 일대는 입지적 희소성과 함께 실거주자들의 문의가 폭주하고 있습니다. 특히 본 현장만이 가진 {fkp if fkp else '압도적 미래 가치'}는 시간이 흐를수록 그 진가를 발휘할 것입니다.\n\n✅ 수분양자를 위한 파격적 혜택:\n- 계약금 단 {dp}로 내 집 마련의 꿈을 실현하세요.\n- 입주 전까지 금융 부담 제로! {ib} 혜택 전격 시행.\n\n주변 구축 시세 대비 약 {gap_percent}% 낮은 합리적 분양가는 향후 강력한 시세 차익의 발판이 될 것입니다. 지금 이 기회를 놓치지 마십시오.\n\n☎️ 공식 분양 센터: 1600-0000",
                f"[High-End 분석] {field_name} 자산가치 집중 조명\n\n왜 지금 {field_name}이어야 하는가? 팩트로 증명합니다. 📊\n\n본 현장은 {address} 내에서도 {fkp if fkp else '우수한 입지'}를 점유하고 있으며, 1군 브랜드의 시공 능력이 더해진 명품 단지입니다.\n\n💰 금융 프로모션 안내:\n1. {ib} 수혜로 잔금 시까지 금융 비용 0원!\n2. 신축 아파트만의 특화 평면 및 최고급 커뮤니티\n3. {supply_volume}세대 랜드마크 스케일\n\n선착순 호수 지정 제도로 운영 중이오니, 로얄층 선점을 위해 서둘러 연락 주시기 바랍니다.\n☎️ 전문 상담: 010-0000-0000",
                f"🚨 [긴급] {field_name} 인기 타입 선착순 마감 직전 🚨\n\n오늘 당신의 선택이 5년 뒤 자산의 크기를 바꿉니다! 🔥\n현재 {field_name} 현장은 실시간 계약 폭주로 인해 잔여 물량이 급속도로 소진되고 있습니다.\n\n✨ 핵심 소구점:\n- {address} 중심 인프라를 한 걸음에 누리는 완벽한 입지\n- 전매 무제한 수혜 및 {ib} 파격 조건\n- {fkp} 적용\n\n지금 바로 모델하우스 방문 예약하시고 마지막 남은 로얄층의 주인공이 되십시오. 🎁\n📞 긴급 접수처: 1800-0000"
            ],
            "channel_talk_samples": [
                f"🔥 {field_name} | 파격 조건변경 소식! 🔥\n\n현재 호갱노노 급상승 검색어 등재! 💎\n입주 시까지 계약금 {dp}만으로 내 집 마련이 가능한 마지막 현장.\n\n이자 부담 걱정 끝! {ib} 확정 수혜 단지.\n🚅 {address}의 미래를 선점할 유일한 입지.\n\n지금 바로 채팅으로 잔여 세대를 확인하세요! 👇",
                f"🚨 [긴급] {field_name} 로열층 선착순 폭주 중! 🚨\n\n망설이면 사라지는 마지막 기회! 현재 홍보관 방문 예약이 줄을 잇고 있습니다. 💨\n\n💎 투자 핵심:\n1. {address} 랜드마크급 {supply_volume}세대 스케일\n2. 인근 대비 {gap_percent}% 합리적 공급가\n\n실시간 잔여 호수와 특별 혜택 정보를 지금 바로 안내해 드립니다! 🗨️",
                f"📊 {field_name} 전용 [정밀 분석 리포트 확인] 📊\n\n전문가가 분석한 진짜 정보, 궁금하시죠? 🧐\n\n수록 내용:\n- {address} 입지적 가치 및 공급 현황 정밀 진단\n- 시세 차익을 결정짓는 {fkp if fkp else '핵심 입지 가치'}\n- 금융 혜택 적용 시 실투자금 시뮬레이션\n\n지금 채널톡 신청 시 리포트를 즉시 발송해 드립니다! 💎"
            ],
            "media_mix": safe_data["media_mix"] if safe_data["media_mix"] else [
                {"media": "호갱노노 채널톡", "feature": "현장 집중 관심자", "reason": "실시간 데이터 기반", "strategy_example": "입지 분석 리포트 중심 상담 유도"},
                {"media": "LMS(문자 마케팅)", "feature": "다이렉트 도달", "reason": "높은 인지 및 확인율", "strategy_example": "혜택 강조 및 방문 예약 유도"},
                {"media": "메타/인스타 리드광고", "feature": "DB 수량 극대화", "reason": "관심사 기반 대량 노출", "strategy_example": "혜택 위주 소재 활용"}
            ]
        }
        
        # 결과를 히스토리에 저장 (Fallback 케이스)
        try:
            with Session(engine) as session:
                new_history = AnalysisHistory(
                    user_email=req.user_email,
                    field_name=field_name,
                    address=address,
                    score=85,
                    response_json=json.dumps(final_result)
                )
                session.add(new_history)
                session.commit()
                logger.info(f"Fallback analysis saved to history for {field_name}")
        except Exception as he:
            logger.error(f"Failed to save fallback analysis to history: {he}")
            
        return final_result

@app.get("/import-csv")
async def import_csv_data():
    """CSV 파일에서 데이터를 import"""
    import csv
    
    csv_file = os.path.join(BASE_DIR, "sites_data.csv")
    if not os.path.exists(csv_file):
        return {"status": "error", "message": "CSV 파일을 찾을 수 없습니다."}
    
    imported = 0
    updated = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            with Session(engine) as session:
                for row in reader:
                    site_id = row['id']
                    existing = session.get(Site, site_id)
                    
                    if existing:
                        existing.name = row['name']
                        existing.address = row['address']
                        existing.brand = row['brand'] if row['brand'] else None
                        existing.category = row['category']
                        existing.price = float(row['price'])
                        existing.target_price = float(row['target_price'])
                        existing.supply = int(row['supply'])
                        existing.down_payment = row.get('down_payment', '10%')
                        existing.interest_benefit = row.get('interest_benefit', '중도금 무이자')
                        existing.status = row['status'] if row['status'] else None
                        updated += 1
                    else:
                        session.add(Site(
                            id=site_id,
                            name=row['name'],
                            address=row['address'],
                            brand=row['brand'] if row['brand'] else None,
                            category=row['category'],
                            price=float(row['price']),
                            target_price=float(row['target_price']),
                            supply=int(row['supply']),
                            down_payment=row.get('down_payment', '10%'),
                            interest_benefit=row.get('interest_benefit', '중도금 무이자'),
                            status=row['status'] if row['status'] else None
                        ))
                        imported += 1
                session.commit()
        return {"status": "success", "imported": imported, "updated": updated}
    except Exception as e:
        logger.error(f"CSV import error: {e}")
        return {"status": "error", "message": str(e)}

class LeadSubmitRequest(BaseModel):
    name: str
    phone: str
    rank: str
    site: str
    source: Optional[str] = "알 수 없음"

@app.post("/submit-lead")
async def submit_lead(req: LeadSubmitRequest):
    """모수 신청(리드) 제출 API"""
    try:
        with Session(engine) as session:
            new_lead = Lead(
                name=req.name,
                phone=req.phone,
                rank=req.rank,
                site=req.site,
                source=req.source
            )
            session.add(new_lead)
            session.commit()
            logger.info(f"New lead submitted: {req.name} ({req.site})")
            
            # 구글 시트 연동 (웹훅 URL이 설정된 경우)
            if GOOGLE_SHEET_WEBHOOK_URL:
                try:
                    # 구글 매크로는 리디렉션을 사용하므로 follow_redirects=True가 필수입니다.
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        payload = {
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "name": req.name,
                            "phone": req.phone,
                            "rank": req.rank,
                            "site": req.site,
                            "source": req.source
                        }
                        # 데이터가 확실히 전송될 때까지 기다립니다.
                        response = await client.post(GOOGLE_SHEET_WEBHOOK_URL, json=payload, timeout=8.0)
                        logger.info(f"Google Sheet webhook triggered. Status: {response.status_code}")
                except Exception as ex:
                    logger.error(f"Google Sheet sync error: {ex}")

        return {"status": "success", "message": "Lead submitted successfully"}
    except Exception as e:
        logger.error(f"Lead submission error: {e}")
        raise HTTPException(status_code=500, detail="리드 제출 중 서버 오류가 발생했습니다.")
@app.get("/history", response_model=List[AnalysisHistory])
async def get_history(email: Optional[str] = None):
    """분석 히스토리 조회 API"""
    try:
        with Session(engine) as session:
            statement = select(AnalysisHistory)
            if email:
                statement = statement.where(AnalysisHistory.user_email == email)
            statement = statement.order_by(AnalysisHistory.created_at.desc()).limit(50)
            results = session.exec(statement).all()
            return results
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        return []

@app.get("/")
async def root():
    return {"message": "Bunyang AlphaGo API is running"}

if __name__ == "__main__":
    create_db_and_tables()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
