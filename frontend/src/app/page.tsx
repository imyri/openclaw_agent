"use client";

import { useEffect, useState } from "react";
import StatsPanel from "../components/StatsPanel";
import Terminal, { AIThought } from "../components/Terminal";
import { fetchRiskState, WS_URL } from "../services/api";

export default function CommandCentre() {
  const [feed, setFeed] = useState<AIThought[]>([]);
  const [pnlState, setPnlState] = useState({ pnl: 0, killswitch: false });

  useEffect(() => {
    fetchRiskState().then(data => 
      setPnlState({ pnl: data.daily_pnl_r, killswitch: data.killswitch_active })
    );

    const ws = new WebSocket(WS_URL);
    ws.onmessage = (event) => {
      try {
        const newThought: AIThought = JSON.parse(event.data);
        setFeed((prev) => [newThought, ...prev].slice(0, 50));
      } catch (e) {
        console.error("WebSocket payload error:", e);
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-200 p-8">
      <header className="flex justify-between items-center mb-8 border-b border-neutral-800 pb-6">
        <div>
          <h1 className="text-3xl font-light tracking-widest text-white">
            OPENCLAW <span className="text-emerald-500 font-bold">SYSTEMS</span>
          </h1>
          <p className="text-neutral-500 text-sm mt-1 font-mono">Autonomous SMC/ICT Execution Agent</p>
        </div>
        <StatsPanel pnl={pnlState.pnl} killswitch={pnlState.killswitch} />
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          {/* Future Chart Component will go here */}
          <div className="bg-neutral-900 rounded-lg border border-neutral-800 h-[600px] flex items-center justify-center">
            <span className="text-neutral-600 font-mono text-sm">TradingView Widget Pending</span>
          </div>
        </div>
        <div className="lg:col-span-1">
          <Terminal feed={feed} />
        </div>
      </main>
    </div>
  );
}