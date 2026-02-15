from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


ActionType = Literal["LONG", "SHORT", "WAIT"]
EventStatus = Literal["WAIT", "IGNORED", "REJECTED", "EXECUTED", "FAILED", "KILLSWITCH"]


class FVGZone(BaseModel):
    top: float | None = None
    bottom: float | None = None


class MarketState(BaseModel):
    timestamp: datetime
    symbol: str
    timeframe: str
    valid_poi_found: bool
    setup_type: str | None = None
    stop_reference: float | None = None
    closest_bullish_fvg: FVGZone = Field(default_factory=FVGZone)
    closest_bearish_fvg: FVGZone = Field(default_factory=FVGZone)
    last_swing_high: float | None = None
    last_swing_low: float | None = None


class AIDecision(BaseModel):
    action: ActionType
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    entry_poi: float | None = None
    target_liquidity: float | None = None
    stop_reference: float | None = None


class ExecutionEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    action: ActionType
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    status: EventStatus
    price: float | None = None
    size: float | None = None
    pnl_r: float | None = None


class RiskState(BaseModel):
    daily_pnl_r: float
    max_drawdown_limit: float
    killswitch_active: bool
    active_trades: list[dict]
