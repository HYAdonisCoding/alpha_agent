"""
Market Data Loader
==================
Unified interface for loading financial market data from multiple sources.

Supported sources:
- Yahoo Finance (global markets)
- AKShare (A-share markets)
- CSV cache (local processed data)

Data types:
- Price data (OHLCV)
- Fundamental data
- Volume data
- Market cap
- Industry classification
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union
from pathlib import Path

import pandas as pd
import numpy as np
import yaml

logger = logging.getLogger(__name__)


class MarketDataLoader:
    """
    Unified market data loader with local caching.

    Usage:
        loader = MarketDataLoader(config_path="config/settings.yaml")
        prices = loader.load_price(symbols=["AAPL", "MSFT"], start="2023-01-01")
        fundamentals = loader.load_fundamental(symbols=["AAPL"])
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.cache_dir = Path(self.config.get("data", {}).get("cache_dir", "data/processed"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.universe = self.config.get("data", {}).get("universe", {})
        self._price_cache: Dict[str, pd.DataFrame] = {}

    def _load_config(self, path: str) -> dict:
        with open(path, "r") as f:
            return yaml.safe_load(f)

    # ---- Price Data ----

    def load_price(
        self,
        symbols: Optional[List[str]] = None,
        market: str = "us",
        start: Optional[str] = None,
        end: Optional[str] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Load OHLCV price data for given symbols.

        Returns DataFrame with MultiIndex columns: (symbol, field)
        Fields: open, high, low, close, adj_close, volume
        """
        if symbols is None:
            symbols = self.universe.get(market, self.universe.get("us", []))

        if start is None:
            start = self.config.get("data", {}).get("date_range", {}).get("start", "2020-01-01")
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        cache_key = f"price_{market}_{start}_{end}"
        cache_file = self.cache_dir / f"{cache_key}.parquet"

        if use_cache and cache_file.exists():
            logger.info(f"Loading price data from cache: {cache_file}")
            df = pd.read_parquet(cache_file)
            # Filter to requested symbols
            available = [s for s in symbols if s in df.columns.get_level_values(0)]
            if available:
                return df[available]

        logger.info(f"Fetching price data for {len(symbols)} symbols from Yahoo Finance...")
        df = self._fetch_yahoo_prices(symbols, start, end)

        if not df.empty:
            df.to_parquet(cache_file)
            logger.info(f"Cached price data to {cache_file}")

        return df

    def _fetch_yahoo_prices(
        self, symbols: List[str], start: str, end: str
    ) -> pd.DataFrame:
        """Fetch price data from Yahoo Finance."""
        try:
            import yfinance as yf

            data = {}
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=start, end=end)
                    if not hist.empty:
                        # Standardize columns
                        hist = hist.rename(columns={
                            "Open": "open",
                            "High": "high",
                            "Low": "low",
                            "Close": "close",
                            "Volume": "volume",
                        })
                        if "Adj Close" in hist.columns:
                            hist = hist.rename(columns={"Adj Close": "adj_close"})
                        data[symbol] = hist[["open", "high", "low", "close", "volume"]]
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol}: {e}")

            if not data:
                return pd.DataFrame()

            df = pd.concat(data, axis=1)
            df.columns.names = ["symbol", "field"]
            return df

        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
            return pd.DataFrame()

    # ---- Volume Data ----

    def load_volume(self, symbols: Optional[List[str]] = None, **kwargs) -> pd.DataFrame:
        """Load volume data for given symbols."""
        prices = self.load_price(symbols=symbols, **kwargs)
        if prices.empty:
            return pd.DataFrame()

        try:
            return prices.xs("volume", level="field", axis=1)
        except KeyError:
            return pd.DataFrame()

    # ---- Returns Computation ----

    def compute_returns(
        self,
        prices: Optional[pd.DataFrame] = None,
        symbols: Optional[List[str]] = None,
        period: int = 1,
        **kwargs,
    ) -> pd.DataFrame:
        """Compute period returns from price data."""
        if prices is None:
            prices = self.load_price(symbols=symbols, **kwargs)

        if prices.empty:
            return pd.DataFrame()

        try:
            close = prices.xs("close", level="field", axis=1)
            return close.pct_change(period).dropna()
        except KeyError:
            return pd.DataFrame()

    # ---- Fundamental Data ----

    def load_fundamental(
        self, symbols: Optional[List[str]] = None, **kwargs
    ) -> pd.DataFrame:
        """
        Load fundamental data: market cap, P/E, P/B, sector, industry.
        """
        if symbols is None:
            symbols = self.universe.get("us", [])

        fundamentals = {}
        try:
            import yfinance as yf

            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    fundamentals[symbol] = {
                        "market_cap": info.get("marketCap"),
                        "pe_ratio": info.get("trailingPE"),
                        "pb_ratio": info.get("priceToBook"),
                        "sector": info.get("sector"),
                        "industry": info.get("industry"),
                        "country": info.get("country"),
                    }
                except Exception as e:
                    logger.warning(f"Failed to fetch fundamentals for {symbol}: {e}")

        except ImportError:
            logger.error("yfinance not installed")

        return pd.DataFrame(fundamentals).T

    # ---- Market Cap ----

    def load_market_cap(
        self, symbols: Optional[List[str]] = None, **kwargs
    ) -> pd.Series:
        """Load market capitalization data."""
        fund = self.load_fundamental(symbols=symbols, **kwargs)
        if "market_cap" in fund.columns:
            return fund["market_cap"]
        return pd.Series(dtype=float)

    # ---- Industry ----

    def load_industry(
        self, symbols: Optional[List[str]] = None, **kwargs
    ) -> pd.Series:
        """Load industry classification."""
        fund = self.load_fundamental(symbols=symbols, **kwargs)
        if "industry" in fund.columns:
            return fund["industry"]
        return pd.Series(dtype=str)

    # ---- A-Share Data via AKShare ----

    def load_a_share(
        self,
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load A-share market data via AKShare."""
        if symbols is None:
            symbols = self.universe.get("cn", [])

        if start is None:
            start = "2020-01-01"
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        try:
            import akshare as ak

            data = {}
            for symbol in symbols:
                try:
                    # AKShare stock daily data
                    df = ak.stock_zh_a_hist(
                        symbol=symbol,
                        period="daily",
                        start_date=start.replace("-", ""),
                        end_date=end.replace("-", ""),
                        adjust="qfq",  # forward-adjusted
                    )
                    if not df.empty:
                        df["日期"] = pd.to_datetime(df["日期"])
                        df = df.set_index("日期")
                        df = df.rename(columns={
                            "开盘": "open",
                            "最高": "high",
                            "最低": "low",
                            "收盘": "close",
                            "成交量": "volume",
                        })
                        data[symbol] = df[["open", "high", "low", "close", "volume"]]
                except Exception as e:
                    logger.warning(f"Failed to fetch A-share {symbol}: {e}")

            if not data:
                return pd.DataFrame()

            df = pd.concat(data, axis=1)
            df.columns.names = ["symbol", "field"]
            return df

        except ImportError:
            logger.error("akshare not installed. Run: pip install akshare")
            return pd.DataFrame()

    # ---- Utility ----

    def get_close_prices(
        self, prices: Optional[pd.DataFrame] = None, **kwargs
    ) -> pd.DataFrame:
        """Extract close prices from price DataFrame."""
        if prices is None:
            prices = self.load_price(**kwargs)
        if prices.empty:
            return pd.DataFrame()
        try:
            return prices.xs("close", level="field", axis=1)
        except KeyError:
            return pd.DataFrame()

    def get_volumes(
        self, prices: Optional[pd.DataFrame] = None, **kwargs
    ) -> pd.DataFrame:
        """Extract volumes from price DataFrame."""
        if prices is None:
            prices = self.load_price(**kwargs)
        if prices.empty:
            return pd.DataFrame()
        try:
            return prices.xs("volume", level="field", axis=1)
        except KeyError:
            return pd.DataFrame()

    def load_all(
        self,
        symbols: Optional[List[str]] = None,
        market: str = "us",
        **kwargs,
    ) -> Dict[str, pd.DataFrame]:
        """Load all available data for a market."""
        prices = self.load_price(symbols=symbols, market=market, **kwargs)
        fundamentals = self.load_fundamental(symbols=symbols, **kwargs)

        return {
            "prices": prices,
            "close": self.get_close_prices(prices),
            "volume": self.get_volumes(prices),
            "fundamentals": fundamentals,
        }
