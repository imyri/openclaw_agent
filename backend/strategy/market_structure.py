import pandas as pd
import numpy as np
import logging
import json

# Forensic JSON logging for the LLM's consumption
logger = logging.getLogger("openclaw.quant_engine")

class QuantitativeEngine:
    """
    The Math Engine for OpenClaw-Class.
    Strictly calculates invalidation-driven SMC concepts (FVG, MSS, BPR).
    """
    def __init__(self, data: pd.DataFrame):
        # Expects a standard OHLCV dataframe with a UTC DatetimeIndex
        self.df = data.copy()

    def detect_fair_value_gaps(self) -> pd.DataFrame:
        """
        Detects 3-candle imbalance zones (FVGs).
        Bullish FVG Mathematical Definition: Low_t > High_{t-2}
        Bearish FVG Mathematical Definition: High_t < Low_{t-2}
        """
        df = self.df
        
        # Bullish FVG: Current Low is higher than the High 2 candles ago + Momentum
        df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2)) & (df['Close'].shift(1) > df['Open'].shift(1))
        df['Bullish_FVG_Top'] = np.where(df['Bullish_FVG'], df['Low'], np.nan)
        df['Bullish_FVG_Btm'] = np.where(df['Bullish_FVG'], df['High'].shift(2), np.nan)
        
        # Bearish FVG: Current High is lower than the Low 2 candles ago + Momentum
        df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2)) & (df['Close'].shift(1) < df['Open'].shift(1))
        df['Bearish_FVG_Top'] = np.where(df['Bearish_FVG'], df['Low'].shift(2), np.nan)
        df['Bearish_FVG_Btm'] = np.where(df['Bearish_FVG'], df['High'], np.nan)
        
        return df

    def map_market_structure(self, swing_lookback=5) -> pd.DataFrame:
        """
        Calculates Fractal Swing Highs and Swing Lows to identify Market Structure Shifts (MSS).
        """
        df = self.df
        
        # Swing High: Current High is the max of the rolling window
        df['Swing_High'] = df['High'] == df['High'].rolling(window=swing_lookback*2+1, center=True).max()
        # Swing Low: Current Low is the min of the rolling window
        df['Swing_Low'] = df['Low'] == df['Low'].rolling(window=swing_lookback*2+1, center=True).min()
        
        # Forward fill the last known structural points
        df['Last_Swing_High'] = df['High'].where(df['Swing_High']).ffill()
        df['Last_Swing_Low'] = df['Low'].where(df['Swing_Low']).ffill()
        
        # Bullish MSS: Close breaks above last Swing High with displacement (Large Body)
        df['Bullish_MSS'] = (df['Close'] > df['Last_Swing_High']) & (df['Close'] - df['Open'] > (df['High'] - df['Low']) * 0.7)
        
        # Bearish MSS: Close breaks below last Swing Low with displacement
        df['Bearish_MSS'] = (df['Close'] < df['Last_Swing_Low']) & (df['Open'] - df['Close'] > (df['High'] - df['Low']) * 0.7)
        
        return df

    def run_execution_checklist(self) -> dict:
        """
        The final filter. Scans the latest candlestick.
        Returns a highly structured JSON dictionary of the current state for the LLM Brain.
        """
        self.df = self.detect_fair_value_gaps()
        self.df = self.map_market_structure()
        if self.df.empty or len(self.df) < 5:
            print("Waiting for more candle data...")
            return {"status": "WAITING_DATA"}
        latest = self.df.iloc[-1]
        
        # Only flag a POI if the math proves it exists
        valid_setup = False
        setup_type = None
        
        if latest['Bullish_MSS'] and latest['Bullish_FVG']:
            valid_setup = True
            setup_type = "BULLISH_MSS_WITH_DISPLACEMENT"
        elif latest['Bearish_MSS'] and latest['Bearish_FVG']:
            valid_setup = True
            setup_type = "BEARISH_MSS_WITH_DISPLACEMENT"

        state_report = {
            "timestamp": str(self.df.index[-1]),
            "valid_poi_found": valid_setup,
            "setup_type": setup_type,
            "closest_bullish_fvg": {"top": latest['Bullish_FVG_Top'], "bottom": latest['Bullish_FVG_Btm']},
            "closest_bearish_fvg": {"top": latest['Bearish_FVG_Top'], "bottom": latest['Bearish_FVG_Btm']},
            "last_swing_high": latest['Last_Swing_High'],
            "last_swing_low": latest['Last_Swing_Low']
        }
        
        logger.info(f"Market Structure State: {json.dumps(state_report)}")
        return state_report