import asyncio
import ccxt.pro as ccxt
import pandas as pd
import logging
from zoneinfo import ZoneInfo

logger = logging.getLogger("openclaw.data_feed")

class LiveDataFeed:
    """
    Maintains a continuous WebSocket connection to Binance.
    Strictly enforces UTC timezone and prevents repainting by locking closed candles.
    """
    def __init__(self, symbol: str = "BTC/USDT", timeframe: str = "5m", max_candles: int = 100):
        self.symbol = symbol
        self.timeframe = timeframe
        self.max_candles = max_candles
        
        # ccxt.pro allows asynchronous websocket streaming
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.df = pd.DataFrame()
        self.last_closed_candle_time = None

    async def start_stream(self, on_candle_close_callback):
        """
        Streams live OHLCV data. Triggers the callback ONLY when a candle permanently closes.
        """
        logger.info(f"Starting WebSocket Data Feed for {self.symbol} ({self.timeframe})...")
        
        while True:
            try:
                # 1. Fetch live tick data via WebSocket
                ohlcv = await self.exchange.watch_ohlcv(self.symbol, self.timeframe)
                
                # 2. Convert to DataFrame and enforce UTC DatetimeIndex
                new_df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                new_df['timestamp'] = pd.to_datetime(new_df['timestamp'], unit='ms', utc=True)
                new_df.set_index('timestamp', inplace=True)
                
                self.df = new_df.tail(self.max_candles)
                
                # 3. The Anti-Repaint Lock Mechanism
                latest_timestamp = self.df.index[-1]
                
                if self.last_closed_candle_time is None:
                    # Initialization state
                    self.last_closed_candle_time = latest_timestamp
                    continue
                    
                # If the timestamp moves forward, the previous candle has definitively closed
                if latest_timestamp > self.last_closed_candle_time:
                    logger.info(f"Candle closed at {self.last_closed_candle_time}. Triggering Quantitative Engine.")
                    
                    # Lock the dataframe to only include fully closed candles
                    locked_df = self.df[self.df.index <= self.last_closed_candle_time].copy()
                    
                    # Trigger the rest of the system asynchronously
                    asyncio.create_task(on_candle_close_callback(locked_df))
                    
                    # Update the lock marker
                    self.last_closed_candle_time = latest_timestamp

            except Exception as e:
                logger.error(f"WebSocket Stream Interrupted: {e}. Attempting reconnection...")
                await asyncio.sleep(5) # Exponential backoff would be added here in prod