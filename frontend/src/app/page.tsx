"use client";

import { useEffect, useRef, useState } from "react";

import StatsPanel from "../components/StatsPanel";
import Terminal, { AIThought } from "../components/Terminal";
import { fetchRiskState, WS_URL } from "../services/api";

export default function CommandCentre() {
  const [feed, setFeed] = useState<AIThought[]>([]);
  const [pnlState, setPnlState] = useState({ pnl: 0, killswitch: false });
  const reconnectRef = useRef<number>(0);
  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetchRiskState().then((data) => {
      setPnlState({ pnl: data.daily_pnl_r, killswitch: data.killswitch_active });
    });

    const connect = () => {
      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        reconnectRef.current = 0;
      };

      socket.onmessage = (event) => {
        try {
          const next: AIThought = JSON.parse(event.data);
          setFeed((prev) => [next, ...prev].slice(0, 100));
        } catch (error) {
          console.error("WebSocket payload error:", error);
        }
      };

      socket.onclose = () => {
        const attempt = Math.min(reconnectRef.current, 6);
        const waitMs = Math.min(1000 * 2 ** attempt, 30000);
        reconnectRef.current += 1;
        timerRef.current = setTimeout(connect, waitMs);
      };
    };

    connect();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      socketRef.current?.close();
    };
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
          <div className="bg-neutral-900 rounded-lg border border-neutral-800 h-[600px] overflow-hidden">
            <iframe
              title="BTCUSDT Chart"
              src="https://s.tradingview.com/widgetembed/?symbol=BINANCE%3ABTCUSDT&interval=5&hidesidetoolbar=1&symboledit=1&saveimage=0&toolbarbg=0f172a&theme=dark&style=1&timezone=Etc%2FUTC&studies=[]&hideideas=1"
              className="w-full h-full"
            />
          </div>
        </div>
        <div className="lg:col-span-1">
          <Terminal feed={feed} />
        </div>
      </main>
    </div>
  );
}
