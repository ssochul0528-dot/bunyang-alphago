"use client";
// Force rebuild for deployment fix

import React, { useState, useEffect, useRef } from "react";
import { useSession, signIn, signOut } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Database,
  TrendingUp,
  Target,
  MapPin,
  ShieldCheck,
  Zap,
  BarChart3,
  PieChart,
  Download,
  Cpu,
  Instagram,
  Youtube,
  MessageCircle,
  MessageSquare,
  Building,
  Home,
  Smartphone,
  CheckCircle2,
  User,
  LogOut,
  ChevronRight,
  RefreshCw,
  FileText
} from "lucide-react";
import sitesData from "./sites.json";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Cell
} from "recharts";

// For PDF generation
import { toCanvas } from 'html-to-image';
import { jsPDF } from 'jspdf';

// --- Types ---
interface AnalysisResult {
  score: number;
  score_breakdown: {
    price_score: number;
    location_score: number;
    benefit_score: number;
    total_score: number;
  };
  market_diagnosis: string;
  ad_recommendation: string;
  media_mix: { media: string; feature: string; reason: string; strategy_example: string }[];
  copywriting: string;
  price_data: { name: string; price: number }[];
  radar_data: { subject: string; A: number; B: number; fullMark: number }[];
  market_gap_percent: number;
  target_audience: string[];
  target_persona: string;
  competitors: { name: string; price: number; gap_label: string }[];
  roi_forecast: { expected_leads: number; expected_cpl: number; expected_ctr: number; conversion_rate: number };
  keyword_strategy: string[];
  weekly_plan: string[];
  lms_copy_samples: string[];
  channel_talk_samples: string[];
}

interface AnalysisHistoryEntry {
  id: number;
  field_name: string;
  address: string;
  score: number;
  created_at: string;
  response_json: string;
}

// --- Components ---
const AnimatedNumber = ({ value, decimals = 0 }: { value: number, decimals?: number }) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let startTime: number | null = null;
    const duration = 1200; // 1.2 seconds
    const startValue = displayValue; // Start from current for smooth re-triggers

    const animateCount = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);

      // easeOutExpo
      const easing = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = easing * (value - startValue) + startValue;

      setDisplayValue(current);

      if (progress < 1) {
        requestAnimationFrame(animateCount);
      }
    };

    const animationFrame = requestAnimationFrame(animateCount);
    return () => cancelAnimationFrame(animationFrame);
  }, [value]);

  return <span>{displayValue.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}</span>;
};

// --- Base URL - 환경에 따라 동적으로 설정 ---
const getBaseUrl = () => {
  // 우선적으로 환경 변수(Vercel 등에서 설정 가능)를 사용합니다.
  let url = process.env.NEXT_PUBLIC_API_URL;

  if (!url) {
    if (typeof window === 'undefined') return "http://localhost:8000";
    const { hostname, port } = window.location;

    // 로컬 접속 (localhost, 127.0.0.1, 또는 사설 IP 대역) 여부 확인
    const isLocal =
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname.startsWith('192.168.') ||
      hostname.startsWith('10.') ||
      hostname.startsWith('172.') ||
      port === '3000';

    url = isLocal
      ? `http://${hostname}:8000`
      : "https://bunyang-alphago-production-d17b.up.railway.app";
  }

  // 프로토콜이 없는 경우 https:// 추가 (브라우저에서 상대 경로로 인식되는 것 방지)
  if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
    url = `https://${url}`;
  }

  // 마지막 슬래시가 있으면 제거하여 중복 방지
  return url.replace(/\/$/, "");
};

const API_BASE_URL = getBaseUrl();

