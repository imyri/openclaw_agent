import { ShieldAlert, TrendingUp } from "lucide-react";

interface StatsProps {
  pnl: number;
  killswitch: boolean;
}

export default function StatsPanel({ pnl, killswitch }: StatsProps) {
  return (
    <div className="flex gap-6">
      <div className="bg-neutral-900 px-6 py-4 rounded-lg border border-neutral-800 flex items-center gap-4">
        <TrendingUp className={pnl >= 0 ? "text-emerald-500" : "text-rose-500"} />
        <div>
          <span className="text-xs text-neutral-500 block uppercase tracking-wider">Daily PnL</span>
          <span className={`text-2xl font-bold ${pnl >= 0 ? "text-emerald-400" : "text-rose-500"}`}>
            {pnl > 0 ? "+" : ""}{pnl} R
          </span>
        </div>
      </div>

      <div className="bg-neutral-900 px-6 py-4 rounded-lg border border-neutral-800 flex items-center gap-4">
        <ShieldAlert className={killswitch ? "text-rose-500" : "text-emerald-500"} />
        <div>
          <span className="text-xs text-neutral-500 block uppercase tracking-wider">Risk Guard</span>
          <span className={`text-2xl font-bold ${killswitch ? "text-rose-500" : "text-emerald-400"}`}>
            {killswitch ? "HALTED" : "ARMED"}
          </span>
        </div>
      </div>
    </div>
  );
}