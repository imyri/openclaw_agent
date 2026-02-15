import asyncio
import logging

import ccxt.async_support as ccxt
import pandas as pd

from core.config import settings

logger = logging.getLogger("openclaw.data_feed")


class LiveDataFeed:
    """
    Async OHLCV polling feed with anti-repaint close-candle locking.
    """

    def __init__(self, symbol: str, timeframe: str, max_candles: int = 100, poll_seconds: int = 3):
        self.symbol = symbol
        self.timeframe = timeframe
        self.max_candles = max_candles
        self.poll_seconds = poll_seconds
        self.exchange = ccxt.binanceusdm({"enableRateLimit": True})
        if settings.ENABLE_TESTNET:
            self.exchange.set_sandbox_mode(True)
            logger.info("TESTNET MODE ENABLED for market data polling.")
        self.df = pd.DataFrame()
        self.last_closed_candle_time = None

    async def _fetch_frame(self) -> pd.DataFrame:
        ohlcv = await self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=self.max_candles)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        return df

    async def start_stream(self, on_candle_close_callback):
        logger.info("Starting data feed for %s (%s)", self.symbol, self.timeframe)
        try:
            self.df = await self._fetch_frame()
            if len(self.df) > 1:
                self.last_closed_candle_time = self.df.index[-2]
        except Exception as exc:
            logger.error("Initial OHLCV fetch failed: %s", exc)

        while True:
            try:
                new_df = await self._fetch_frame()
                combined = pd.concat([self.df, new_df])
                combined = combined[~combined.index.duplicated(keep="last")]
                combined.sort_index(inplace=True)
                self.df = combined.tail(self.max_candles)

                if len(self.df) < 2:
                    await asyncio.sleep(self.poll_seconds)
                    continue

                latest_timestamp = self.df.index[-1]
                closed_timestamp = self.df.index[-2]

                if self.last_closed_candle_time is None:
                    self.last_closed_candle_time = closed_timestamp
                    await asyncio.sleep(self.poll_seconds)
                    continue

                if closed_timestamp > self.last_closed_candle_time:
                    locked_df = self.df[self.df.index <= closed_timestamp].copy()
                    logger.info("Closed candle %s detected. Triggering pipeline.", closed_timestamp)
                    asyncio.create_task(on_candle_close_callback(locked_df))
                    self.last_closed_candle_time = closed_timestamp
                elif latest_timestamp > self.last_closed_candle_time:
                    # Handles first iteration where last lock points older than last complete candle.
                    self.last_closed_candle_time = closed_timestamp
            except Exception as exc:
                logger.error("Data feed loop interrupted: %s", exc)
            finally:
                await asyncio.sleep(self.poll_seconds)

    async def close(self):
        await self.exchange.close()