export default function BunyangAlphaGo() {
  const [mounted, setMounted] = useState(false);
  const [address, setAddress] = useState("");
  const [searchResults, setSearchResults] = useState<{ id: string, name: string, address: string }[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const [isScanning, setIsScanning] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [activeLmsTab, setActiveLmsTab] = useState(0);
  const [activeChannelTab, setActiveChannelTab] = useState(0);

  const { data: session } = useSession();
  const user = session?.user;
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [showLeadModal, setShowLeadModal] = useState(false);
  const [showLeadSuccess, setShowLeadSuccess] = useState(false);
  const [leadForm, setLeadForm] = useState({ name: "", phone: "", rank: "", site: "" });
  const [leadSource, setLeadSource] = useState("");
  const [isSubmittingLead, setIsSubmittingLead] = useState(false);

  const [history, setHistory] = useState<AnalysisHistoryEntry[]>([]);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [isFetchingHistory, setIsFetchingHistory] = useState(false);

  const reportRef = useRef<HTMLDivElement>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadPDF = async () => {
    if (!reportRef.current) {
      alert("리포트 데이터를 준비하고 있습니다. 잠시만 기다려 주세요.");
      return;
    }

    setIsDownloading(true);
    // 차트와 애니메이션이 완전히 렌더링될 시간을 줍니다.
    await new Promise(resolve => setTimeout(resolve, 1200));

    try {
      const element = reportRef.current;
      const canvas = await toCanvas(element, {
        pixelRatio: 2,
        backgroundColor: '#020617',
        cacheBust: true,
      });

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const margin = 10;
      const imgWidth = pageWidth - (margin * 2);
      const imgHeight = (canvas.height * imgWidth) / canvas.width;

      pdf.addImage(imgData, 'PNG', margin, margin, imgWidth, imgHeight);
      pdf.save(`${fieldName || '부동산'}_알파고_분석리포트.pdf`);
    } catch (e: any) {
      console.error("PDF download failure:", e);
      alert(`리포트 생성 중 문제가 발생했습니다: ${e.message || '렌더링 오류'}\n브라우저를 새로고침하신 후, 모든 차트가 나타나면 다시 시도해 주세요.`);
    } finally {
      setIsDownloading(false);
    }
  };

  const lmsTabs = [
    { label: "신뢰/종합 (긴글)", desc: "공식 브랜드 가치 및 서술형 미래 가치 강조" },
    { label: "혜택집중 (공략)", desc: "금융 솔루션 및 수익성 정밀 분석" },
    { label: "마감임박 (후킹)", desc: "심리적 트리거 및 실시간 현장 분위기" }
  ];

  const channelTabs = [
    { label: "조건/혜택 (Long)", desc: "🔥 파격 조건변경 및 모바일 최적화 긴 문구" },
    { label: "긴급/마감 (폭주)", desc: "🚨 잔여세대 급소진 및 VIP 예약 안내" },
    { label: "전문 분석 (리포트)", desc: "💎 전문가 전용 정밀 분석 및 팩트 체크" }
  ];
  const [fieldName, setFieldName] = useState("");
  const [addressValue, setAddressValue] = useState("");
  const [productCategory, setProductCategory] = useState("아파트");
  const [salesStage, setSalesStage] = useState("사전 의향서");

  const [downPayment, setDownPayment] = useState("10%");
  const [interestBenefit, setInterestBenefit] = useState("무이자");
  const [additionalBenefits, setAdditionalBenefits] = useState<string[]>([]);

  const [mainConcern, setMainConcern] = useState("DB 수량 부족");
  const [monthlyBudget, setMonthlyBudget] = useState(1000); // Default 1000만원
  const [simulationBudget, setSimulationBudget] = useState(1000);
  const [existingMedia, setExistingMedia] = useState<string[]>(["인스타그램", "블로그"]);

  const [salesPrice, setSalesPrice] = useState(2800);
  const [targetPrice, setTargetPrice] = useState(3200);
  const [downPaymentAmount, setDownPaymentAmount] = useState(3000); // Default 3000만원
  const [supply, setSupply] = useState(300);

  // Categorized Keypoint States
  const [kpLocation, setKpLocation] = useState("");
  const [kpProduct, setKpProduct] = useState("");
  const [kpBenefit, setKpBenefit] = useState("");
  const [kpGift, setKpGift] = useState("");
  const [kpExtra, setKpExtra] = useState("");

  useEffect(() => {
    setMounted(true);
  }, []);

  // Real-time site search
  useEffect(() => {
    if (isScanning || showConfig || result) return;

    const delayDebounceFn = setTimeout(async () => {
      const query = address.trim();
      if (query.length >= 1) {
        setIsSearching(true);

        // 1. 로컬 데이터에서 우선 검색 (네트워크 장애 대비)
        const localResults = sitesData
          .filter(site =>
            site.name.toLowerCase().includes(query.toLowerCase()) ||
            site.address.toLowerCase().includes(query.toLowerCase()) ||
            (site.brand && site.brand.toLowerCase().includes(query.toLowerCase()))
          )
          .slice(0, 50)
          .map(site => ({
            id: site.id,
            name: site.name,
            address: site.address,
            category: site.category,
            brand: site.brand,
            status: site.status,
            isLocal: true
          }));

        if (localResults.length > 0) {
          setSearchResults(localResults);
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        try {
          const res = await fetch(`${API_BASE_URL}/search-sites?q=${encodeURIComponent(query)}`, {
            signal: controller.signal,
            cache: 'no-store'
          });
          clearTimeout(timeoutId);
          if (res.ok) {
            const serverData = await res.json();
            // 서버 데이터가 있으면 서버 데이터로 교체 (더 최신 데이터일 수 있음)
            if (serverData && serverData.length > 0) {
              setSearchResults(serverData);
            }
          }
        } catch (e: any) {
          console.error("Server search failed, using local results if available:", e);
          // 서버 실패 시 로컬 결과가 이미 있으면 유지, 없으면 빈 배열
          if (localResults.length === 0) {
            setSearchResults([]);
          }
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults([]);
      }
    }, 400);
    return () => clearTimeout(delayDebounceFn);
  }, [address, isScanning, showConfig, result]);

  if (!mounted) return null;

  // Helper styles applied via standard HTML classes
  const inputClass = "w-full bg-slate-900/50 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500/50 transition-all";

  // Manual Scan fallback
  const handleManualScan = () => {
    if (!address || isSearching || isScanning) return;
    setIsScanning(true);
    setSearchResults([]);
    setFieldName(address + " (신규 등록)");
    setAddressValue(address);
    // Use default values for others
    setTimeout(() => {
      setIsScanning(false);
      setShowConfig(true);
    }, 1500);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (!isSearching && searchResults.length > 0) {
        handleSelectSite(searchResults[0]);
      } else {
        handleManualScan();
      }
    }
  };

  const handleSelectSite = async (site: any) => {
    setIsScanning(true);
    setSearchResults([]);
    setAddress(site.name);

    try {
      const res = await fetch(`${API_BASE_URL}/site-details/${site.id}`);
      if (res.ok) {
        const details = await res.json();
        setFieldName(details.name);
        setAddressValue(details.address);
        setProductCategory(details.category || "아파트");
        setSalesPrice(details.price || 2800);
        setTargetPrice(details.target_price || 3200);
        setSupply(details.supply || 300);
        setDownPayment(details.down_payment || "10%");
        setInterestBenefit(details.interest_benefit || "중도금 무이자");

        setTimeout(() => {
          setIsScanning(false);
          setShowConfig(true);
        }, 1200);
        return;
      }
    } catch (e) {
      console.error("Server site details failed, trying local fallback:", e);
    }

    // --- Local Fallback: Find site details in sites.json ---
    const localSite = sitesData.find(s => s.id === site.id);
    if (localSite) {
      setFieldName(localSite.name);
      setAddressValue(localSite.address);
      setProductCategory(localSite.category || "아파트");
      setSalesPrice(Number(localSite.price) || 2800);
      setTargetPrice(Number(localSite.target_price) || 3200);
      setSupply(Number(localSite.supply) || 300);
      setDownPayment(localSite.down_payment || "10%");
      setInterestBenefit(localSite.interest_benefit || "중도금 무이자");

      setTimeout(() => {
        setIsScanning(false);
        setShowConfig(true);
      }, 1000);
      return;
    }

    // --- Second Fallback: Use data already in the search result object if available ---
    // This handles external sites from server search that aren't in local sites.json
    if (site.name && site.address) {
      console.log("Using search result data as fallback for:", site.name);
      setFieldName(site.name);
      setAddressValue(site.address);
      setProductCategory(site.category || "아파트");
      // Use defaults for unknown fields
      setSalesPrice(2800);
      setTargetPrice(3200);
      setSupply(300);
      setDownPayment("10%");
      setInterestBenefit("중도금 무이자");

      setTimeout(() => {
        setIsScanning(false);
        setShowConfig(true);
      }, 1000);
    } else {
      alert("현장 데이터를 동기화하는 중 오류가 발생했습니다. 수동 입력을 진행합니다.");
      handleManualScan();
    }
  };


  const handleFinalAnalyze = async () => {
    setIsScanning(true);
    setShowConfig(false);
    setActiveLmsTab(0);
    setActiveChannelTab(0);

    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        mode: 'cors', // CORS 명시
        body: JSON.stringify({
          field_name: fieldName || "알 수 없는 현장",
          address: addressValue || "지역 정보 없음",
          product_category: productCategory || "아파트",
          sales_stage: salesStage || "분양중",
          down_payment: downPayment || "10%",
          interest_benefit: interestBenefit || "무이자",
          additional_benefits: Array.isArray(additionalBenefits) ? additionalBenefits.join(', ') : "없음",
          main_concern: mainConcern || "기타",
          monthly_budget: Number(monthlyBudget) || 0,
          existing_media: Array.isArray(existingMedia) ? existingMedia.join(', ') : "없음",
          sales_price: Number(salesPrice) || 0,
          target_area_price: Number(targetPrice) || 0,
          down_payment_amount: Number(downPaymentAmount) || 0,
          supply_volume: Number(supply) || 0,
          field_keypoints: [kpLocation, kpProduct, kpBenefit, kpGift, kpExtra].filter(v => v).join('\n'),
          user_email: user?.email || ""
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`API Analysis Error (${response.status}):`, errorText);
        throw new Error(`Server Error ${response.status}`);
      }
      const data = await response.json();
      setResult(data);
      setSimulationBudget(monthlyBudget);
    } catch (error: any) {
      console.error("Analysis failed:", error);
      const attemptedUrl = `${API_BASE_URL}/analyze`;
      setResult({
        score: 82,
        score_breakdown: { price_score: 35, location_score: 25, benefit_score: 22, total_score: 82 },
        market_diagnosis: `서버 연결에 실패했으나 로컬 분석 모드로 진단합니다.\n(Try URL: ${attemptedUrl})\n(Error: ${error.message || 'Unknown'})`,
        market_gap_percent: 12.5,
        price_data: [{ name: "우리 현장", price: salesPrice }, { name: "비교군", price: targetPrice }, { name: "대장주", price: targetPrice * 1.1 }],
        radar_data: [
          { subject: "분양가", A: 85, B: 70, fullMark: 100 },
          { subject: "브랜드", A: 90, B: 75, fullMark: 100 },
          { subject: "단지규모", A: 70, B: 60, fullMark: 100 },
          { subject: "입지", A: 80, B: 65, fullMark: 100 },
          { subject: "분양조건", A: 95, B: 50, fullMark: 100 },
          { subject: "상품성", A: 85, B: 70, fullMark: 100 }
        ],
        ad_recommendation: "메타 광고 위주 집행 추천 (로컬 모드)",
        media_mix: [
          { media: "메타 릴스", feature: "인스타그램/페이스북 노출", reason: "초기 인지도 확산 및 잠재 고객 확보 유리", strategy_example: "인테리어와 혜택을 강조한 숏폼 영상 광고 집행" },
          { media: "네이버", feature: "키워드/블로그 검색", reason: "관심 고객의 능동적 검색 대응", strategy_example: "키워드 상위 노출 및 블로그 리뷰 확보" },
          { media: "당근마켓", feature: "지역 기반 타겟팅", reason: "인근 거주 실거주 수요 공략", strategy_example: "인근 주민 대상 타겟 광고 및 이벤트 노출" }
        ],
        copywriting: "지금이 바로 기회입니다. 놓치지 마세요!",
        target_audience: ["실거주자", "투자자"],
        target_persona: "수도권 거주 3040 세대",
        competitors: [{ name: "A단지", price: targetPrice, gap_label: "비슷함" }],
        roi_forecast: { expected_leads: 50, expected_cpl: 45000, expected_ctr: 1.5, conversion_rate: 2.1 },
        keyword_strategy: ["분양", "신축", "역세권"],
        weekly_plan: [
          "1주차: 타겟 분석 및 광고 소재 기획",
          "2주차: 메인 매체 광고 집행 및 초기 반응 테스트",
          "3주차: 고효율 소재 집중 집행 및 리타겟팅 시작",
          "4주차: 잔여 물량 소진을 위한 마감 임박 메시지 전송"
        ],
        lms_copy_samples: [
          `【${fieldName}】\n\n🔥 파격조건변경!!\n☛ 계약금 10%\n☛ 중도금 무이자 확정 혜택\n☛ 실거주의무 및 청약통장 無\n\n■ 초현대적 입지+트리플 교통망\n🚅 GTX-D 고속철도 수혜(예정)\n🏫 단지 바로 앞 초·중·고 학세권\n🏙️ ${addressValue} 핵심 인프라 라이프\n\n🎁 예약 후 방문 시 '신세계 상품권' 증정\n☎️ 문의 : 1600-0000`,
          `[특별공식발송] ${fieldName} 안내\n\n💰 강력한 금융 혜택\n✅ 계약금 1000만원 정액제\n✅ 중도금 60% 전액 무이자\n✅ 무제한 전매 가능 단지\n\n🏡 현장 특장점\n- 주변 시세 대비 낮은 분양가\n- 고품격 커뮤니티 시설 완비\n\n☎️ 상담문의: 010-0000-0000`,
          `🚨 ${fieldName} 마감 임박 안내!\n\n🔥 인기 타입 완판 직전, 잔여 소수 분양\n🔥 주택수 미포함 세제 혜택 단지\n🏗️ 인근 대규모 개발 호재 수혜\n\n🎁 선착순 계약 시 '고급 가전 사은품' 증정\n📞 대표번호: 1811-0000`
        ],
        channel_talk_samples: [
          `🔥 ${fieldName} | 파격 조건변경 소식!\n\n현재 호갱노노에서 가장 뜨거운 관심을 받는 이유, 드디어 공개합니다! 💎\n\n✅ 핵심 혜택:\n- 계약금 10% & 중도금 무이자 확정\n- 주변 시세 대비 압도적 저평가 단지\n\n📢 실시간 로열층 확인 👇\n☎️ 대표문의 : 1600-0000`,
          `🚨 [긴급] ${fieldName} 로열층 마감 직전!\n\n망설이는 순간 기회는 지나갑니다. 현재 방문객 폭주로 인해 남은 물량이 실시간으로 소진되고 있습니다! 💨\n\n📞 긴급 상담: 010-0000-0000`,
          `📊 ${fieldName} 입지 분석 보고서 배포\n\n호갱노노 유저분들이 주목하는 진짜 팩트를 분석했습니다. 🧐\n학군/상권/미래가치를 숫자로 증명한 정밀 리포트를 채널톡에서 바로 받아보세요. 💎`
        ]
      });
    } finally {
      setIsScanning(false);
    }
  };

  const handleRegenerateCopy = async () => {
    console.log("Starting AI copy regeneration...");
    if (!result) {
      console.error("No result object found to regenerate from.");
      return;
    }

    setIsRegenerating(true);
    try {
      const payload = {
        field_name: fieldName,
        address: addressValue,
        product_category: productCategory,
        sales_stage: salesStage,
        down_payment: downPayment,
        interest_benefit: interestBenefit,
        additional_benefits: additionalBenefits,
        main_concern: mainConcern,
        monthly_budget: monthlyBudget,
        existing_media: existingMedia,
        sales_price: salesPrice,
        target_area_price: targetPrice,
        down_payment_amount: downPaymentAmount,
        supply_volume: supply,
        field_keypoints: [kpLocation, kpProduct, kpBenefit, kpGift, kpExtra].filter(v => v).join('\n')
      };
      console.log("Regeneration payload:", payload);

      const response = await fetch(`${API_BASE_URL}/regenerate-copy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const data = await response.json();
        console.log("Regeneration success. New data received.");

        // Critical: Update state inside function to ensure we use the latest 'result' object
        setResult(prev => {
          if (!prev) return null;
          const updated = {
            ...prev,
            lms_copy_samples: data.lms_copy_samples,
            channel_talk_samples: data.channel_talk_samples
          };
          console.log("State updated with new samples.");
          return updated;
        });

        // Show custom success modal
        setShowSuccessModal(true);
      } else {
        const errorData = await response.text();
        console.error("Regeneration failed with status:", response.status, errorData);
        alert(`카피 생성 중 오류가 발생했습니다 (${response.status}): ${errorData}`);
      }
    } catch (e: any) {
      console.error("Regeneration network/runtime error:", e);
      alert("서버와 통신 중 오류가 발생했습니다: " + e.message);
    } finally {
      setIsRegenerating(false);
      console.log("Regeneration process finished.");
    }
  };

  const handleSocialLogin = (provider: string) => {
    setIsLoggingIn(provider);
    signIn(provider, { redirect: false }).then(() => {
      setIsLoggingIn(null);
      setShowLoginModal(false);
    });
  };

  const handleLeadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leadForm.name || !leadForm.phone || !leadForm.rank || !leadForm.site) {
      alert("모든 정보를 입력해주세요.");
      return;
    }
    setIsSubmittingLead(true);
    try {
      const res = await fetch(`${API_BASE_URL}/submit-lead`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...leadForm, source: leadSource })
      });
      if (res.ok) {
        setShowLeadModal(false);
        setShowLeadSuccess(true);
        setLeadForm({ name: "", phone: "", rank: "", site: "" });
      } else {
        alert("신청 중 오류가 발생했습니다.");
      }
    } catch (err) {
      console.error(err);
      alert("서버 통신 오류가 발생했습니다.");
    } finally {
      setIsSubmittingLead(false);
    }
  };

  const fetchHistory = async () => {
    setIsFetchingHistory(true);
    try {
      const res = await fetch(`${API_BASE_URL}/history${user?.email ? `?email=${user.email}` : ''}`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
    } finally {
      setIsFetchingHistory(false);
    }
  };

  const handleLoadHistory = (entry: AnalysisHistoryEntry) => {
    const data = JSON.parse(entry.response_json);
    setResult(data);
    setFieldName(entry.field_name);
    setAddressValue(entry.address);
    setShowHistoryModal(false);
    setShowConfig(false);
    // Smooth scroll to top/result
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLogout = () => {
    if (confirm("로그아웃 하시겠습니까?")) {
      signOut({ redirect: false });
      setResult(null);
    }
  };

  const toggleBenefit = (benefit: string) => {
    setAdditionalBenefits(prev =>
      prev.includes(benefit) ? prev.filter(b => b !== benefit) : [...prev, benefit]
    );
  };

  const getMediaIcon = (mediaName: string) => {
    if (mediaName.includes("메타") || mediaName.includes("인스타")) return <Instagram className="text-pink-500" size={24} />;
    if (mediaName.includes("유튜브") || mediaName.includes("구글")) return <Youtube className="text-red-500" size={24} />;
    if (mediaName.includes("카카오")) return <MessageCircle className="text-yellow-400" size={24} />;
    if (mediaName.includes("당근")) return <MapPin className="text-orange-500" size={24} />;
    if (mediaName.includes("네이버")) return <Search className="text-green-500" size={24} />;
    if (mediaName.includes("호갱노노") || mediaName.includes("리치고")) return <Home className="text-blue-400" size={24} />;
    if (mediaName.includes("문자") || mediaName.includes("LMS")) return <MessageSquare className="text-indigo-400" size={24} />;
    if (mediaName.includes("분양의신")) return <Building className="text-purple-400" size={24} />;
    return <Smartphone className="text-slate-400" size={24} />;
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans selection:bg-blue-500/30">
      {/* Background Decor */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-900/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-900/10 blur-[120px] rounded-full" />
      </div>

      {/* Background Mesh Overlay */}
      <div className="bg-mesh" />

      {/* Header */}
      <header className="fixed top-0 left-0 w-full z-50 glass-panel border-b border-white/5 h-20">
        <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => window.location.href = "/"}
          >
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center blue-glow-border shadow-[0_0_20px_rgba(59,130,246,0.5)] group-hover:scale-110 transition-transform">
              <Cpu className="text-white" size={24} />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-black tracking-tighter leading-none group-hover:text-blue-400 transition-colors">분양알파고</span>
              <span className="text-[10px] uppercase tracking-[0.2em] text-blue-400 font-bold">Marketing AI Engine</span>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <nav className="hidden lg:flex items-center gap-8 text-sm font-bold text-slate-400">
              <button
                onClick={() => {
                  fetchHistory();
                  setShowHistoryModal(true);
                }}
                className="hover:text-blue-400 transition-all flex items-center gap-2 group"
              >
                <Database size={16} className="group-hover:scale-110 transition-transform" /> 내 리포트
              </button>
              <a href="#solution-guide" className="hover:text-blue-400 transition-all">솔루션 안내</a>
              {result && (
                <a href="#ai-performance-guide" className="text-blue-500 hover:text-blue-400 transition-all flex items-center gap-1.5 px-3 py-1 bg-blue-500/10 rounded-full border border-blue-500/20">
                  <Zap size={12} className="fill-blue-500" /> AI 가이드
                </a>
              )}
            </nav>

            <div className="h-4 w-[1px] bg-white/10 hidden md:block" />

            {user ? (
              <div className="flex items-center gap-3 pl-2">
                <div className="flex flex-col items-end hidden sm:flex">
                  <span className="text-[11px] font-black text-white">{user.name}</span>
                  <span className="text-[9px] text-slate-500">{user.email}</span>
                </div>
                <div className="relative group cursor-pointer" onClick={handleLogout}>
                  <div className="w-10 h-10 rounded-full border-2 border-blue-500/20 overflow-hidden bg-slate-900/50 p-1 group-hover:border-red-500/50 transition-all">
                    <img src={user?.image || "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"} alt="profile" className="w-full h-full object-contain rounded-full" />
                  </div>
                  <div className="absolute inset-0 bg-red-600/60 opacity-0 group-hover:opacity-100 flex items-center justify-center rounded-full transition-all">
                    <LogOut size={14} className="text-white" />
                  </div>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowLoginModal(true)}
                className="px-6 py-2.5 bg-white hover:bg-slate-200 text-slate-900 rounded-full text-xs font-black transition-all shadow-xl flex items-center gap-2 transform hover:scale-105"
              >
                <User size={14} /> 시작하기
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-40 pb-24">
        {/* Section 1: Hero & Real-time Scanner */}
        <section className="mb-24 flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-8 px-5 py-2 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-[10px] font-black uppercase tracking-[0.2em] animate-float flex items-center gap-2"
          >
            <Zap size={12} fill="currentColor" /> Real-time Marketing Engine v2.0
          </motion.div>

          <div className="max-w-5xl mx-auto text-center mb-16">
            <motion.h2
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-5xl md:text-8xl font-black mb-10 tracking-tight leading-[1.02]"
            >
              마케팅 오류 <span className="blue-glow-text text-blue-500">ZERO</span>,<br />
              <span className="text-gradient">AI 분양 분석 엔진</span>
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-lg md:text-2xl text-slate-400 font-medium max-w-3xl mx-auto leading-relaxed"
            >
              분양가 분석부터 타겟 추출, 카피 생성까지<br />
              부동산 분양의 모든 과정을 AI가 정교하게 재설계합니다.
            </motion.p>
          </div>

          {!showConfig && !result && (
            <div className="w-full max-w-3xl flex flex-col items-center">
              {/* Guidance Text */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="mb-4 flex items-center gap-2 text-slate-500 font-bold"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                <span className="text-[11px] uppercase tracking-[0.2em]">분석할 현장명 또는 주소를 입력하면 실시간 분석이 시작됩니다.</span>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="relative w-full"
              >
                <div className={`glass-panel p-3 rounded-[3rem] flex flex-col md:flex-row items-center gap-3 transition-all duration-500 ${isSearching ? 'blue-glow border-blue-500/50 scale-[1.01]' : 'blue-glow-border border-white/20'}`}>
                  <div className="flex-1 flex items-center gap-4 pl-6 w-full">
                    <MapPin className={`${isSearching ? 'text-blue-400 animate-bounce' : 'text-blue-500'} transition-all`} size={24} />
                    <input
                      type="text"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="예) 마포역 에테르노, 의정부 해링턴 플레이스..."
                      className="flex-1 bg-transparent border-none outline-none py-5 text-xl text-white font-bold placeholder:text-slate-700"
                      onKeyPress={handleKeyPress}
                    />
                  </div>
                  <button
                    onClick={handleManualScan}
                    disabled={isScanning || !address.trim()}
                    className={`w-full md:w-auto px-10 py-5 rounded-[2.2rem] font-black text-lg transition-all flex items-center justify-center gap-3 shadow-[0_0_40px_rgba(59,130,246,0.3)] transform active:scale-95 ${isSearching
                      ? 'bg-blue-600/50 text-blue-200 cursor-wait'
                      : 'bg-blue-600 hover:bg-blue-500 text-white hover:shadow-[0_0_60px_rgba(59,130,246,0.5)] hover:scale-[1.02]'
                      }`}
                  >
                    {isScanning || isSearching ? (
                      <RefreshCw className="animate-spin" size={20} />
                    ) : (
                      <Zap size={20} fill="currentColor" />
                    )}
                    {isSearching ? '데이터 검색 중...' : '정밀 분석 시작'}
                  </button>
                </div>

                {/* Search Examples / Tags */}
                <div className="mt-6 flex flex-wrap justify-center gap-3">
                  <span className="text-[10px] text-slate-600 font-bold uppercase tracking-widest mt-1.5 mr-2">인기 검색어:</span>
                  {["의정부역 해링턴", "동탄 푸르지오", "수지구청역", "반포 자이"].map(tag => (
                    <button
                      key={tag}
                      onClick={() => setAddress(tag)}
                      className="px-4 py-2 rounded-full bg-slate-900/50 border border-slate-800 text-[11px] text-slate-400 hover:text-blue-400 hover:border-blue-500/30 transition-all font-bold"
                    >
                      # {tag}
                    </button>
                  ))}
                </div>

                {/* Search Results Dropdown - Forced Opaque for Visibility */}
                <AnimatePresence>
                  {(isSearching || (address.trim().length >= 1 && searchResults.length > 0) || (!isSearching && searchResults.length === 0 && address.trim().length >= 1)) && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      style={{ backgroundColor: '#020617', opacity: 1 }}
                      className="absolute left-0 right-0 mt-3 border border-slate-800 rounded-2xl overflow-hidden z-[9999] shadow-[0_20px_60px_rgba(0,0,0,1)]"
                    >
                      {isSearching && searchResults.length === 0 && (
                        <div className="px-6 py-12 text-center flex flex-col items-center gap-3 text-slate-400">
                          <RefreshCw size={24} className="animate-spin text-blue-500/50" />
                          <p className="text-sm font-medium">실시간 데이터베이스 조회 중...</p>
                        </div>
                      )}

                      {searchResults && searchResults.length > 0 && (
                        <div className="max-h-[60vh] overflow-y-auto">
                          {isSearching && (
                            <div className="px-4 py-2 bg-blue-500/5 border-b border-white/5 text-[9px] text-blue-400/70 font-bold flex items-center gap-2">
                              <RefreshCw size={10} className="animate-spin" />
                              최신 데이터를 불러오고 있습니다...
                            </div>
                          )}
                          {searchResults.map((site: any) => (
                            <button
                              key={site.id}
                              onClick={() => handleSelectSite(site)}
                              className="w-full px-6 py-5 text-left hover:bg-white/10 transition-all border-b border-white/5 last:border-0 flex justify-between items-center group"
                            >
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1.5">
                                  {site.category && (
                                    <span className={`text-[10px] font-black px-1.5 py-0.5 rounded border ${site.category === '민간임대'
                                      ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                                      : site.category === '아파트'
                                        ? 'bg-blue-500/20 text-blue-300 border-blue-500/40'
                                        : 'bg-orange-500/20 text-orange-300 border-orange-500/40'
                                      }`}>
                                      {site.category}
                                    </span>
                                  )}
                                  {site.brand && site.brand !== "기타" && (
                                    <span className="text-[10px] font-black bg-slate-700/50 text-slate-300 px-1.5 py-0.5 rounded border border-slate-600/40">
                                      {site.brand}
                                    </span>
                                  )}
                                  <div className="text-white font-extrabold text-base group-hover:text-blue-400 transition-colors">{site.name}</div>
                                  {site.status && (
                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${site.status.includes('미분양') || site.status.includes('할인') || site.status.includes('잔여')
                                      ? 'bg-red-500/30 text-red-300 border border-red-500/40'
                                      : 'bg-green-500/30 text-green-300 border border-green-500/40'
                                      }`}>
                                      {site.status}
                                    </span>
                                  )}
                                </div>
                                <div className="text-sm text-white flex items-center gap-1.5 font-medium">
                                  <MapPin className="w-3.5 h-3.5 text-blue-400" />
                                  {site.address}
                                </div>
                              </div>
                              <ShieldCheck className="text-slate-700 group-hover:text-blue-500 transition-all transform group-hover:scale-110" size={24} />
                            </button>
                          ))}
                        </div>
                      )}

                      {!isSearching && searchResults.length === 0 && address.trim().length >= 1 && (
                        <div className="px-6 py-10 text-center">
                          <div className="text-slate-500 mb-4 flex flex-col items-center gap-2">
                            <MapPin size={32} className="opacity-20" />
                            <p className="text-sm">검색 결과가 없습니다.</p>
                          </div>
                          <button
                            onClick={handleManualScan}
                            className="text-xs font-bold text-blue-500 hover:text-blue-400 underline decoration-blue-500/30 underline-offset-4"
                          >
                            새로운 현장으로 직접 등록하기
                          </button>
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            </div>
          )}
        </section>

        {/* New: Detailed Introduction Section */}
        {
          !isScanning && !showConfig && !result && (
            <motion.div
              id="solution-guide"
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.8 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
                <div className="md:col-span-3 mb-12 text-center">
                  <span className="px-4 py-1.5 bg-blue-500/10 text-blue-500 text-[10px] font-black rounded-full border border-blue-500/20 uppercase tracking-[0.2em] mb-4 inline-block">Service Deep-Dive</span>
                  <h3 className="text-4xl md:text-5xl font-black text-white tracking-tight">마케팅 현장의 패러다임을 바꿉니다</h3>
                </div>

                {/* Card 1: Data */}
                <div className="glass-card rounded-[2.5rem] overflow-hidden flex flex-col group">
                  <div className="h-52 w-full relative overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop" alt="Real-time Data" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80" />
                    <div className="absolute bottom-6 left-8 w-14 h-14 glass-panel rounded-2xl flex items-center justify-center border-blue-500/30">
                      <Database className="text-blue-500" size={28} />
                    </div>
                  </div>
                  <div className="p-10 pt-6">
                    <h4 className="text-2xl font-black mb-4 text-white">실시간 데이터 동기화</h4>
                    <p className="text-slate-400 leading-relaxed font-medium">네이버 부동산, 국토부 실거래가 데이터를 실시간 크롤링하여 현장 및 주변 시세를 1분 만에 분석합니다.</p>
                  </div>
                </div>

                {/* Card 2: AI */}
                <div className="glass-card rounded-[2.5rem] overflow-hidden flex flex-col group">
                  <div className="h-52 w-full relative overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=2070&auto=format&fit=crop" alt="AI Strategy" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80" />
                    <div className="absolute bottom-6 left-8 w-14 h-14 glass-panel rounded-2xl flex items-center justify-center border-indigo-500/30">
                      <Cpu className="text-indigo-400" size={28} />
                    </div>
                  </div>
                  <div className="p-10 pt-6">
                    <h4 className="text-2xl font-black mb-4 text-white">AI 마케팅 페르소나</h4>
                    <p className="text-slate-400 leading-relaxed font-medium">분양 전문가의 노하우가 담긴 AI 엔진이 타겟 오디언스를 세분화하고 고효율 매체 믹스 가이드를 제시합니다.</p>
                  </div>
                </div>

                {/* Card 3: Copy */}
                <div className="glass-card rounded-[2.5rem] overflow-hidden flex flex-col group">
                  <div className="h-52 w-full relative overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=2071&auto=format&fit=crop" alt="Copywriting" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80" />
                    <div className="absolute bottom-6 left-8 w-14 h-14 glass-panel rounded-2xl flex items-center justify-center border-orange-500/30">
                      <MessageSquare className="text-orange-400" size={28} />
                    </div>
                  </div>
                  <div className="p-10 pt-6">
                    <h4 className="text-2xl font-black mb-4 text-white">고효율 카피라이팅</h4>
                    <p className="text-slate-400 leading-relaxed font-medium">호갱노노, 채널톡, LMS 등 매체별 특성에 최적화된 카피 변체를 생성하여 클릭률을 극대화합니다.</p>
                  </div>
                </div>
              </div>

              {/* Intro Heading */}
              <div className="text-center space-y-8 mb-40">
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  className="inline-block px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-black uppercase tracking-[0.2em]"
                >
                  The Power of Bunyang AlphaGo
                </motion.div>
                <h2 className="text-5xl md:text-7xl font-black tracking-tight leading-[1.1]">
                  데이터로 분양 성과를 <br />
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-blue-600">완벽하게 통제하는 방법</span>
                </h2>
                <p className="text-slate-500 text-xl max-w-3xl mx-auto font-medium leading-relaxed">
                  단순한 추측이 아닌 데이터로 입증합니다. <br />
                  알파고가 제공하는 4가지 혁신적 통찰력을 통해 분양 마케팅의 뉴 노멀을 경험하세요.
                </p>
              </div>

              {/* Feature 1: Market Intelligence */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-32 items-center mb-60">
                <div className="space-y-10 order-2 lg:order-1">
                  <div className="inline-flex items-center gap-3 px-4 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <BarChart3 className="text-emerald-400" size={18} />
                    <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Market Intelligence</span>
                  </div>
                  <h3 className="text-5xl font-black leading-tight text-white">실시간 데이터 기반의 <br /><span className="text-emerald-400">냉철한 시장 진단</span></h3>
                  <div className="space-y-8">
                    <p className="text-slate-400 leading-relaxed text-xl font-medium">
                      "현장이 매력적인가요?"라는 질문에 감으로 대답하지 마십시오. 알파고는 네이버 부동산의 실거래가와 호가를 즉시 수집하여 주변 단지와의 시세 차이를 데이터로 입증합니다.
                    </p>
                    <ul className="space-y-5">
                      {[
                        "반경 5km 내 주요 대장주 단지 실시간 시세 대조",
                        "구매 결정의 핵심인 '시세 우위 지수' 자동 산출",
                        "주변 공급 물량 및 미분양 현황 기반의 희소성 평가"
                      ].map(v => (
                        <li key={v} className="flex items-start gap-5 text-slate-300 font-bold group">
                          <CheckCircle2 size={24} className="text-emerald-500 shrink-0 mt-0.5 group-hover:scale-125 transition-transform" />
                          <span className="text-lg">{v}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="order-1 lg:order-2 perspective-2000">
                  <motion.div
                    whileHover={{ rotateY: -10, rotateX: 5, scale: 1.02 }}
                    className="glass-card rounded-[4rem] p-12 border-white/10 bg-gradient-to-br from-emerald-500/10 via-slate-950/40 to-transparent relative group overflow-hidden shadow-2xl shadow-emerald-900/10"
                  >
                    <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1551288049-bbbda536339a?q=80&w=2070&auto=format&fit=crop')] opacity-10 grayscale group-hover:scale-110 transition-transform duration-1000" />
                    <div className="relative z-10 space-y-10">
                      <div className="h-64 w-full glass-panel rounded-[2.5rem] border border-white/5 flex flex-col items-center justify-center p-10 backdrop-blur-2xl">
                        <div className="text-[10px] font-black text-slate-500 mb-3 uppercase tracking-[0.3em]">Market Price Concentration</div>
                        <div className="text-7xl font-black text-emerald-400 tracking-tighter">-12.5%</div>
                        <div className="px-6 py-2 bg-emerald-500/10 rounded-full text-[11px] text-emerald-400 font-black mt-6 border border-emerald-500/20 shadow-lg shadow-emerald-500/10">강력 매수 권고 구간</div>
                      </div>
                      <div className="grid grid-cols-2 gap-6">
                        <div className="p-7 glass-panel rounded-3xl border border-white/5">
                          <div className="text-[10px] text-slate-500 mb-2 font-black uppercase tracking-widest">Expected Price</div>
                          <div className="text-2xl font-black text-white">2,810<span className="text-sm text-slate-500 ml-1">만원</span></div>
                        </div>
                        <div className="p-7 glass-panel rounded-3xl border border-white/5">
                          <div className="text-[10px] text-slate-500 mb-2 font-black uppercase tracking-widest">Market Avg</div>
                          <div className="text-2xl font-black text-white">3,240<span className="text-sm text-slate-500 ml-1">만원</span></div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </div>
              </div>

              {/* Feature 2: Media Strategy */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-32 items-center mb-60">
                <div className="lg:order-1 perspective-2000">
                  <motion.div
                    whileHover={{ rotateY: 10, rotateX: 5, scale: 1.02 }}
                    className="glass-card rounded-[4rem] p-12 border-white/10 bg-gradient-to-br from-blue-500/10 via-slate-950/40 to-transparent relative group overflow-hidden shadow-2xl shadow-blue-900/10"
                  >
                    <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=2070&auto=format&fit=crop')] opacity-10 grayscale group-hover:scale-110 transition-transform duration-1000" />
                    <div className="relative z-10 grid grid-cols-2 gap-6">
                      {[
                        { m: 'Meta Reels', pct: '45%', c: 'bg-blue-600', val: 85 },
                        { m: 'Naver Search', pct: '25%', c: 'bg-indigo-600', val: 60 },
                        { m: 'Hogangnono', pct: '20%', c: 'bg-blue-400', val: 40 },
                        { m: 'Carrot Ads', pct: '10%', c: 'bg-slate-600', val: 20 }
                      ].map(item => (
                        <div key={item.m} className="p-6 glass-panel rounded-3xl border border-white/5 backdrop-blur-xl">
                          <div className="text-[10px] font-black text-slate-500 uppercase mb-3 tracking-widest">{item.m}</div>
                          <div className="text-3xl font-black text-white mb-3">{item.pct}</div>
                          <div className="h-2 w-full bg-slate-800/50 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              whileInView={{ width: `${item.val}%` }}
                              transition={{ duration: 1, ease: "easeOut" }}
                              className={`h-full ${item.c} shadow-[0_0_15px_rgba(59,130,246,0.4)]`}
                            />
                          </div>
                        </div>
                      ))}
                      <div className="col-span-2 p-8 bg-blue-600/10 rounded-3xl border border-blue-500/30 text-center backdrop-blur-xl">
                        <div className="text-[10px] font-black text-blue-400 mb-3 tracking-[0.3em] uppercase">Target Persona IQ</div>
                        <div className="text-lg font-bold text-white tracking-tight leading-relaxed">"내 집 마련을 꿈꾸는 서울 서북권 30대 신혼부부"</div>
                      </div>
                    </div>
                  </motion.div>
                </div>
                <div className="space-y-10 lg:order-2">
                  <div className="inline-flex items-center gap-3 px-4 py-1.5 rounded-xl bg-blue-500/10 border border-blue-500/20">
                    <Cpu className="text-blue-400" size={18} />
                    <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">Media Intelligence</span>
                  </div>
                  <h3 className="text-5xl font-black leading-tight text-white">매체비를 버리지 않는 <br /><span className="text-blue-500">데이터 미디어 믹스</span></h3>
                  <div className="space-y-8">
                    <p className="text-slate-400 leading-relaxed text-xl font-medium">
                      DB당 단가를 최소화하는 '필승 조합'을 찾으십시오. 알파고는 현장 스코어와 사업 단계(사전/본계약/잔여)를 분석하여 전환율이 가장 높은 매체 비중을 제안합니다.
                    </p>
                    <ul className="space-y-5">
                      {[
                        "Meta, 네이버, 호갱노노 등 10대 부동산 매체 실시간 효율 기반",
                        "사업 현황에 최적화된 시즌별/단계별 미디어 로드맵 제시",
                        "광고 피로도를 고려한 예산 투입 강도 실시간 최적화 엔진"
                      ].map(v => (
                        <li key={v} className="flex items-start gap-5 text-slate-300 font-bold group">
                          <CheckCircle2 size={24} className="text-blue-500 shrink-0 mt-0.5 group-hover:scale-125 transition-transform" />
                          <span className="text-lg">{v}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Feature 3: Copywriting */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-32 items-center mb-60">
                <div className="space-y-10 order-2 lg:order-1">
                  <div className="inline-flex items-center gap-3 px-4 py-1.5 rounded-xl bg-orange-500/10 border border-orange-500/20">
                    <MessageSquare className="text-orange-400" size={18} />
                    <span className="text-[10px] font-black text-orange-400 uppercase tracking-widest">Direct Response AI</span>
                  </div>
                  <h3 className="text-5xl font-black leading-tight text-white">클릭을 부르는 <br /><span className="text-orange-400">심리 기반 AI 카피라이팅</span></h3>
                  <div className="space-y-8">
                    <p className="text-slate-400 leading-relaxed text-xl font-medium">
                      마케터의 수 시간 고민을 1초로 단축하십시오. 단순한 정보 나열이 아닌, 사용자의 '결핍'과 '욕망'을 자극하는 행동 유도형 카피를 무한 생성합니다.
                    </p>
                    <ul className="space-y-5">
                      {[
                        "LMS, 채널톡, 호갱노노 배너 등 채널별 최적화된 텍스트 볼륨",
                        "신뢰형/금융집중형/마감임박형 등 성과 검증된 3대 전략 카피",
                        "현장의 특장점(USP)을 AI가 자동으로 매칭하여 문장 조합"
                      ].map(v => (
                        <li key={v} className="flex items-start gap-5 text-slate-300 font-bold group">
                          <CheckCircle2 size={24} className="text-orange-500 shrink-0 mt-0.5 group-hover:scale-125 transition-transform" />
                          <span className="text-lg">{v}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="order-1 lg:order-2 perspective-2000">
                  <div className="glass-card rounded-[4rem] p-16 border-white/10 bg-gradient-to-br from-orange-500/10 via-slate-950/40 to-transparent relative group overflow-hidden shadow-2xl shadow-orange-900/10">
                    <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=2071&auto=format&fit=crop')] opacity-10 grayscale group-hover:scale-110 transition-transform duration-1000" />
                    <div className="relative z-10 space-y-10">
                      <motion.div
                        initial={{ x: 50, opacity: 0 }}
                        whileInView={{ x: 0, opacity: 1 }}
                        className="p-8 glass-panel rounded-3xl border border-white/10 shadow-2xl backdrop-blur-2xl rotate-[-3deg] hover:rotate-0 transition-all duration-500"
                      >
                        <div className="text-[11px] text-orange-500 font-black mb-4 flex items-center gap-2 uppercase tracking-widest">
                          <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse shadow-[0_0_10px_rgba(249,115,22,0.6)]" /> Premium LMS v1
                        </div>
                        <div className="text-base text-slate-100 leading-relaxed font-bold italic">
                          "💎 [공지] 시세 대비 -12.5% 파격 분양가 확정! {addressValue.split(' ')[1] || '해당'} 지역 마지막 7억대 주거 찬스..."
                        </div>
                      </motion.div>
                      <motion.div
                        initial={{ x: -50, opacity: 0 }}
                        whileInView={{ x: 0, opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="p-8 glass-panel rounded-3xl border border-white/10 shadow-2xl backdrop-blur-2xl ml-16 rotate-[3deg] hover:rotate-0 transition-all duration-500"
                      >
                        <div className="text-[11px] text-blue-500 font-black mb-4 flex items-center gap-2 uppercase tracking-widest">
                          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shadow-[0_0_10px_rgba(59,130,246,0.6)]" /> Alert Mode v2
                        </div>
                        <div className="text-base text-slate-100 leading-relaxed font-bold mb-2">
                          🚨 [실시간] 조건변경 공지 직후 홍보관 방문객 4배 폭증! 남은 고층 잔여세대 실시간 동향 파악하기...
                        </div>
                      </motion.div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Feature 4: ROI Simulation */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-32 items-center mb-60">
                <div className="lg:order-1 perspective-2000">
                  <motion.div
                    whileHover={{ scale: 1.05, rotateX: 5 }}
                    className="glass-card rounded-[4rem] p-16 border-white/10 bg-gradient-to-br from-indigo-500/10 via-slate-950/40 to-transparent relative group overflow-hidden shadow-2xl shadow-indigo-900/10"
                  >
                    <div className="relative z-10 space-y-10">
                      <div className="h-64 w-full glass-panel rounded-[2.5rem] border border-indigo-500/20 flex flex-col items-center justify-center p-12 backdrop-blur-3xl shadow-inner">
                        <div className="text-[10px] font-black text-indigo-400 mb-4 uppercase tracking-[0.4em]">Expected ROI Optimization</div>
                        <div className="text-8xl font-black text-white tracking-tighter">4.2<span className="text-2xl text-indigo-500 ml-2">%</span></div>
                        <div className="text-[10px] text-slate-500 mt-6 font-bold uppercase tracking-[0.2em]">Predicted Final Conversion Rate</div>
                      </div>
                      <div className="space-y-6">
                        <div className="flex justify-between items-end px-2">
                          <div className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Efficiency Pipeline</div>
                          <div className="text-sm font-black text-indigo-400 tracking-tight">OPTIMIZED AT 92%</div>
                        </div>
                        <div className="h-4 w-full bg-slate-900/80 rounded-full overflow-hidden p-1 border border-white/5">
                          <motion.div
                            initial={{ width: 0 }}
                            whileInView={{ width: '92%' }}
                            transition={{ duration: 1.5, ease: "circOut" }}
                            className="h-full bg-gradient-to-r from-indigo-600 via-blue-500 to-indigo-400 rounded-full shadow-[0_0_20px_rgba(99,102,241,0.5)]"
                          />
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </div>
                <div className="space-y-10 lg:order-2">
                  <div className="inline-flex items-center gap-3 px-4 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                    <PieChart className="text-indigo-400" size={18} />
                    <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">ROI Simulator</span>
                  </div>
                  <h3 className="text-5xl font-black leading-tight text-white">예산 투입 전 성과를 <br /><span className="text-indigo-400">100% 시뮬레이션</span></h3>
                  <div className="space-y-8">
                    <p className="text-slate-400 leading-relaxed text-xl font-medium">
                      마케팅 대행사에 예산을 맡기기 전에 먼저 시뮬레이션 하십시오. 예산 규모에 따른 DB 확보량, 예상 단가(CPL)를 정밀 연산하여 실패 확률을 제로로 만듭니다.
                    </p>
                    <ul className="space-y-5">
                      {[
                        "실시간 예산 조정에 따른 성과 지표 자동 업데이트 엔진",
                        "현장 매력도와 전환율이 연동된 과학적 성과 예측 모델",
                        "DB 확보부터 방문까지 고도화된 성과 파이프라인 시각화"
                      ].map(v => (
                        <li key={v} className="flex items-start gap-5 text-slate-300 font-bold group">
                          <CheckCircle2 size={24} className="text-indigo-500 shrink-0 mt-0.5 group-hover:scale-125 transition-transform" />
                          <span className="text-lg">{v}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Final Persuasion CTA */}
              <div className="py-40 text-center glass-card rounded-[5rem] border-white/10 bg-gradient-to-b from-blue-600/20 via-slate-950/60 to-transparent relative overflow-hidden px-10">
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-5" />
                <div className="relative z-10 max-w-4xl mx-auto">
                  <h4 className="text-6xl md:text-7xl font-black mb-12 tracking-tight leading-[1.1]">
                    성공하는 현장은 <br />
                    <span className="text-blue-500 underline decoration-blue-500/30 underline-offset-[16px]">데이터를 먼저 봅니다</span>
                  </h4>
                  <p className="text-slate-400 text-2xl font-medium mb-20 leading-relaxed">
                    불확실한 부동산 시장에서 감에만 의존하시겠습니까?<br />
                    알파고의 압도적 통찰력이 당신의 현장을 '대장주'로 만듭니다.
                  </p>
                  <motion.button
                    whileHover={{ scale: 1.05, y: -5 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                    className="px-16 py-8 bg-blue-600 hover:bg-blue-500 text-white font-black rounded-[2.5rem] text-2xl shadow-[0_0_60px_rgba(59,130,246,0.4)] transition-all flex items-center gap-6 mx-auto"
                  >
                    <Zap size={32} fill="currentColor" /> 지금 바로 무료 분석 시작하기
                  </motion.button>
                  <div className="mt-12 text-[12px] font-black text-slate-500 uppercase tracking-[0.5em] opacity-50">Insight Guaranteed · Data Driven Success</div>
                </div>
              </div>
            </motion.div>
          )
        }

        <AnimatePresence>
          {isScanning && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center mt-20">
              <div className="relative w-64 h-64 flex items-center justify-center">
                <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full" />
                <div className="absolute inset-0 border-t-4 border-blue-500 rounded-full radar-sweep" />
                <Cpu className="text-blue-400 animate-pulse" size={48} />
              </div>
              <h3 className="text-xl font-bold text-blue-400 mt-8">네이버 부동산 데이터 동기화 중...</h3>
            </motion.div>
          )}

          {showConfig && !isScanning && (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="max-w-4xl mx-auto glass p-10 rounded-[2.5rem] border-blue-500/20 shadow-2xl">
              <h3 className="text-2xl font-black mb-10 flex items-center gap-3">
                <ShieldCheck className="text-blue-500" size={28} /> 데이터 최종 확인
              </h3>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                {/* Left Column: Logic & Parameters (5 units) */}
                <div className="lg:col-span-5 space-y-8">
                  {/* Basic Info Group */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-1 h-4 bg-blue-500 rounded-full" />
                      <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest">01. 기본 정보</span>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 block mb-1.5 ml-1">현장명</label>
                      <input type="text" value={fieldName} onChange={e => setFieldName(e.target.value)} className={inputClass} />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 block mb-1.5 ml-1">상세 주소</label>
                      <input type="text" value={addressValue} onChange={e => setAddressValue(e.target.value)} className={inputClass} />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 block mb-1.5 ml-1">상품 분류</label>
                      <select value={productCategory} onChange={e => setProductCategory(e.target.value)} className={inputClass}>
                        {["아파트", "민간임대", "오피스텔", "지식산업센터", "상가", "숙박시설", "타운하우스"].map(v => <option key={v} value={v} className="bg-slate-950">{v}</option>)}
                      </select>
                    </div>
                  </div>

                  {/* Sales Terms Group */}
                  <div className="space-y-4 pt-6 border-t border-slate-800/50">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-1 h-4 bg-indigo-500 rounded-full" />
                      <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest">02. 분양 조건</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-500 block mb-1.5 ml-1">계약금 비율</label>
                        <select value={downPayment} onChange={e => setDownPayment(e.target.value)} className={inputClass}>
                          {["5%", "10%", "정액제"].map(v => <option key={v} value={v} className="bg-slate-950">{v}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-500 block mb-1.5 ml-1">계약금액 (만원)</label>
                        <input type="number" value={downPaymentAmount} onChange={e => setDownPaymentAmount(Number(e.target.value))} className={inputClass} />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 block mb-1.5 ml-1">공급 규모 (세대)</label>
                      <input type="number" value={supply} onChange={e => setSupply(Number(e.target.value))} className={inputClass} />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 block mb-1.5 ml-1">주요 추가 혜택</label>
                      <div className="flex flex-wrap gap-2">
                        {["전매 제한 해제", "풀옵션 무상", "발코니 확장", "중도금 무이자"].map(v => (
                          <button key={v} onClick={() => toggleBenefit(v)} className={`px-2 py-1.5 rounded-lg text-[9px] font-bold transition-all border ${additionalBenefits.includes(v) ? 'bg-blue-600 border-blue-400 text-white' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
                            {v}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Price Matrix Group */}
                  <div className="space-y-4 pt-6 border-t border-slate-800/50">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-1 h-4 bg-emerald-500 rounded-full" />
                      <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest">03. 시세 분석 (만원/평)</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <input type="number" value={salesPrice} onChange={e => setSalesPrice(Number(e.target.value))} placeholder="분양가" className={inputClass} />
                      <input type="number" value={targetPrice} onChange={e => setTargetPrice(Number(e.target.value))} placeholder="주변 시세" className={inputClass} />
                    </div>
                  </div>
                </div>

                {/* Right Column: Content & Copywriting (7 units) */}
                <div className="lg:col-span-7 bg-slate-900/20 rounded-3xl p-8 border border-white/5 relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-5"><Cpu size={120} /></div>

                  <div className="flex items-center gap-2 mb-6 relative z-10">
                    <div className="w-1.5 h-6 bg-blue-500 rounded-full shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
                    <label className="text-[15px] font-black text-white uppercase tracking-tight">현장 핵심 강조 포인트</label>
                  </div>

                  <div className="space-y-4 relative z-10">
                    {[
                      { id: 'loc', label: '입지 호재', icon: <MapPin size={14} />, color: 'text-emerald-400', val: kpLocation, set: setKpLocation, placeholder: '예: GTX-C 개통 확정, 트리플 역세권' },
                      { id: 'prod', label: '단지 특징', icon: <Building size={14} />, color: 'text-blue-400', val: kpProduct, set: setKpProduct, placeholder: '예: 1,816세대 대단지, 초품아, 4Bay' },
                      { id: 'ben', label: '파격 혜택', icon: <Zap size={14} />, color: 'text-indigo-400', val: kpBenefit, set: setKpBenefit, placeholder: '예: 10년 전 분양가, 계약금 5% 최저가' },
                      { id: 'gift', label: '방문 사은품', icon: <Download size={14} />, color: 'text-orange-400', val: kpGift, set: setKpGift, placeholder: '예: 스타벅스 기프트카드, 고급 와인' },
                      { id: 'extra', label: '기타 강조', icon: <Target size={14} />, color: 'text-slate-400', val: kpExtra, set: setKpExtra, placeholder: '예: 투자 가치 높은 갭투자 현장' }
                    ].map((item) => (
                      <div key={item.id} className="relative group">
                        <div className="flex items-center justify-between mb-1.5 px-1">
                          <div className={`flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider ${item.color}`}>
                            {item.icon} {item.label}
                          </div>
                        </div>
                        <input
                          type="text"
                          value={item.val}
                          onChange={e => item.set(e.target.value)}
                          placeholder={item.placeholder}
                          className="w-full bg-slate-950/80 border border-slate-800 rounded-2xl px-5 py-4 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50 transition-all shadow-inner"
                        />
                      </div>
                    ))}
                  </div>

                  <div className="mt-8 p-5 bg-blue-600/10 rounded-2xl border border-blue-500/20 flex gap-4 relative z-10">
                    <Cpu size={20} className="text-blue-500 shrink-0 mt-0.5" />
                    <p className="text-[11px] text-slate-400 leading-relaxed font-medium">
                      입력하신 키포인트는 AI 엔진이 분석하여 <span className="text-blue-400 font-bold">LMS의 헤드라인</span>과 <span className="text-orange-400 font-bold">호갱노노의 실시간 톡</span> 광고 문구로 자동 조합되어 반영됩니다.
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-12 flex gap-4">
                <button onClick={() => setShowConfig(true)} className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 py-4 rounded-2xl font-bold transition-all border border-slate-700">초기화</button>
                <button onClick={handleFinalAnalyze} className="flex-[2] bg-blue-600 hover:bg-blue-500 text-white py-4 rounded-2xl font-bold blue-glow transition-all flex items-center justify-center gap-2">
                  <Zap size={20} /> 정밀 분석 실행
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Section 2 & 3: Results */}
        {
          result && !isScanning && (
            <motion.div
              ref={reportRef}
              id="pdf-report-container"
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-6 relative p-8 rounded-[3rem] bg-slate-950/20"
            >
              {/* Internal Dashboard Header & Integrated Download Button */}
              <div className="lg:col-span-12 glass p-8 rounded-3xl border-white/10 flex flex-col md:flex-row items-center justify-between gap-6 mb-2">
                <div className="flex items-center gap-6">
                  <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center blue-glow shadow-xl">
                    <ShieldCheck className="text-white" size={32} />
                  </div>
                  <div>
                    <h2 className="text-3xl font-black text-white flex items-center gap-3">
                      {fieldName} <span className="text-sm font-bold text-blue-400 bg-blue-500/10 px-3 py-1 rounded-full border border-blue-500/20">AI 정밀 분석 완료</span>
                    </h2>
                    <p className="text-slate-400 text-sm font-medium flex items-center gap-2 mt-1">
                      <MapPin size={14} className="text-blue-500" /> {addressValue} | <Target size={14} className="text-indigo-500" /> {result.target_persona}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 no-print" data-html2canvas-ignore="true">
                  <button
                    onClick={handleDownloadPDF}
                    disabled={isDownloading}
                    className="group relative px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-2xl font-black text-base shadow-[0_15px_30px_rgba(59,130,246,0.4)] transition-all transform hover:-translate-y-1 active:translate-y-0 disabled:grayscale disabled:cursor-not-allowed flex items-center gap-3"
                  >
                    {isDownloading ? (
                      <>
                        <RefreshCw size={20} className="animate-spin" /> 리포트 생성 중...
                      </>
                    ) : (
                      <>
                        <Download size={20} className="group-hover:animate-bounce" />
                        PDF 리포트 다운로드
                      </>
                    )}
                    <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
                  </button>
                </div>
              </div>

              {/* Dashboard Row 1: Score & Chart */}
              <div className="lg:col-span-4 glass p-8 rounded-3xl flex flex-col items-center justify-center relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-5"><ShieldCheck size={120} /></div>
                <h3 className="text-slate-400 font-bold text-xs uppercase tracking-widest mb-6">종합 매력 지수</h3>
                <div className="relative">
                  <svg className="w-48 h-48 -rotate-90">
                    <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="10" fill="transparent" className="text-blue-900/20" />
                    <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="10" fill="transparent" strokeDasharray={2 * Math.PI * 88} strokeDashoffset={2 * Math.PI * 88 * (1 - result.score / 100)} strokeLinecap="round" className="text-blue-500 transition-all duration-1000" />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-6xl font-black">{result.score}</span>
                    <span className="text-blue-400 font-bold text-[10px] tracking-widest uppercase">Target Achieved</span>
                  </div>
                </div>
                <div className="mt-8 grid grid-cols-3 gap-6 w-full pt-6 border-t border-slate-800/50">
                  <div className="text-center">
                    <div className="text-slate-500 text-[10px] font-bold mb-1">시세</div>
                    <div className="text-blue-400 font-bold text-sm">{result.score_breakdown.price_score}<span className="text-[10px] text-slate-500">/40</span></div>
                  </div>
                  <div className="text-center border-x border-slate-800/50">
                    <div className="text-slate-500 text-[10px] font-bold mb-1">입지</div>
                    <div className="text-blue-400 font-bold text-sm">{result.score_breakdown.location_score}<span className="text-[10px] text-slate-500">/30</span></div>
                  </div>
                  <div className="text-center">
                    <div className="text-slate-500 text-[10px] font-bold mb-1">조건</div>
                    <div className="text-blue-400 font-bold text-sm">{result.score_breakdown.benefit_score}<span className="text-[10px] text-slate-500">/30</span></div>
                  </div>
                </div>
              </div>

              <div className="lg:col-span-8 glass p-8 rounded-3xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-5"><TrendingUp size={120} /></div>
                <div className="flex items-center justify-between mb-8 relative z-10">
                  <div>
                    <h3 className="text-xl font-black flex items-center gap-2">
                      <Zap className="text-blue-500 fill-blue-500/20" size={24} /> 6대 핵심 밸런스 분석
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 font-medium italic">경점 현장 평균 대비 우리 현장 육각형 지표 (Radar Matrix)</p>
                  </div>
                  <div className="flex gap-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-blue-500" />
                      <span className="text-[10px] font-bold text-slate-400">우리 현장</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-slate-700" />
                      <span className="text-[10px] font-bold text-slate-400">시장 평균</span>
                    </div>
                  </div>
                </div>

                <div className="h-[300px] w-full relative z-10">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={result.radar_data}>
                      <PolarGrid stroke="#1e293b" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: "#94a3b8", fontSize: 11, fontWeight: 'bold' }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "16px", fontSize: "12px", boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)" }}
                        itemStyle={{ color: "#fff" }}
                      />
                      <Radar
                        name="우리 현장"
                        dataKey="A"
                        stroke="#3b82f6"
                        fill="#3b82f6"
                        fillOpacity={0.5}
                        strokeWidth={3}
                      />
                      <Radar
                        name="시장 평균"
                        dataKey="B"
                        stroke="#475569"
                        fill="#475569"
                        fillOpacity={0.2}
                        strokeWidth={2}
                        strokeDasharray="4 4"
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Dashboard Row 2: Target & Competitors */}
              <div className="lg:col-span-6 glass p-8 rounded-3xl">
                <h3 className="text-lg font-bold mb-6 flex items-center gap-2"><Target className="text-blue-500" size={18} /> 핵심 타겟 페르소나</h3>
                <div className="p-5 bg-blue-500/5 rounded-2xl border border-blue-500/10 mb-6">
                  <p className="text-blue-200 text-sm font-medium leading-relaxed italic">"{result.target_persona}"</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(result.target_audience || []).map((tag: string) => (
                    <span key={tag} className="px-3 py-1.5 bg-slate-900 text-slate-400 text-[10px] font-bold rounded-lg border border-slate-800">#{tag}</span>
                  ))}
                </div>
              </div>

              <div className="lg:col-span-6 glass p-8 rounded-3xl">
                <h3 className="text-lg font-bold mb-6 flex items-center gap-2"><BarChart3 className="text-blue-500" size={18} /> 경쟁 단지 비교</h3>
                <div className="space-y-4">
                  {(result.competitors || []).map((comp: any) => (
                    <div key={comp.name} className="flex items-center justify-between p-4 bg-slate-900/50 rounded-xl border border-slate-800/50">
                      <div>
                        <div className="text-xs font-bold text-white mb-1">{comp.name}</div>
                        <div className="text-[10px] text-slate-500">{comp.gap_label}</div>
                      </div>
                      <div className="text-sm font-black text-blue-400">{comp.price.toLocaleString()} 만원</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Dashboard Row 3: Diagnosis Updated to Full Width */}
              <div id="ai-performance-guide" className="lg:col-span-12 glass p-8 rounded-3xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-5"><Zap size={140} className="text-blue-500" /></div>
                <h3 className="text-lg font-bold mb-6 flex items-center gap-2"><Database className="text-blue-500" size={18} /> AI 퍼포먼스 가이드</h3>
                <p className="text-slate-300 text-sm leading-relaxed mb-8 whitespace-pre-line">{result.market_diagnosis}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-slate-900 rounded-xl border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-500 mb-2 uppercase">Copy Strategy</div>
                    <div className="text-xs font-bold text-blue-400 leading-relaxed">{result.copywriting}</div>
                  </div>
                  <div className="p-4 bg-slate-900 rounded-xl border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-500 mb-2 uppercase">Keyword Group</div>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {(result.keyword_strategy || []).slice(0, 3).map((kw: string) => (
                        <span key={kw} className="text-[9px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20">{kw}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Dashboard Row 4: Specialized Media Strategy */}
              <div className="lg:col-span-12 glass p-8 rounded-3xl border-blue-500/10">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
                  <div>
                    <h3 className="text-xl font-black flex items-center gap-3">
                      <Database className="text-blue-500" size={24} />
                      매체별 맞춤전략
                      <span className="text-[10px] font-bold bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30 uppercase tracking-widest ml-2">Smart Mix</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 font-medium italic">선택한 현장 고민 해결을 위한 최적의 미디어 믹 제안</p>
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-[9px] font-black text-slate-500 uppercase tracking-[0.2em] ml-1">현재 현장의 가장 큰 고민 선택</label>
                    <div className="flex bg-slate-950 p-1.5 rounded-2xl border border-slate-800">
                      {["DB 수량 부족", "DB 질 저하", "낮은 클릭률(CTR)", "방문객 없음"].map(v => (
                        <button
                          key={v}
                          onClick={() => {
                            setMainConcern(v);
                            setTimeout(() => handleFinalAnalyze(), 50);
                          }}
                          className={`px-5 py-2.5 rounded-xl text-[11px] font-bold transition-all ${mainConcern === v
                            ? 'bg-blue-600 text-white blue-glow shadow-lg'
                            : 'text-slate-500 hover:text-slate-300'
                            }`}
                        >
                          {v}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {(result.media_mix || []).map((item, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: idx * 0.1 }}
                      className="p-6 bg-slate-900/40 rounded-2xl border border-slate-800 hover:border-blue-500/30 transition-all flex flex-col gap-3 group relative overflow-hidden"
                    >
                      <div className="absolute top-0 right-0 p-4 opacity-10 grayscale group-hover:grayscale-0 transition-all duration-500">
                        {getMediaIcon(item.media)}
                      </div>

                      <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform duration-300">
                          {getMediaIcon(item.media)}
                        </div>
                        <span className="text-blue-100 font-black text-sm tracking-tight">{item.media}</span>
                      </div>

                      <div className="text-[11px] font-bold text-slate-400 uppercase tracking-tighter bg-slate-900/80 px-2 py-1.5 rounded w-fit border border-slate-800">
                        {item.feature}
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed font-medium mt-1">
                        {item.reason}
                      </p>

                      <div className="mt-4 p-3 bg-blue-600/5 rounded-xl border border-blue-500/10">
                        <div className="text-[10px] font-black text-blue-400 mb-1 flex items-center gap-1">
                          <Zap size={10} /> 집행 전략 제안
                        </div>
                        <p className="text-[11px] text-slate-400 leading-snug font-medium italic">
                          "{item.strategy_example}"
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Dashboard Row 5: Redesigned ROI Simulation */}
              <div className="lg:col-span-12 glass p-10 rounded-[2.5rem] bg-gradient-to-br from-indigo-900/20 via-slate-900/50 to-blue-900/20 border-indigo-500/20">
                <div className="flex flex-col lg:flex-row items-center justify-between gap-12">
                  <div className="w-full lg:w-1/3">
                    <h3 className="text-2xl font-black mb-4 flex items-center gap-3">
                      <PieChart className="text-indigo-400" size={28} />
                      예상 ROI 시뮬레이션
                    </h3>
                    <p className="text-sm text-slate-400 leading-relaxed mb-8">
                      마케팅 고민과 예산을 조절하여 <span className="text-white font-bold">최적의 매체 믹스 성과</span>를 실시간으로 시뮬레이션 하세요.
                    </p>

                    <div className="mb-6 invisible h-0" />

                    <div className="mb-10 p-6 bg-slate-950/70 rounded-[2rem] border border-blue-500/30 shadow-2xl">
                      <div className="flex justify-between items-center mb-6">
                        <span className="text-sm font-black text-blue-400 uppercase tracking-widest flex items-center gap-2">
                          <Zap size={16} className="fill-blue-400" />
                          실시간 예산 조정
                        </span>
                        <span className="text-2xl font-black text-white bg-blue-600/20 px-4 py-1.5 rounded-xl border border-blue-500/30">
                          {simulationBudget.toLocaleString()}<span className="text-xs ml-1 text-slate-400">만원</span>
                        </span>
                      </div>
                      <input
                        type="range"
                        min="100"
                        max="10000"
                        step="100"
                        value={simulationBudget}
                        onChange={(e) => setSimulationBudget(Number(e.target.value))}
                        className="w-full h-3 bg-slate-800 rounded-xl appearance-none cursor-pointer accent-blue-500 mb-4"
                      />
                      <div className="flex justify-between">
                        <span className="text-xs font-bold text-slate-600">100만원</span>
                        <span className="text-xs font-bold text-slate-600">1억원</span>
                      </div>
                    </div>

                    <div className="p-8 bg-indigo-600 rounded-[2rem] shadow-2xl shadow-indigo-900/40 border border-indigo-400/30">
                      <div className="text-xs font-black text-indigo-100 uppercase tracking-widest mb-3 flex items-center gap-2">
                        <Cpu size={14} /> AI Performance Advice
                      </div>
                      <p className="text-sm font-bold leading-relaxed">{result.ad_recommendation}</p>
                    </div>
                  </div>

                  <div className="w-full lg:w-2/3 grid grid-cols-1 sm:grid-cols-2 gap-6 relative">
                    {/* Step 1: Budget */}
                    <div className="p-8 bg-slate-950/50 rounded-[2.5rem] border border-slate-800 text-center flex flex-col items-center justify-center group hover:border-blue-500/50 transition-all hover:bg-slate-900/50">
                      <div className="w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center mb-5 text-slate-500 group-hover:text-blue-400 transition-colors shadow-inner">
                        <TrendingUp size={32} />
                      </div>
                      <div className="text-[11px] font-black text-slate-500 uppercase tracking-[0.2em] mb-3">집행 예산</div>
                      <div className="text-4xl font-black text-white">
                        <AnimatedNumber value={simulationBudget} />
                        <span className="text-sm text-slate-500 ml-1">만원</span>
                      </div>
                    </div>

                    {/* Step 2: CTR */}
                    <div className="p-8 bg-slate-950/50 rounded-[2.5rem] border border-slate-800 text-center flex flex-col items-center justify-center group hover:border-orange-500/50 transition-all hover:bg-slate-900/50">
                      <div className="w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center mb-5 text-slate-500 group-hover:text-orange-400 transition-colors shadow-inner">
                        <Target size={32} />
                      </div>
                      <div className="text-[11px] font-black text-slate-500 uppercase tracking-[0.2em] mb-3">예상 클릭률(CTR)</div>
                      <div className="text-4xl font-black text-white">
                        <AnimatedNumber value={result.roi_forecast.expected_ctr || 1.8} decimals={1} />
                        <span className="text-sm text-slate-500 ml-1">%</span>
                      </div>
                    </div>

                    {/* Step 3: Leads */}
                    <div className="p-8 bg-blue-900/10 rounded-[2.5rem] border border-blue-500/30 text-center flex flex-col items-center justify-center relative shadow-[0_20px_40px_-15px_rgba(59,130,246,0.3)] hover:bg-blue-900/20 transition-all">
                      <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1.5 bg-blue-600 text-[10px] font-black rounded-full shadow-lg border border-blue-400/30 tracking-widest">LIVE ESTIMATE</div>
                      <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mb-5 text-white shadow-xl shadow-blue-900/40">
                        <ShieldCheck size={32} />
                      </div>
                      <div className="text-[11px] font-black text-blue-300 uppercase tracking-[0.2em] mb-3">예상 DB 확보</div>
                      <div className="text-5xl font-black text-white">
                        <AnimatedNumber value={(result.roi_forecast.expected_leads / (Number(monthlyBudget) || 1)) * simulationBudget} />
                        <span className="text-sm text-blue-400 ml-1">개</span>
                      </div>
                    </div>

                    {/* Step 4: Conversion */}
                    <div className="p-8 bg-emerald-900/10 rounded-[2.5rem] border border-emerald-500/20 text-center flex flex-col items-center justify-center group hover:border-emerald-500/50 transition-all hover:bg-emerald-900/20">
                      <div className="w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center mb-5 text-slate-500 group-hover:text-emerald-400 transition-colors shadow-inner">
                        <Zap size={32} />
                      </div>
                      <div className="text-[11px] font-black text-slate-500 uppercase tracking-[0.2em] mb-3">예상 방문/전환</div>
                      <div className="text-4xl font-black text-white">
                        <AnimatedNumber value={((result.roi_forecast.expected_leads / (Number(monthlyBudget) || 1)) * simulationBudget) * result.roi_forecast.conversion_rate / 100} decimals={1} />
                        <span className="text-sm text-slate-500 ml-1">명</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 추가된 강력한 CTA 버튼 */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  className="mt-12 w-full"
                >
                  <motion.button
                    whileHover={{ scale: 1.02, boxShadow: "0 0 30px rgba(79, 70, 229, 0.4)" }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      setLeadForm(prev => ({ ...prev, site: fieldName }));
                      setLeadSource("ROI 시뮬레이션 하단");
                      setShowLeadModal(true);
                    }}
                    className="w-full py-6 bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-600 bg-[length:200%_auto] hover:bg-right text-white rounded-3xl font-black text-lg transition-all shadow-2xl flex items-center justify-center gap-4 relative overflow-hidden group"
                  >
                    <div className="absolute inset-0 bg-white/10 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000 ease-in-out" />
                    <FileText className="text-white group-hover:rotate-12 transition-transform" size={24} />
                    <span className="tracking-tight">현장 정밀 진단 리포트 무료받기</span>
                    <div className="flex items-center gap-1 bg-white/20 px-3 py-1 rounded-full text-[10px] font-bold">
                      <Zap size={10} className="fill-white" /> 신청폭주
                    </div>
                    <ChevronRight className="group-hover:translate-x-2 transition-transform" size={24} />
                  </motion.button>
                  <p className="text-center text-[11px] text-slate-500 mt-4 font-bold italic">
                    * 리포트 신청 시 담당자가 24시간 이내에 정밀 분석 자료를 송부해 드립니다.
                  </p>
                </motion.div>
              </div>

              {/* Dashboard Row 5: LMS Copy Sample with Tabs */}
              <div className="lg:col-span-12 glass p-8 rounded-3xl border-indigo-500/20 bg-indigo-900/5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                  <div>
                    <h3 className="text-xl font-black flex items-center gap-3">
                      <MessageSquare className="text-indigo-400" size={24} />
                      전략별 맞춤 LMS 카피 (3종)
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 italic">상담 목적에 맞는 마케팅 문구를 선택하여 활용하세요.</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleRegenerateCopy}
                      disabled={isRegenerating}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold border border-slate-700 transition-all flex items-center gap-2"
                    >
                      <RefreshCw size={14} className={isRegenerating ? "animate-spin" : ""} /> AI 카피 재생성
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(result.lms_copy_samples[activeLmsTab]);
                        alert("카피가 클립보드에 복사되었습니다.");
                      }}
                      className="px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-400 rounded-xl text-xs font-bold border border-indigo-500/30 transition-all flex items-center gap-2"
                    >
                      <Download size={14} /> 현재 카피 복사
                    </button>
                  </div>
                </div>

                {/* Tabs Navigation */}
                <div className="flex flex-wrap gap-2 mb-6 p-1.5 bg-slate-950/50 rounded-2xl border border-slate-800/50">
                  {lmsTabs.map((tab, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveLmsTab(idx)}
                      className={`flex-1 min-w-[100px] px-4 py-3 rounded-xl text-[11px] font-black transition-all ${activeLmsTab === idx
                        ? 'bg-indigo-600 text-white shadow-lg blue-glow'
                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'
                        }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="relative p-8 bg-slate-950/80 rounded-2xl border border-indigo-500/10 shadow-inner group">
                  <div className="absolute top-4 right-4 text-[10px] font-mono text-indigo-500/50 font-black tracking-widest">
                    {lmsTabs[activeLmsTab].desc}
                  </div>
                  <motion.pre
                    key={activeLmsTab}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed font-sans italic"
                  >
                    {result.lms_copy_samples[activeLmsTab]}
                  </motion.pre>
                  <div className="mt-8 flex flex-col md:flex-row items-center justify-between gap-6 pt-6 border-t border-slate-800/50">
                    <div className="flex flex-wrap gap-4">
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                        <span className="text-[10px] font-bold text-slate-500">도달률 최적화</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                        <span className="text-[10px] font-bold text-slate-500">CTA 액션 유도</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                        <span className="text-[10px] font-bold text-slate-500">현장 특화 리포트 기반</span>
                      </div>
                    </div>

                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        setLeadForm(prev => ({ ...prev, site: fieldName }));
                        setLeadSource(`LMS 카피 (${lmsTabs[activeLmsTab].label})`);
                        setShowLeadModal(true);
                      }}
                      className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-black rounded-xl text-xs blue-glow transition-all flex items-center gap-2"
                    >
                      <Target size={14} /> 무료 모수 확인하기
                    </motion.button>
                  </div>
                </div>
              </div>

              {/* Dashboard Row 6: Hogangnono ChannelTalk Copy Sample with Tabs */}
              <div className="lg:col-span-12 glass p-8 rounded-3xl border-orange-500/20 bg-orange-900/5 mt-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                  <div>
                    <h3 className="text-xl font-black flex items-center gap-3 text-orange-400">
                      <MessageCircle className="text-orange-400" size={24} />
                      호갱노노 채널톡 최적화 카피 (3종)
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 italic">호갱노노 유저 성향에 맞춘 임팩트 있는 이모지 카피입니다.</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleRegenerateCopy}
                      disabled={isRegenerating}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold border border-slate-700 transition-all flex items-center gap-2"
                    >
                      <RefreshCw size={14} className={isRegenerating ? "animate-spin" : ""} /> AI 카피 재생성
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(result.channel_talk_samples[activeChannelTab]);
                        alert("카피가 클립보드에 복사되었습니다.");
                      }}
                      className="px-4 py-2 bg-orange-600/20 hover:bg-orange-600/40 text-orange-400 rounded-xl text-xs font-bold border border-orange-500/30 transition-all flex items-center gap-2"
                    >
                      <Download size={14} /> 현재 카피 복사
                    </button>
                  </div>
                </div>

                {/* Tabs Navigation */}
                <div className="flex flex-wrap gap-2 mb-6 p-1.5 bg-slate-950/50 rounded-2xl border border-slate-800/50">
                  {channelTabs.map((tab, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveChannelTab(idx)}
                      className={`flex-1 min-w-[100px] px-4 py-3 rounded-xl text-[11px] font-black transition-all ${activeChannelTab === idx
                        ? 'bg-orange-600 text-white shadow-lg'
                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'
                        }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="relative p-8 bg-slate-950/80 rounded-2xl border border-orange-500/10 shadow-inner group">
                  <div className="absolute top-4 right-4 text-[10px] font-mono text-orange-500/50 font-black tracking-widest">
                    {channelTabs[activeChannelTab].desc}
                  </div>
                  <motion.pre
                    key={activeChannelTab}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed font-sans font-medium"
                  >
                    {result.channel_talk_samples[activeChannelTab]}
                  </motion.pre>
                  <div className="mt-8 flex flex-col md:flex-row items-center justify-between gap-6 pt-6 border-t border-slate-800/50">
                    <div className="flex flex-wrap gap-4">
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
                        <span className="text-[10px] font-bold text-slate-500">호갱노노 고관여 유입용</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                        <span className="text-[10px] font-bold text-slate-500">비주얼 임팩트(Emoji)</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                        <span className="text-[10px] font-bold text-slate-500">서술형 키포인트 연동</span>
                      </div>
                    </div>

                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        setLeadForm(prev => ({ ...prev, site: fieldName }));
                        setLeadSource(`채널톡 카피 (${channelTabs[activeChannelTab].label})`);
                        setShowLeadModal(true);
                      }}
                      className="px-6 py-3 bg-orange-600 hover:bg-orange-500 text-white font-black rounded-xl text-xs shadow-lg shadow-orange-900/40 transition-all flex items-center gap-2"
                    >
                      <PieChart size={14} /> 무료 모수 확인하기
                    </motion.button>
                  </div>
                </div>
              </div>

              {/* Dashboard Row 7: Weekly Roadmap */}
              <div className="lg:col-span-12 glass p-8 rounded-3xl mt-6">
                <h3 className="text-lg font-bold mb-8 flex items-center gap-2">
                  <Zap className="text-yellow-500" size={18} /> 4주 집중 마케팅 로드맵
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  {(result.weekly_plan || []).map((step: string, idx: number) => (
                    <div key={idx} className="relative p-6 bg-slate-900/30 rounded-2xl border border-slate-800 group hover:border-blue-500/30 transition-all">
                      <div className="absolute -top-3 left-6 px-3 py-1 bg-blue-600 text-[10px] font-black rounded-full shadow-lg">WEEK 0{idx + 1}</div>
                      <p className="text-xs text-slate-300 font-medium leading-relaxed mt-2">{step.includes(': ') ? step.split(': ')[1] : step}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* 최하단 강력한 CTA 버튼 섹션 */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                className="lg:col-span-12 mt-12 mb-12"
              >
                <div className="relative p-1 bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 rounded-[2.5rem] shadow-[0_20px_50px_-15px_rgba(59,130,246,0.5)]">
                  <div className="bg-slate-950 rounded-[2.3rem] p-10 md:p-14 text-center overflow-hidden relative">
                    {/* 데코레이션 배경 */}
                    <div className="absolute top-0 left-0 w-full h-full bg-blue-600/5 pointer-events-none" />
                    <div className="absolute -top-24 -left-24 w-64 h-64 bg-blue-600/10 rounded-full blur-[80px]" />
                    <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-indigo-600/10 rounded-full blur-[80px]" />

                    <div className="relative z-10 max-w-2xl mx-auto">
                      <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600/20 rounded-full border border-blue-500/30 mb-8">
                        <Zap size={14} className="text-blue-400 fill-blue-400" />
                        <span className="text-[11px] font-black text-blue-300 uppercase tracking-widest">Premium Analysis Report</span>
                      </div>

                      <h2 className="text-3xl md:text-4xl font-black text-white mb-6 leading-tight">
                        데이터로 증명된 <span className="text-blue-500">필승 전략</span>,<br />
                        상세 리포트로 지금 바로 받으시겠습니까?
                      </h2>

                      <p className="text-slate-400 text-sm md:text-base mb-10 leading-relaxed font-medium">
                        단순한 요약 분석을 넘어, 지역별 수급 현황부터 매체별 예상 성과까지<br className="hidden md:block" />
                        전문가가 직접 검수한 <span className="text-white">실전용 정밀 대외비 리포트</span>를 보내드립니다.
                      </p>

                      <motion.button
                        whileHover={{ scale: 1.05, boxShadow: "0 0 40px rgba(59, 130, 246, 0.4)" }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => {
                          setLeadForm(prev => ({ ...prev, site: fieldName }));
                          setLeadSource("페이지 최하단 CTA");
                          setShowLeadModal(true);
                        }}
                        className="group relative inline-flex items-center justify-center px-10 py-6 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-black text-xl transition-all blue-glow overflow-hidden"
                      >
                        <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
                        <FileText className="mr-3" size={24} />
                        현장 정밀 진단 리포트 무료받기
                        <ChevronRight className="ml-3 group-hover:translate-x-2 transition-transform" size={24} />
                      </motion.button>

                      <div className="mt-8 flex items-center justify-center gap-6">
                        <div className="flex -space-x-3">
                          {[1, 2, 3, 4].map(i => (
                            <div key={i} className="w-8 h-8 rounded-full border-2 border-slate-950 bg-slate-800 flex items-center justify-center overflow-hidden">
                              <img src={`https://i.pravatar.cc/100?img=${i + 10}`} alt="user" />
                            </div>
                          ))}
                        </div>
                        <p className="text-[11px] text-slate-500 font-bold">방금 전 <span className="text-slate-300 underline">서울 마포구 현장</span> 리포트 신청 완료</p>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )
        }
      </main>

      {/* Success Notification Modal */}
      <AnimatePresence>
        {showSuccessModal && (
          <div className="fixed inset-0 z-[110] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowSuccessModal(false)}
              className="absolute inset-0 bg-slate-950/90 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-sm bg-gradient-to-b from-blue-900/20 to-slate-900 border border-blue-500/50 rounded-[2.5rem] p-10 overflow-hidden text-center shadow-[0_0_50px_-12px_rgba(59,130,246,0.5)]"
            >
              <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-blue-500 animate-pulse" />

              <div className="mb-6 relative">
                <div className="w-20 h-20 bg-blue-600/20 rounded-3xl flex items-center justify-center mx-auto border border-blue-500/30">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", damping: 10, stiffness: 100, delay: 0.2 }}
                  >
                    <CheckCircle2 className="text-blue-500" size={48} />
                  </motion.div>
                </div>
                {/* Decorative particles */}
                <div className="absolute -top-2 -right-2 w-4 h-4 bg-blue-500 rounded-full blur-xl opacity-50" />
                <div className="absolute -bottom-2 -left-2 w-4 h-4 bg-indigo-500 rounded-full blur-xl opacity-50" />
              </div>

              <h2 className="text-2xl font-black text-white mb-4">카피 생성 완료!</h2>
              <p className="text-sm text-slate-400 mb-8 leading-relaxed">
                현재 현장의 최신 데이터를 분석하여<br />
                <span className="text-blue-400 font-bold">10종의 마케팅 문구</span>가 성공적으로 업데이트되었습니다.
              </p>

              <button
                type="button"
                onClick={() => setShowSuccessModal(false)}
                className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-black text-sm transition-all shadow-lg blue-glow flex items-center justify-center group"
              >
                새로운 카피 확인하기
                <ChevronRight className="ml-2 group-hover:translate-x-1 transition-transform" size={16} />
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <footer className="relative z-10 border-t border-blue-900/30 py-12 mt-20">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-8">
          <div
            className="flex items-center gap-2 grayscale hover:grayscale-0 cursor-pointer transition-all hover:text-blue-400"
            onClick={() => window.location.href = "/"}
          >
            <Cpu size={20} />
            <span className="text-sm font-bold">분양알파고</span>
          </div>
          <p className="text-slate-500 text-xs">
            © 2026 Bunyang AlphaGo. 데이터 기반 분양 마케팅의 미래.
          </p>
          <div className="flex gap-6 text-slate-500 text-xs font-bold">
            <a href="#" className="hover:text-blue-400">Terms</a>
            <a href="#" className="hover:text-blue-400">Privacy</a>
            <a href="#" className="hover:text-blue-400">API</a>
          </div>
        </div>
      </footer>

      {/* Login Modal */}
      <AnimatePresence>
        {showLoginModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 text-slate-900">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowLoginModal(false)}
              className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-md bg-slate-900 border border-blue-500/20 rounded-[2.5rem] p-10 shadow-2xl overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600" />

              <div className="text-center mb-10">
                <div className="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-blue-500/30">
                  <ShieldCheck className="text-blue-500" size={32} />
                </div>
                <h2 className="text-2xl font-black text-white mb-2">분양 알파고 시작하기</h2>
                <p className="text-sm text-slate-500">소셜 계정으로 로그인하여 분석 리포트를 무제한으로 이용하세요.</p>
              </div>

              <div className="space-y-4">
                <button
                  onClick={() => handleSocialLogin('kakao')}
                  disabled={!!isLoggingIn}
                  className="w-full py-4 bg-[#FEE500] hover:bg-[#FADA00] text-[#191919] rounded-2xl font-black text-sm transition-all flex items-center justify-center gap-3 shadow-xl relative overflow-hidden"
                >
                  {isLoggingIn === 'kakao' ? <RefreshCw className="animate-spin" size={20} /> : (
                    <>
                      <img src="https://upload.wikimedia.org/wikipedia/commons/e/e3/KakaoTalk_logo.svg" alt="kakao" className="w-5 h-5" />
                      카카오로 3초만에 시작하기
                    </>
                  )}
                </button>

                <button
                  onClick={() => handleSocialLogin('google')}
                  disabled={!!isLoggingIn}
                  className="w-full py-4 bg-white hover:bg-slate-100 text-slate-900 rounded-2xl font-black text-sm transition-all flex items-center justify-center gap-3 shadow-xl relative"
                >
                  {isLoggingIn === 'google' ? <RefreshCw className="animate-spin" size={20} /> : (
                    <>
                      <img src="https://www.gstatic.com/images/branding/product/2x/googleg_48dp.png" alt="google" className="w-5 h-5" />
                      구글 계정으로 시작하기
                    </>
                  )}
                </button>

                <div className="relative my-4">
                  <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-800"></div></div>
                  <div className="relative flex justify-center text-[10px] uppercase"><span className="bg-slate-900 px-2 text-slate-500">or Debug Mode</span></div>
                </div>

                <button
                  onClick={() => {
                    setIsLoggingIn('credentials');
                    signIn('credentials', { email: 'admin@alphago.com', redirect: false }).then(() => {
                      setIsLoggingIn(null);
                      setShowLoginModal(false);
                    });
                  }}
                  disabled={!!isLoggingIn}
                  className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-slate-400 font-bold rounded-2xl text-[11px] transition-all border border-slate-700"
                >
                  {isLoggingIn === 'credentials' ? <RefreshCw className="animate-spin" size={14} /> : "테스트 계정으로 로그인 (admin@alphago.com)"}
                </button>
              </div>

              <div className="mt-10 pt-8 border-t border-slate-800 text-center">
                <p className="text-[10px] text-slate-600 uppercase tracking-widest font-bold">
                  Premium Analysis Service powered by AI
                </p>
                <div className="flex justify-center gap-4 mt-4">
                  <span className="text-[10px] text-slate-500 hover:text-blue-400 cursor-pointer transition-colors">이용약관</span>
                  <span className="text-[10px] text-slate-500 hover:text-blue-400 cursor-pointer transition-colors">개인정보처리방침</span>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      {/* History Modal */}
      <AnimatePresence>
        {showHistoryModal && (
          <div className="fixed inset-0 z-[120] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowHistoryModal(false)}
              className="absolute inset-0 bg-slate-950/90 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-2xl bg-slate-900 border border-blue-500/30 rounded-[2.5rem] p-10 shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
            >
              <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-blue-600 to-indigo-600" />

              <div className="mb-8 flex justify-between items-center">
                <div>
                  <h3 className="text-2xl font-black flex items-center gap-3">
                    <Database className="text-blue-500" size={28} /> 내 리포트 목록
                  </h3>
                  <p className="text-sm text-slate-400 mt-1">지금까지 분석한 현장의 데이터가 안전하게 저장되어 있습니다.</p>
                </div>
                <button onClick={() => setShowHistoryModal(false)} className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-500">
                  <LogOut size={20} />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {isFetchingHistory ? (
                  <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <RefreshCw className="animate-spin text-blue-500" size={32} />
                    <p className="text-slate-500 font-bold">리포트를 불러오는 중...</p>
                  </div>
                ) : history.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-30 text-center">
                    <Database size={64} />
                    <p className="text-slate-400 font-bold leading-relaxed">저장된 리포트가 없습니다.<br />첫 분석을 시작해 보세요.</p>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {history.map((entry) => (
                      <button
                        key={entry.id}
                        onClick={() => handleLoadHistory(entry)}
                        className="w-full p-6 bg-slate-950/50 rounded-2xl border border-slate-800 hover:border-blue-500/50 hover:bg-slate-900 transition-all text-left flex items-center justify-between group"
                      >
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-white font-bold group-hover:text-blue-400 transition-colors">{entry.field_name}</span>
                            <span className="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20 font-black">Score: {entry.score}</span>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-slate-500">
                            <span className="flex items-center gap-1"><MapPin size={12} /> {entry.address}</span>
                            <span className="flex items-center gap-1"><Zap size={12} /> {new Date(entry.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <ChevronRight className="text-slate-700 group-hover:text-blue-500 translate-x-0 group-hover:translate-x-1 transition-all" size={20} />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {showLeadModal && (
          <div className="fixed inset-0 z-[120] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowLeadModal(false)}
              className="absolute inset-0 bg-slate-950/90 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-lg bg-slate-900 border border-blue-500/30 rounded-[2.5rem] p-10 shadow-2xl overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-blue-600 to-indigo-600" />

              <div className="mb-8">
                <h3 className="text-2xl font-black mb-2 flex items-center gap-3">
                  <PieChart className="text-blue-500" size={28} /> 무료 모수 확인하기
                </h3>
                <p className="text-sm text-slate-400 leading-relaxed font-medium">
                  현장 인근 타겟 모수를 정밀 분석하여 리포트를 보내드립니다. <br />
                  아래 정보를 정확히 입력해주세요.
                </p>
              </div>

              <form onSubmit={handleLeadSubmit} className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-2 ml-1">이름</label>
                    <input
                      type="text"
                      required
                      value={leadForm.name}
                      onChange={e => setLeadForm({ ...leadForm, name: e.target.value })}
                      className={inputClass}
                      placeholder="성함 입력"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-2 ml-1">연락처</label>
                    <input
                      type="tel"
                      required
                      value={leadForm.phone}
                      onChange={e => setLeadForm({ ...leadForm, phone: e.target.value })}
                      className={inputClass}
                      placeholder="010-0000-0000"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-2 ml-1">직급</label>
                    <input
                      type="text"
                      required
                      value={leadForm.rank}
                      onChange={e => setLeadForm({ ...leadForm, rank: e.target.value })}
                      className={inputClass}
                      placeholder="예) 본부장, 팀장"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-2 ml-1">현장명</label>
                    <input
                      type="text"
                      required
                      value={leadForm.site}
                      onChange={e => setLeadForm({ ...leadForm, site: e.target.value })}
                      className={inputClass}
                      placeholder="현장 이름"
                    />
                  </div>
                </div>

                <div className="pt-4">
                  <button
                    type="submit"
                    disabled={isSubmittingLead}
                    className="w-full py-4 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white font-black rounded-2xl shadow-xl shadow-blue-900/40 transition-all flex items-center justify-center gap-3"
                  >
                    {isSubmittingLead ? (
                      <RefreshCw size={18} className="animate-spin" />
                    ) : (
                      <>신청하기 <ChevronRight size={18} /></>
                    )}
                  </button>
                  <p className="text-[10px] text-center text-slate-600 mt-4 leading-relaxed font-bold">집행 예산 및 타겟에 따른 실시간 모수 분석 데이터를 전달드립니다.</p>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Lead Success Modal */}
      <AnimatePresence>
        {showLeadSuccess && (
          <div className="fixed inset-0 z-[130] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowLeadSuccess(false)}
              className="absolute inset-0 bg-slate-950/90 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-sm bg-gradient-to-b from-emerald-900/20 to-slate-900 border border-emerald-500/50 rounded-[2.5rem] p-10 overflow-hidden text-center shadow-[0_0_50px_-12px_rgba(16,185,129,0.5)]"
            >
              <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-500 animate-pulse" />

              <div className="mb-6 relative">
                <div className="w-20 h-20 bg-emerald-600/20 rounded-3xl flex items-center justify-center mx-auto border border-emerald-500/30">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", damping: 10, stiffness: 100, delay: 0.2 }}
                  >
                    <CheckCircle2 className="text-emerald-500" size={48} />
                  </motion.div>
                </div>
                <div className="absolute -top-2 -right-2 w-4 h-4 bg-emerald-500 rounded-full blur-xl opacity-50" />
              </div>

              <h2 className="text-2xl font-black text-white mb-4">신청 완료!</h2>
              <p className="text-sm text-slate-400 mb-8 leading-relaxed">
                성공적으로 접수되었습니다.<br />
                담당 전문가가 <span className="text-emerald-400 font-bold">24시간 이내</span>에<br />
                정밀 분석 리포트를 송부해 드립니다.
              </p>

              <button
                type="button"
                onClick={() => setShowLeadSuccess(false)}
                className="w-full py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl font-black text-sm transition-all shadow-lg flex items-center justify-center group"
              >
                닫기
                <ChevronRight className="ml-2 group-hover:translate-x-1 transition-transform" size={16} />
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div >
  );
}

