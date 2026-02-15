from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from core.config import settings
from core.database import TradeRecord
from core.exchange import get_exchange_instance
from models.schemas import AIDecision

logger = logging.getLogger("openclaw.position_manager")


class PositionManager:
    """
    Handles order validation, RR checks, sizing, and testnet execution.
    """

    def __init__(self, risk_per_trade_percent: float = 0.01, min_rr_ratio: float = 3.0):
        self.exchange = get_exchange_instance()
        self.risk_percent = risk_per_trade_percent
        self.min_rr_ratio = min_rr_ratio

    def validate_and_execute(
        self,
        ai_decision: AIDecision,
        symbol: str,
        current_price: float,
        account_balance: float,
        db: Session,
    ) -> dict:
        if ai_decision.action not in ("LONG", "SHORT"):
            return {"status": "ignored", "reason": "AI decided WAIT."}

        entry = ai_decision.entry_poi or current_price
        target = ai_decision.target_liquidity
        stop_reference = ai_decision.stop_reference

        if target is None or stop_reference is None:
            return {"status": "rejected", "reason": "Missing target_liquidity or stop_reference."}

        if ai_decision.action == "LONG":
            stop_loss = stop_reference * 0.999
            risk_distance = entry - stop_loss
            reward_distance = target - entry
        else:
            stop_loss = stop_reference * 1.001
            risk_distance = stop_loss - entry
            reward_distance = entry - target

        if risk_distance <= 0 or reward_distance <= 0:
            logger.error("Invalid trade math: risk_distance=%s reward_distance=%s", risk_distance, reward_distance)
            return {"status": "rejected", "reason": "Invalid risk/reward distances."}

        rr_ratio = reward_distance / risk_distance
        if rr_ratio < self.min_rr_ratio:
            return {
                "status": "rejected",
                "reason": f"Insufficient RR ratio: {rr_ratio:.2f}. Required: {self.min_rr_ratio:.2f}.",
            }

        monetary_risk = account_balance * self.risk_percent
        position_size = monetary_risk / risk_distance
        if position_size <= 0:
            return {"status": "rejected", "reason": "Computed position size <= 0."}

        execution_result = self._place_binance_orders(
            symbol=symbol,
            action=ai_decision.action,
            amount=position_size,
            stop_loss=stop_loss,
            take_profit=target,
        )

        trade_record = TradeRecord(
            symbol=symbol,
            action=ai_decision.action,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=target,
            position_size=position_size,
            status="OPEN" if execution_result["status"] == "executed" else "FAILED",
            exchange_order_id=execution_result.get("entry_order_id"),
        )
        db.add(trade_record)
        db.commit()
        db.refresh(trade_record)

        execution_result["position_size"] = position_size
        execution_result["entry_price"] = entry
        execution_result["trade_id"] = trade_record.id
        return execution_result

    def _place_binance_orders(
        self,
        symbol: str,
        action: str,
        amount: float,
        stop_loss: float,
        take_profit: float,
    ) -> dict:
        side = "buy" if action == "LONG" else "sell"
        inverse_side = "sell" if side == "buy" else "buy"

        if not settings.ENABLE_TESTNET:
            return {"status": "failed", "reason": "ENABLE_TESTNET is false. Execution blocked."}

        if not settings.EXECUTE_ORDERS:
            return {
                "status": "executed",
                "entry_order_id": "paper-order",
                "reason": "EXECUTE_ORDERS disabled; simulated fill.",
            }

        try:
            entry_order = self.exchange.create_order(symbol, "MARKET", side, amount)
            sl_order = self.exchange.create_order(
                symbol,
                "STOP_MARKET",
                inverse_side,
                amount,
                None,
                {"stopPrice": stop_loss, "closePosition": True},
            )
            tp_order = self.exchange.create_order(
                symbol,
                "TAKE_PROFIT_MARKET",
                inverse_side,
                amount,
                None,
                {"stopPrice": take_profit, "closePosition": True},
            )
            logger.info(
                "Executed %s %s on testnet. Entry=%s SL=%s TP=%s",
                action,
                symbol,
                entry_order.get("id"),
                sl_order.get("id"),
                tp_order.get("id"),
            )
            return {
                "status": "executed",
                "entry_order_id": entry_order.get("id"),
                "stop_order_id": sl_order.get("id"),
                "tp_order_id": tp_order.get("id"),
            }
        except Exception as exc:
            logger.critical("CCXT testnet execution failed: %s", exc)
            return {"status": "failed", "reason": str(exc)}
