import ccxt
import logging

logger = logging.getLogger("openclaw.position_manager")

class PositionManager:
    """
    Handles order routing, position sizing, and RR math.
    """
    def __init__(self, api_key: str, secret: str, risk_per_trade_percent: float = 0.01):
        self.exchange = ccxt.binanceusdm({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
        })
        self.risk_percent = risk_per_trade_percent
        self.min_rr_ratio = 3.0 # Hardcoded 1:3 RR

    def validate_and_execute(self, ai_decision: dict, current_price: float, account_balance: float):
        """
        Intercepts the AI's JSON output. If the math doesn't make sense, it rejects the trade.
        """
        if ai_decision.get("action") not in ["LONG", "SHORT"]:
            return {"status": "ignored", "reason": "AI decided to WAIT or invalid action."}

        action = ai_decision["action"]
        entry = current_price # Simplified for market execution
        target = float(ai_decision.get("target_liquidity"))
        fvg_level = float(ai_decision["reasoning_data"]["closest_fvg"]) # Assume AI passes this
        
        # 1. Math: Calculate Stop Loss (Placed just outside the FVG/OB)
        if action == "LONG":
            stop_loss = fvg_level * 0.999 # Add a tiny spread cushion
            risk_distance = entry - stop_loss
            reward_distance = target - entry
        else: # SHORT
            stop_loss = fvg_level * 1.001
            risk_distance = stop_loss - entry
            reward_distance = entry - target

        if risk_distance <= 0 or reward_distance <= 0:
            logger.error("Invalid Math: Risk or Reward distance is negative.")
            return {"status": "rejected", "reason": "Mathematical error in AI targets."}

        # 2. Risk Shield: Enforce 1:3 RR
        actual_rr = reward_distance / risk_distance
        if actual_rr < self.min_rr_ratio:
            logger.warning(f"Trade Rejected. Required RR: 1:3. Actual RR: 1:{round(actual_rr, 2)}.")
            return {"status": "rejected", "reason": "Insufficient Risk/Reward Ratio."}

        # 3. Math: Calculate Position Size based on Account Balance
        monetary_risk = account_balance * self.risk_percent
        position_size = monetary_risk / risk_distance
        
        # 4. Execution via CCXT
        return self._place_binance_orders("BTC/USDT", action, position_size, stop_loss, target)

    def _place_binance_orders(self, symbol: str, action: str, amount: float, sl: float, tp: float):
        """
        Executes the trade on Binance Futures using ccxt.
        Places entry, then attaches STOP_MARKET and TAKE_PROFIT_MARKET orders.
        """
        side = 'buy' if action == 'LONG' else 'sell'
        inverted_side = 'sell' if side == 'buy' else 'buy'

        try:
            # Place Market Entry
            entry_order = self.exchange.create_order(symbol, 'MARKET', side, amount)
            
            # Place Stop Loss (Must use closePosition=True for Futures)
            sl_params = {'stopPrice': sl, 'closePosition': True}
            sl_order = self.exchange.create_order(symbol, 'STOP_MARKET', inverted_side, amount, None, sl_params)
            
            # Place Take Profit
            tp_params = {'stopPrice': tp, 'closePosition': True}
            tp_order = self.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', inverted_side, amount, None, tp_params)

            logger.info(f"SUCCESS: Executed {action} on {symbol}. SL: {sl}, TP: {tp}")
            return {"status": "executed", "entry": entry_order['id']}
            
        except Exception as e:
            logger.critical(f"CCXT Execution Failed: {e}")
            return {"status": "failed", "reason": str(e)}