export interface AIThought {
  timestamp: string;
  symbol: string;
  action: "LONG" | "SHORT" | "WAIT";
  confidence: number;
  reasoning: string;
  status: "WAIT" | "IGNORED" | "REJECTED" | "EXECUTED" | "FAILED" | "KILLSWITCH";
  price: number | null;
  size: number | null;
  pnl_r: number | null;
}

function badgeClass(status: AIThought["status"]) {
  if (status === "EXECUTED") return "bg-emerald-500/10 text-emerald-500";
  if (status === "WAIT" || status === "IGNORED") return "bg-amber-500/10 text-amber-500";
  return "bg-rose-500/10 text-rose-500";
}

export default function Terminal({ feed }: { feed: AIThought[] }) {
  return (
    <section className="bg-neutral-900 rounded-lg border border-neutral-800 p-6 h-[600px] flex flex-col">
      <h2 className="text-sm text-neutral-500 uppercase tracking-widest mb-4">Live Execution Feed</h2>
      <div className="overflow-y-auto space-y-4 flex-1 pr-2 custom-scrollbar">
        {feed.length === 0 ? (
          <p className="text-neutral-600 animate-pulse font-mono text-sm">Awaiting market structure shift...</p>
        ) : (
          feed.map((log, idx) => (
            <div key={idx} className="bg-neutral-950 p-4 rounded border border-neutral-800 flex flex-col gap-2 font-mono">
              <div className="flex justify-between items-center text-xs">
                <span className="text-neutral-500">
                  {log.timestamp} | {log.symbol}
                </span>
                <span className={`px-2 py-1 rounded font-bold ${badgeClass(log.status)}`}>
                  {log.status}
                </span>
              </div>
              <p className="text-sm text-neutral-300 leading-relaxed">
                <span className="text-indigo-400 mr-2">{">>"}</span>
                {log.action} ({log.confidence}%) at {log.price ?? "-"} | {log.reasoning}
              </p>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
