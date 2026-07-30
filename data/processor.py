"""
Data Processor
==============
Data cleaning, transformation, and factor computation utilities.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Union


class DataProcessor:
    """
    Data cleaning and preprocessing utilities for market data.

    Handles:
    - Missing value imputation
    - Outlier detection and capping
    - Normalization / standardization
    - Rolling window computations
    """

    @staticmethod
    def clean_prices(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean price data:
        - Forward-fill missing values (max 5 days)
        - Drop symbols with >20% missing data
        """
        if df.empty:
            return df

        # Forward fill limited gaps
        df = df.ffill(limit=5)

        # Drop symbols with excessive missing data
        threshold = len(df) * 0.2
        valid_cols = df.columns[df.isna().sum() <= threshold]
        dropped = set(df.columns) - set(valid_cols)
        if dropped:
            import logging
            logging.getLogger(__name__).info(
                f"Dropped symbols with >20% missing data: {dropped}"
            )

        return df[valid_cols.tolist()]

    @staticmethod
    def winsorize(
        series: pd.Series, limits: tuple = (0.01, 0.99)
    ) -> pd.Series:
        """Winsorize (clip) outliers at given percentiles."""
        lower = series.quantile(limits[0])
        upper = series.quantile(limits[1])
        return series.clip(lower=lower, upper=upper)

    @staticmethod
    def zscore_normalize(df: pd.DataFrame, window: int = 252) -> pd.DataFrame:
        """Rolling z-score normalization."""
        rolling_mean = df.rolling(window, min_periods=min(window // 4, 63)).mean()
        rolling_std = df.rolling(window, min_periods=min(window // 4, 63)).std()
        rolling_std = rolling_std.replace(0, np.nan)
        return (df - rolling_mean) / rolling_std

    @staticmethod
    def cross_sectional_rank(df: pd.DataFrame) -> pd.DataFrame:
        """Cross-sectional rank normalization (0 to 1)."""
        return df.rank(axis=1, pct=True)

    @staticmethod
    def compute_rolling_stats(
        df: pd.DataFrame, window: int = 20
    ) -> dict:
        """
        Compute rolling statistics for each column.

        Returns dict with keys: mean, std, skew, kurt, min, max
        """
        return {
            "mean": df.rolling(window, min_periods=window // 2).mean(),
            "std": df.rolling(window, min_periods=window // 2).std(),
            "skew": df.rolling(window, min_periods=window).skew(),
            "min": df.rolling(window, min_periods=window // 2).min(),
            "max": df.rolling(window, min_periods=window // 2).max(),
        }

    @staticmethod
    def fill_forward_prices(df: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
        """
        Fill non-trading days by forward-filling with a gap limit.
        Also fills initial NaN values with 0 (treat as no data rather than 0 return).
        """
        return df.ffill(limit=limit)

    @staticmethod
    def detect_regime(
        returns: pd.DataFrame, method: str = "volatility"
    ) -> pd.Series:
        """
        Detect market regime based on returns.

        Methods:
        - volatility: classify based on 20-day rolling vol vs 252-day
        - trend: classify based on SMA crossover
        """
        if method == "volatility":
            vol_short = returns.rolling(20).std().mean(axis=1)
            vol_long = returns.rolling(252).std().mean(axis=1)

            regime = pd.Series("normal", index=returns.index)
            regime[vol_short > vol_long * 1.5] = "high_volatility"
            regime[vol_short < vol_long * 0.5] = "low_volatility"
            return regime

        elif method == "trend":
            ma_short = returns.mean(axis=1).rolling(20).mean()
            ma_long = returns.mean(axis=1).rolling(60).mean()

            regime = pd.Series("neutral", index=returns.index)
            regime[ma_short > ma_long] = "bullish"
            regime[ma_short < ma_long] = "bearish"
            return regime

        return pd.Series("unknown", index=returns.index)
