"""
Factor Operators Library
========================
Implements factor computation operators commonly used in WorldQuant BRAIN alpha expressions.

Operators follow WorldQuant's operator semantics where possible.
Each operator is implemented as a standalone function so it can be tested independently.
"""

import pandas as pd
import numpy as np
from typing import Optional, Union


class FactorOperators:
    """
    Collection of factor operators matching WorldQuant BRAIN semantics.

    All operators work on DataFrames (time x symbols) and return DataFrames.
    """

    @staticmethod
    def ts_delta(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Time-series delta: series[t] - series[t-n].
        Equivalent to BRAIN: ts_delta(x, n)
        """
        return series - series.shift(n)

    @staticmethod
    def ts_sum(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Time-series sum over n periods.
        BRAIN: ts_sum(x, n)
        """
        return series.rolling(n, min_periods=n // 2).sum()

    @staticmethod
    def ts_mean(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Time-series mean over n periods.
        BRAIN: ts_mean(x, n)
        """
        return series.rolling(n, min_periods=n // 2).mean()

    @staticmethod
    def ts_std(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Time-series standard deviation over n periods.
        BRAIN: ts_std(x, n)
        """
        return series.rolling(n, min_periods=n // 2).std()

    @staticmethod
    def ts_rank(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Time-series rank over n periods. Returns rank from 0 to 1.
        BRAIN: ts_rank(x, n) - ranking of current value within n-period window
        """
        def rolling_rank(col):
            return col.rolling(n, min_periods=n // 2).apply(
                lambda x: (x.rank().iloc[-1] - 1) / (len(x) - 1) if len(x) > 1 else 0.5,
                raw=False,
            )

        return series.apply(rolling_rank, raw=False)

    @staticmethod
    def ts_zscore(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Time-series z-score: (x - mean(x,n)) / std(x,n).
        BRAIN: ts_zscore(x, n)
        """
        mean = series.rolling(n, min_periods=n // 2).mean()
        std = series.rolling(n, min_periods=n // 2).std()
        std = std.replace(0, np.nan)
        return (series - mean) / std

    @staticmethod
    def ts_min(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """Time-series minimum over n periods. BRAIN: ts_min(x, n)"""
        return series.rolling(n, min_periods=n // 2).min()

    @staticmethod
    def ts_max(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """Time-series maximum over n periods. BRAIN: ts_max(x, n)"""
        return series.rolling(n, min_periods=n // 2).max()

    @staticmethod
    def ts_corr(x: pd.DataFrame, y: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Time-series correlation between x and y over n periods.
        BRAIN: ts_corr(x, y, n)
        """
        return x.rolling(n, min_periods=n // 2).corr(y)

    @staticmethod
    def rank(series: Union[pd.DataFrame, pd.Series]) -> pd.DataFrame:
        """
        Cross-sectional rank (0 to 1).
        BRAIN: rank(x)
        """
        if isinstance(series, pd.Series):
            series = series.to_frame()
        return series.rank(axis=1, pct=True)

    @staticmethod
    def scale(series: pd.DataFrame, a: float = 1.0) -> pd.DataFrame:
        """
        Scale values: scale = x / sum(abs(x)) * a
        BRAIN: scale(x, a)
        """
        abs_sum = series.abs().sum(axis=1)
        abs_sum = abs_sum.replace(0, np.nan)
        return series.div(abs_sum, axis=0) * a

    @staticmethod
    def signed_power(series: pd.DataFrame, a: float) -> pd.DataFrame:
        """
        Signed power: sign(x) * |x|^a
        BRAIN: signed_power(x, a)
        """
        return np.sign(series) * (series.abs() ** a)

    @staticmethod
    def decay_linear(series: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Weighted moving average with linearly decaying weights.
        BRAIN: decay_linear(x, n)
        """
        weights = np.arange(1, n + 1)
        weights = weights / weights.sum()

        def weighted_mean(col):
            return col.rolling(n, min_periods=n // 2).apply(
                lambda x: np.dot(x, weights[-len(x):] / weights[-len(x):].sum()),
                raw=True,
            )

        return series.apply(weighted_mean, raw=False)

    @staticmethod
    def ind_neutralize(
        factor: pd.DataFrame, industry: pd.Series
    ) -> pd.DataFrame:
        """
        Industry neutralize a factor: subtract industry mean from each symbol.
        """
        result = factor.copy()
        for dt in factor.index:
            if dt in industry.index:
                ind = industry.loc[dt] if isinstance(industry, pd.DataFrame) else industry
                for ind_val in ind.unique():
                    mask = ind == ind_val
                    symbols_in_ind = factor.columns.intersection(mask[mask].index)
                    if len(symbols_in_ind) > 1:
                        ind_mean = factor.loc[dt, symbols_in_ind].mean()
                        result.loc[dt, symbols_in_ind] -= ind_mean
                    elif len(symbols_in_ind) == 1:
                        result.loc[dt, symbols_in_ind] = 0
        return result

    @staticmethod
    def market_neutralize(factor: pd.DataFrame) -> pd.DataFrame:
        """Market neutralize: subtract cross-sectional mean."""
        return factor.sub(factor.mean(axis=1), axis=0)

    # ---- Utility ----

    @staticmethod
    def evaluate_expression(
        expression: str,
        data: dict,
    ) -> pd.DataFrame:
        """
        Evaluate a simple factor expression using provided data.

        This is a minimal evaluator. For full BRAIN expressions,
        a proper parser would be needed.

        Args:
            expression: Factor expression string
            data: dict mapping variable names to DataFrames
                e.g. {"close": prices_df, "volume": volume_df}

        Returns:
            Factor values DataFrame
        """
        # Very basic evaluation - for demo/prototype use
        # A production system would use a proper expression parser

        ops = FactorOperators()

        # Replace known operators with method calls
        # This is a simplified approach - full implementation needs proper parsing
        local_vars = {**data}
        local_vars.update({
            "ts_delta": ops.ts_delta,
            "ts_sum": ops.ts_sum,
            "ts_mean": ops.ts_mean,
            "ts_std": ops.ts_std,
            "ts_rank": ops.ts_rank,
            "ts_zscore": ops.ts_zscore,
            "ts_min": ops.ts_min,
            "ts_max": ops.ts_max,
            "ts_corr": ops.ts_corr,
            "rank": ops.rank,
            "scale": ops.scale,
            "signed_power": ops.signed_power,
            "decay_linear": ops.decay_linear,
            "np": np,
            "pd": pd,
        })

        try:
            result = eval(expression, {"__builtins__": {}}, local_vars)
            if isinstance(result, pd.Series):
                result = result.to_frame()
            return result
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression '{expression}': {e}")
