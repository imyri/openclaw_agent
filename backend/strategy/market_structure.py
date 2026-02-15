import json
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from core.config import settings
from models.schemas import FVGZone, MarketState

logger = logging.getLogger("openclaw.quant_engine")


class QuantitativeEngine:
    """
    Calculates deterministic market-structure and FVG signals.
    """

    def __init__(self, data: pd.DataFrame):
        self.df = data.copy()

    @staticmethod
    def _maybe_float(value):
        if pd.isna(value):
            return None
        return float(value)

    def detect_fair_value_gaps(self) -> pd.DataFrame:
        df = self.df
        df["Bullish_FVG"] = (df["Low"] > df["High"].shift(2)) & (df["Close"].shift(1) > df["Open"].shift(1))
        df["Bullish_FVG_Top"] = np.where(df["Bullish_FVG"], df["Low"], np.nan)
        df["Bullish_FVG_Btm"] = np.where(df["Bullish_FVG"], df["High"].shift(2), np.nan)

        df["Bearish_FVG"] = (df["High"] < df["Low"].shift(2)) & (df["Close"].shift(1) < df["Open"].shift(1))
        df["Bearish_FVG_Top"] = np.where(df["Bearish_FVG"], df["Low"].shift(2), np.nan)
        df["Bearish_FVG_Btm"] = np.where(df["Bearish_FVG"], df["High"], np.nan)
        return df

    def map_market_structure(self, swing_lookback: int = 5) -> pd.DataFrame:
        df = self.df
        window = swing_lookback * 2 + 1

        df["Swing_High"] = df["High"] == df["High"].rolling(window=window, center=True).max()
        df["Swing_Low"] = df["Low"] == df["Low"].rolling(window=window, center=True).min()

        df["Last_Swing_High"] = df["High"].where(df["Swing_High"]).ffill()
        df["Last_Swing_Low"] = df["Low"].where(df["Swing_Low"]).ffill()

        body = (df["Close"] - df["Open"]).abs()
        range_size = (df["High"] - df["Low"]).replace(0, np.nan)

        df["Bullish_MSS"] = (df["Close"] > df["Last_Swing_High"]) & (body / range_size > 0.7) & (
            df["Close"] > df["Open"]
        )
        df["Bearish_MSS"] = (df["Close"] < df["Last_Swing_Low"]) & (body / range_size > 0.7) & (
            df["Close"] < df["Open"]
        )

        return df

    def run_execution_checklist(self) -> MarketState:
        self.df = self.detect_fair_value_gaps()
        self.df = self.map_market_structure()
        if self.df.empty or len(self.df) < 5:
            return MarketState(
                timestamp=datetime.now(timezone.utc),
                symbol=settings.TRADING_SYMBOL,
                timeframe=settings.TRADING_TIMEFRAME,
                valid_poi_found=False,
            )

        latest = self.df.iloc[-1]
        valid_setup = False
        setup_type = None
        stop_reference = None

        if bool(latest.get("Bullish_MSS")) and bool(latest.get("Bullish_FVG")):
            valid_setup = True
            setup_type = "BULLISH_MSS_WITH_DISPLACEMENT"
            stop_reference = self._maybe_float(latest.get("Bullish_FVG_Btm"))
        elif bool(latest.get("Bearish_MSS")) and bool(latest.get("Bearish_FVG")):
            valid_setup = True
            setup_type = "BEARISH_MSS_WITH_DISPLACEMENT"
            stop_reference = self._maybe_float(latest.get("Bearish_FVG_Top"))

        state = MarketState(
            timestamp=self.df.index[-1].to_pydatetime(),
            symbol=settings.TRADING_SYMBOL,
            timeframe=settings.TRADING_TIMEFRAME,
            valid_poi_found=valid_setup,
            setup_type=setup_type,
            stop_reference=stop_reference,
            closest_bullish_fvg=FVGZone(
                top=self._maybe_float(latest.get("Bullish_FVG_Top")),
                bottom=self._maybe_float(latest.get("Bullish_FVG_Btm")),
            ),
            closest_bearish_fvg=FVGZone(
                top=self._maybe_float(latest.get("Bearish_FVG_Top")),
                bottom=self._maybe_float(latest.get("Bearish_FVG_Btm")),
            ),
            last_swing_high=self._maybe_float(latest.get("Last_Swing_High")),
            last_swing_low=self._maybe_float(latest.get("Last_Swing_Low")),
        )
        logger.info("Market structure state: %s", json.dumps(state.model_dump(mode="json")))
        return state
