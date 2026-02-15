export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/ai-feed";
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function fetchRiskState() {
  return fetch(`${API_URL}/api/risk-state`)
    .then(res => res.json())
    .catch(err => {
      console.error("Failed to fetch risk state", err);
      return { daily_pnl_r: 0, killswitch_active: false, active_trades: [] };
    });
}
