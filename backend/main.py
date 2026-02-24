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
    if not q or len(q) < 2:
        return []

    results = []
    seen_ids = set()
    q_lower = q.lower().strip()

    # 1. DB 검색 (분양 데이터베이스 우선)
    try:
        with Session(engine) as session:
            # 대소문자 구분 없이 검색 (name, address, brand, category, status 모두 검색)
            statement = select(Site).where(
                or_(
                    col(Site.name).ilike(f"%{q}%"), 
                    col(Site.address).ilike(f"%{q}%"), 
                    col(Site.brand).ilike(f"%{q}%"),
                    col(Site.category).ilike(f"%{q}%"),
                    col(Site.status).ilike(f"%{q}%")
                )
            ).order_by(col(Site.last_updated).desc()).limit(100)
            db_sites = session.exec(statement).all()
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
            res_isale = await client.get(url_isale, params=params, headers=h, timeout=3.0)
            if res_isale.status_code == 200:
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

    # 검색 결과 정렬 - 현장명에 검색어가 포함된 경우 우선 표시
    def sort_key(x):
        name_lower = x.name.lower() if x.name else ""
        address_lower = x.address.lower() if x.address else ""
        
        # 정확히 일치하는 경우 최우선
        if name_lower == q_lower:
            return (0, 0)
        # 현장명이 검색어로 시작하는 경우
        if name_lower.startswith(q_lower):
            return (1, name_lower.find(q_lower))
        # 현장명에 검색어가 포함된 경우
        if q_lower in name_lower:
            return (2, name_lower.find(q_lower))
        # 주소에 검색어가 포함된 경우
        if q_lower in address_lower:
            return (3, address_lower.find(q_lower))
        # 그 외
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
    with Session(engine) as session:
        site = session.get(Site, site_id)
        if site: return site
        return {"id": site_id, "name": "분양 분석 완료", "address": "지역 정보", "brand": "기타", "category": "부동산", "price": 2500, "target_price": 2800, "supply": 500, "status": "데이터 로드"}

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
    당신은 대한민국 상위 0.1% 부동산 퍼포먼스 마케팅 디렉터이자 '분양 알파고'의 수석 전략가입니다. 
    [{field_name}] 현장의 수분양 의향을 극대화하고 DB 전환율을 폭발적으로 높이기 위한 LMS(문서) 및 채널톡 카피 5종을 작성하십시오.

    [현장 핵심 데이터]
    - 현장명: {field_name} / 위치: {address}
    - 핵심 특장점: {fkp}
    - 금융 혜택: 계약금 {dp}, {ib}
    
    [작성 요구사항]
    1. LMS (5종 세트): 
       - 1안(신뢰/브랜드): 장문의 전문성 있는 톤앤매너, 공식적 분위기.
       - 2안(금융/수익): 주변 시세 대비 저렴한 분양가, 이자 혜택 등 수익성 강조.
       - 3안(긴급/후킹): 마감 임박, 로열층 소진 등 심리적 트리거 활용.
       - 4안(입지/비전): 미래 가치, 개발 호재, 교통망 부각.
       - 5안(감성/라이프스타일): 거주 만족도, 특화 설계, 삶의 질 강조.
    2. 채널톡 (5종 세트):
       - 모바일 앱(호갱노노, 직방 등) 유저를 타겟으로 한 짧고 핵심적인 문구.
       - 이모지를 적극적으로 활용하여 클릭율(CTR)을 극대화하십시오.

    [출력 포맷: JSON]
    {{
        "lms_copy_samples": ["LMS 1안", "LMS 2안", "LMS 3안", "LMS 4안", "LMS 5안"],
        "channel_talk_samples": ["채널톡 1안", "채널톡 2안", "채널톡 3안", "채널톡 4안", "채널톡 5안"]
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
        while len(lms_res) < 5: lms_res.append(f"{field_name} 추가 카피 준비 중...")
        
        chn_res = ai_data.get("channel_talk_samples", [])
        if not isinstance(chn_res, list): chn_res = []
        chn_res = [str(x) for x in chn_res if x]
        while len(chn_res) < 5: chn_res.append(f"{field_name} 추가 채널톡 준비 중...")

        return RegenerateCopyResponse(
            lms_copy_samples=lms_res[:5],
            channel_talk_samples=chn_res[:5]
        )
    
    # Fallback to smart templates
    gap_percent = 15
    lms_samples = [
        f"【{field_name}】\n\n🔥 파격조건변경!!\n☛ 계약금 {dp}\n☛ {ib} 파격 혜택\n☛ 실거주의무 및 청약통장 無\n\n■ 브랜드 & 자산 가치\n▶ 주변 시세 대비 {gap_percent}% 낮은 압도적 분양가\n▶ {fkp} 특화 설계 적용\n☎️ 문의 : 1600-0000",
        f"[특별공식발송] {field_name} 관심고객 안내\n💰 강력한 금융 혜택\n✅ 계약금 {dp}\n✅ {ib}\n☎️ 상담문의: 010-0000-0000",
        f"🚨 {field_name} 제로계약금 수준 마감 임박!\n🔥 {ib}, 주택수 미포함 수혜\n📞 대표번호: 1811-0000",
        f"💎 {field_name} 미래가치 리포트 공개\n🏙️ {address}의 핵심 수혜지\n📉 합리적 {gap_percent}% 낮은 가격\n▶ 상세 내용: [상담문의]",
        f"🏢 {field_name} 프리미엄 평면 안내\n✨ 전세대 포베이 특화 설계\n🌳 주거 만족도 1위의 가치\n☎️ 대표문의: 0507-0000-0000"
    ]
    channel_samples = [
        f"🔥 {field_name} | 파격 조건변경 소식!\n✅ 핵심 혜택 요약:\n- 계약금 {dp}\n- 이자 부담 제로! {ib} 확정\n📢 실시간 로열층 확인 👇",
        f"🚨 [긴급] {field_name} 로열층 선착순 마감 직전!\n📞 긴급 상담 및 방문예약: 010-0000-0000",
        f"📊 {field_name} 고관여 실거주용 [정밀 분석 리포트]\n{fkp} 등 주거 만족도 1위의 진짜 이유를 리포트로 확인하세요. 💎",
        f"🏗️ {address}의 미래 [{field_name}]\n💎 랜드마크 입지 프리미엄 공개",
        f"🎁 [{field_name}] 이벤트 참여\n모델하우스 방문 시 특별 선물 증정 ✨"
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
        당신은 대한민국 부동산 분양 마케팅의 절대강자 '분양 알파고' 시스템입니다. 
        [{field_name}] 현장의 성공적인 분양을 위한 '정밀 시장 분석' 및 '특화 마케팅 가이드'를 전문가 수준으로 상세하게 JSON으로 작성하십시오.

        [데이터 세트]
        - 현장명: {field_name} / 위치: {address} / 상품군: {product_category}
        - 프라이싱: 공급가 {sales_price} VS 주변 시세 {target_price}
        - 공급 규모: {supply_volume}세대
        - 금융 조건: 계약금 {dp}, {ib}
        - 핵심 특장점: {fkp}
        - 현재 마케팅 고민: {main_concern}
        
        [검색참고 데이터] 
        {search_context[:1000] if search_context else "최신 검색 트렌드 기반 분석 필요"}

        [미션 및 출력 요구사항]
        1. market_diagnosis: 현재의 거시 경제 흐름과 해당 지역의 구체적 지표를 결합한 날카로운 통찰력을 제공하십시오.
        2. media_mix: '호갱노노 채널톡', 'LMS(문자 마케팅)'를 포함한 최적의 3개 매체 전략을 제시하십시오.
        3. lms_copy_samples & channel_talk_samples: 위 매체에 특화된 고효율 카피 각 5종을 작성하십시오.

        [JSON Output Structure]
        {{
            "market_diagnosis": "...",
            "target_persona": "...",
            "target_audience": ["#태그1", "#태그2", "#태그3", "#태그4", "#태그5"],
            "competitors": [
                {{"name": "인근 비교 단지 A", "price": {target_price or 0}, "gap_label": "도보 5분"}},
                {{"name": "인근 비교 단지 B", "price": {target_price * 1.05 if target_price else 0}, "gap_label": "1.2km 인접"}}
            ],
            "ad_recommendation": "...",
            "copywriting": "...",
            "keyword_strategy": ["키워드1", "2", "3", "4", "5"],
            "weekly_plan": ["1주차", "2주차", "3주차", "4주차"],
            "roi_forecast": {{"expected_leads": 150, "expected_cpl": 45000, "conversion_rate": 3.5, "expected_ctr": 1.9}},
            "lms_copy_samples": ["카피1", "카피2", "카피3", "카피4", "카피5"],
            "channel_talk_samples": ["채널1", "채널2", "채널3", "채널4", "채널5"],
            "media_mix": [
                {{"media": "매체명", "feature": "강점", "reason": "이유", "strategy_example": "전략"}}
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
            
            # 카피 샘플은 반드시 5개 보장
            if key in ["lms_copy_samples", "channel_talk_samples"]:
                val = [str(x) for x in val if x]
                while len(val) < 5:
                    val.append(f"{field_name} 특화 분석 카피 생성 대기 중...")
                val = val[:5]
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

        return {
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
    except Exception as e:
        import traceback
        logger.error(f"Critical analyze error: {e}\n{traceback.format_exc()}")
        
        cat_msg = "주거 선호도가 높은 아파트" if "아파트" in product_category else "수익형 부동산으로서 가치가 높은 상품"
        smart_diagnosis = (
            f"[{field_name}]은 인근 시세({target_price}만원) 대비 약 {gap_percent}% {gap_status}한 가격대로 책정되어 실거주 및 투자 수요의 유입이 매우 강력할 것으로 예측됩니다. "
            f"특히 {address} 내에서도 {cat_msg}로 분류되어 입지적 희소성이 돋보이며, {field_keypoints if field_keypoints else '탁월한 입지'}를 바탕으로 초기 분양률 80% 이상을 목표로 하는 공격적인 마케팅이 유효한 시점입니다. "
            f"주변 {product_category} 공급량과 대비해 보았을 때 시세 차익 약 {abs(market_gap):.0f}만원의 프리미엄 확보가 가능하므로, 이를 핵심 소구점으로 한 퍼포먼스 광고 집행을 적극 권장합니다."
        )

        return {
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
                f"【{field_name}】\n\n🔥 파격조건변경!!\n☛ 계약금 {dp}\n☛ {ib} 혜택 확정\n☛ 실거주의무 및 전매제한 해제\n\n■ 브랜드 & 자산 가치\n▶ 주변 시세 대비 {gap_percent}% 낮은 압도적 분양가\n▶ {fkp if fkp else '프리미엄 특화 설계'} 적용\n▶ {supply_volume}세대 랜드마크 스케일\n\n☎️ 공식문의 : 1600-0000",
                f"[공식본부발송] {field_name} 로열층 선착순 안내\n💰 강력한 금융 혜택\n✅ 계약금 정액제 실시\n✅ {ib}\n✅ 무제한 전매 가능\n\n🏡 현장 특장점\n- {address} 내 마지막 노다지 핵심 황금 자리\n- 시세 차익 약 {abs(market_gap):.0f}만원의 강력한 가치\n☎️ 대표번호: 010-0000-0000",
                f"🚨 {field_name} 마감 임박 안내!\n🔥 전세대 영구 파노라마 조망\n🔥 인기 타입 완판 직전\n🔥 {ib} 수혜\n\n📞 긴급문의: 1800-0000",
                f"💎 [{field_name}] 미래가치 리포트 발송\n🏙️ {address}의 중심, 다시 없을 기회\n📉 {gap_status} 가격대로 선점하는 내집마련\n🚀 GTX/교통 호재의 직접 수혜지\n▶ 리포트 확인: [상담예약]",
                f"🏠 [{field_name}] 라이프스타일의 완성\n✨ {fkp if fkp else '최고급 커뮤니티'}를 갖춘 대단지\n🌿 도심 속 힐링 라이프, 숲세권 가치\n💝 선착순 방문 이벤트 진행 중\n☎️ 문의: 010-0000-0000"
            ],
            "channel_talk_samples": [
                f"🔥 {field_name} | 파격 조건변경 소식!\n✅ 핵심 혜택 요약:\n- 계약 초기 자금 부담 완화\n- 이자心配 없는 {ib} 혜택\n📢 잔여 세대 확인 👇",
                f"🚨 [긴급] {field_name} 로열층 선착순 마감 직전!\n💎 투자/실거주 포인트:\n1. {address} 권역 최상위 입지\n2. 시세 차익만 {gap_percent}% 이상 예상\n📞 긴급 상담 문의: 010-0000-0000",
                f"📊 {field_name} 전용 [팩트 체크 리포트]\n✨ 리포트 수록 내용:\n- {address} 권역 분석\n- 인근 대비 {gap_percent}% 저렴한 분양가\n▶ 리포트 신청: [상담예약신청]",
                f"🏗️ {address}의 판도를 바꿀 [{field_name}]\n💎 브랜드 프리미엄과 압도적 입지\n🌟 랜드마크가 될 이유, 지금 확인하세요.",
                f"🎁 [{field_name}] 특별 방문 이벤트!\n방문만 해도 증정되는 특별한 혜택\n지금 바로 예약하고 로열층 선점하세요. ✨"
            ],
            "media_mix": [
                {"media": "호갱노노 채널톡", "feature": "현장 집중 관심자", "reason": "실시간 데이터 기반", "strategy_example": "입지 분석 리포트 중심 상담 유도"},
                {"media": "LMS(문자 마케팅)", "feature": "다이렉트 도달", "reason": "높은 인지 및 확인율", "strategy_example": "혜택 강조 및 방문 예약 유도"},
                {"media": "메타/인스타 리드광고", "feature": "DB 수량 극대화", "reason": "관심사 기반 대량 노출", "strategy_example": "혜택 위주 소재 활용"}
            ]
        }

@app.get("/import-csv")
async def import_csv_data():
    """CSV 파일에서 데이터를 import"""
    import csv
    
    csv_file = "sites_data.csv"
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
@app.get("/")
async def root():
    return {"message": "Bunyang AlphaGo API is running"}

if __name__ == "__main__":
    create_db_and_tables()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
