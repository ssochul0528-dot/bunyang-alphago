"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
    Terminal,
    Activity,
    Send,
    Search,
    Cpu,
    CheckCircle2,
    XCircle,
    ArrowLeft,
    ChevronRight
} from "lucide-react";
import Link from "next/link";

export default function TestPage() {
    const [mounted, setMounted] = useState(false);
    const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
    const [searchQuery, setSearchQuery] = useState("힐스테이트");
    const [lastResponse, setLastResponse] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        setMounted(true);
        checkApi();
    }, []);

    const checkApi = async () => {
        try {
            const res = await fetch("http://localhost:8000/");
            if (res.ok) setApiStatus("online");
            else setApiStatus("offline");
        } catch (e) {
            setApiStatus("offline");
        }
    };

    const runSearchTest = async () => {
        setIsLoading(true);
        try {
            const res = await fetch(`http://localhost:8000/search-sites?q=${encodeURIComponent(searchQuery)}`);
            const data = await res.json();
            setLastResponse(data);
        } catch (e) {
            setLastResponse({ error: "Search failed", details: e });
        } finally {
            setIsLoading(false);
        }
    };

    const runAnalysisTest = async () => {
        setIsLoading(true);
        try {
            const res = await fetch("http://localhost:8000/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    field_name: "테스트 현장",
                    address: "경기도 의정부시 테스트동",
                    product_category: "아파트",
                    sales_stage: "선착순",
                    down_payment: "10%",
                    interest_benefit: "무이자",
                    additional_benefits: ["발코니 확장", "중도금 무이자"],
                    main_concern: "DB 수량 부족",
                    existing_media: ["인스타그램"],
                    sales_price: 2500,
                    target_area_price: 2800,
                    down_payment_amount: 3000,
                    supply_volume: 500
                })
            });
            const data = await res.json();
            setLastResponse(data);
        } catch (e) {
            setLastResponse({ error: "Analysis failed", details: e });
        } finally {
            setIsLoading(false);
        }
    };

    if (!mounted) return null;

    return (
        <div className="min-h-screen bg-[#020617] text-white font-sans selection:bg-blue-500/30">
            {/* Background Decor */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-900/10 blur-[150px] rounded-full" />
                <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-900/10 blur-[150px] rounded-full" />
            </div>

            <main className="relative z-10 max-w-5xl mx-auto px-6 py-12">
                {/* Navigation */}
                <div className="mb-12">
                    <Link href="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-blue-400 transition-colors group">
                        <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                        <span className="text-sm font-medium">메인 페이지로 돌아가기</span>
                    </Link>
                </div>

                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
                    <div>
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-2.5 bg-blue-600 rounded-xl blue-glow">
                                <Terminal size={24} className="text-white" />
                            </div>
                            <h1 className="text-3xl font-black tracking-tighter">System Diagnostic <span className="text-blue-500">Board</span></h1>
                        </div>
                        <p className="text-slate-400 text-sm max-w-md">
                            분양알파고 API 서버와 데이터 스트림의 정밀 진단을 위한 테스트 환경입니다.
                            현장 검색 및 AI 분석 로직의 응답성을 확인하세요.
                        </p>
                    </div>

                    <div className="flex items-center gap-4 bg-slate-900/50 border border-slate-800 p-4 rounded-2xl">
                        <div className="flex items-center gap-2">
                            <Activity size={18} className={apiStatus === 'online' ? 'text-green-500 animate-pulse' : 'text-slate-500'} />
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Server Status:</span>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 ${apiStatus === 'online' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                            apiStatus === 'offline' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                                'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                            }`}>
                            {apiStatus === 'online' && <CheckCircle2 size={10} />}
                            {apiStatus === 'offline' && <XCircle size={10} />}
                            {apiStatus}
                        </div>
                    </div>
                </div>

                {/* Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Controls */}
                    <div className="lg:col-span-5 space-y-6">
                        <section className="glass p-6 rounded-3xl border-slate-800/50">
                            <h3 className="text-sm font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                                <Search size={14} /> Site Search Test
                            </h3>
                            <div className="space-y-4">
                                <div className="relative">
                                    <input
                                        type="text"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        placeholder="검색어 입력..."
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500/50 transition-all font-medium"
                                    />
                                </div>
                                <button
                                    onClick={runSearchTest}
                                    disabled={isLoading}
                                    className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2 text-sm"
                                >
                                    {isLoading ? <Cpu className="animate-spin" size={16} /> : <ChevronRight size={16} />}
                                    검색 API 실행
                                </button>
                            </div>
                        </section>

                        <section className="glass p-6 rounded-3xl border-slate-800/50">
                            <h3 className="text-sm font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                                <Cpu size={14} /> AI Analysis Test
                            </h3>
                            <p className="text-xs text-slate-400 mb-6 leading-relaxed">
                                테스트 데이터를 사용하여 AI 분석 엔진을 호출합니다.
                                매력 지수 계산 및 매체 믹스 추출 로직을 검증합니다.
                            </p>
                            <button
                                onClick={runAnalysisTest}
                                disabled={isLoading}
                                className="w-full bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl border border-slate-700 transition-all flex items-center justify-center gap-2 text-sm"
                            >
                                {isLoading ? <Cpu className="animate-spin" size={16} /> : <Send size={16} />}
                                전체 분석 시뮬레이션
                            </button>
                        </section>

                        <section className="p-6 bg-blue-900/10 border border-blue-500/20 rounded-3xl">
                            <h4 className="text-xs font-black text-blue-400 uppercase tracking-widest mb-2">Endpoint Info</h4>
                            <ul className="text-[11px] text-blue-200/60 font-mono space-y-1">
                                <li>GET /search-sites?q=...</li>
                                <li>POST /analyze</li>
                                <li>GET /site-details/:id</li>
                            </ul>
                        </section>
                    </div>

                    {/* Response Viewer */}
                    <div className="lg:col-span-7 flex flex-col">
                        <div className="flex-1 glass border-slate-800/50 rounded-3xl flex flex-col overflow-hidden min-h-[500px]">
                            <div className="bg-slate-950/80 px-6 py-4 border-b border-slate-800/50 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-red-500/50" />
                                    <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                                    <div className="w-3 h-3 rounded-full bg-green-500/50" />
                                    <span className="ml-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">API Response Viewer</span>
                                </div>
                                {lastResponse && (
                                    <button
                                        onClick={() => setLastResponse(null)}
                                        className="text-[10px] font-bold text-slate-500 hover:text-white transition-colors"
                                    >
                                        Clear
                                    </button>
                                )}
                            </div>
                            <div className="flex-1 p-6 font-mono text-xs overflow-auto custom-scrollbar">
                                {lastResponse ? (
                                    <motion.pre
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="text-blue-300 whitespace-pre-wrap"
                                    >
                                        {JSON.stringify(lastResponse, null, 2)}
                                    </motion.pre>
                                ) : (
                                    <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-4">
                                        <Terminal size={48} strokeWidth={1} />
                                        <p className="font-sans font-medium">명령을 실행하여 API 응답을 확인하세요</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            <style jsx global>{`
        .glass {
          background: rgba(15, 23, 42, 0.6);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(51, 65, 85, 0.5);
        }
        .blue-glow {
          box-shadow: 0 0 20px rgba(37, 99, 235, 0.4);
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(15, 23, 42, 0.5);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(51, 65, 85, 0.5);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(51, 65, 85, 0.8);
        }
      `}</style>
        </div>
    );
}
