"""
Backtest Engine
===============
Simulates alpha factor performance using historical data.

Computes:
- Factor returns (long-short or long-only)
- Cumulative PnL
- Turnover
- Drawdown
"""

import logging
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from alpha.operators import FactorOperators

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Complete backtest result for an alpha factor."""

    # Summary metrics
    sharpe: float = 0.0
    fitness: float = 0.0
    turnover: float = 0.0
    max_drawdown: float = 0.0
    annual_return: float = 0.0
    annual_volatility: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0

    # IC metrics
    ic_mean: float = 0.0
    ic_ir: float = 0.0
    ic_std: float = 0.0
    ic_positive_ratio: float = 0.0

    # Detailed series (optional, for plotting)
    cumulative_returns: Optional[pd.Series] = None
    daily_returns: Optional[pd.Series] = None
    ic_series: Optional[pd.Series] = None
    drawdown_series: Optional[pd.Series] = None

    # Metadata
    alpha_name: str = ""
    expression: str = ""
    n_days: int = 0
    n_assets: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "sharpe": round(self.sharpe, 4),
            "fitness": round(self.fitness, 4),
            "turnover": round(self.turnover, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "annual_return": round(self.annual_return, 4),
            "annual_volatility": round(self.annual_volatility, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "win_rate": round(self.win_rate, 4),
            "ic_mean": round(self.ic_mean, 4),
            "ic_ir": round(self.ic_ir, 4),
            "ic_std": round(self.ic_std, 4),
            "ic_positive_ratio": round(self.ic_positive_ratio, 4),
            "alpha_name": self.alpha_name,
            "expression": self.expression,
            "n_days": self.n_days,
            "n_assets": self.n_assets,
        }


class BacktestEngine:
    """
    Simulate alpha factor performance.

    Supports:
    - Long-short portfolio (top/bottom quantile)
    - Long-only portfolio
    - Sector-neutral construction

    Usage:
        engine = BacktestEngine()
        result = engine.run(expression="rank(ts_delta(close,20))", data=data)
    """

    def __init__(
        self,
        lookback_days: int = 252,
        forward_days: int = 20,
        top_quantile: float = 0.2,
        bottom_quantile: float = 0.2,
        transaction_cost: float = 0.001,
        decay_weight: float = 0.5,
        warmup_days: int = 60,
    ):
        """
        Args:
            lookback_days: Days of historical data to use
            forward_days: Forward return period for IC calculation
            top_quantile: Fraction of assets in long leg
            bottom_quantile: Fraction of assets in short leg
            transaction_cost: Per-trade cost as fraction
            decay_weight: Weight for exponential decay (0=equal, 1=fully recent)
        """
        self.lookback_days = lookback_days
        self.forward_days = forward_days
        self.top_quantile = top_quantile
        self.bottom_quantile = bottom_quantile
        self.transaction_cost = transaction_cost
        self.decay_weight = decay_weight
        self.warmup_days = warmup_days
        self.operators = FactorOperators()

    def run(
        self,
        expression: str,
        data: Dict[str, pd.DataFrame],
        alpha_name: str = "",
        neutralization: str = "none",  # "none", "market", "industry"
        industry_data: Optional[pd.Series] = None,
    ) -> BacktestResult:
        """
        Run a complete backtest for an alpha expression.

        Args:
            expression: Alpha factor expression (e.g., "rank(ts_delta(close,20))")
            data: Dict of DataFrames keyed by field name
            alpha_name: Name for the alpha
            neutralization: Type of neutralization to apply
            industry_data: Industry classification for industry neutralization

        Returns:
            BacktestResult with all metrics
        """
        # 1. Compute factor values
        factor = self.operators.evaluate_expression(expression, data)
        if factor.empty:
            logger.warning(f"Empty factor for expression: {expression}")
            return BacktestResult(alpha_name=alpha_name, expression=expression)

        # 2. Apply neutralization
        if neutralization == "market":
            factor = self.operators.market_neutralize(factor)
        elif neutralization == "industry" and industry_data is not None:
            factor = self.operators.ind_neutralize(factor, industry_data)

        # 3. Compute forward returns
        if "close" in data:
            forward_returns = data["close"].pct_change(self.forward_days).shift(
                -self.forward_days
            )
        else:
            # Use first available data as proxy
            first_key = list(data.keys())[0]
            forward_returns = data[first_key].pct_change(self.forward_days).shift(
                -self.forward_days
            )

        # Align indices
        common_dates = factor.index.intersection(forward_returns.index)
        common_symbols = factor.columns.intersection(forward_returns.columns)

        factor = factor.loc[common_dates, common_symbols]
        forward_returns = forward_returns.loc[common_dates, common_symbols]

        n_days = len(common_dates)
        n_assets = len(common_symbols)

        if n_days < 63 or n_assets < 3:
            logger.warning(f"Insufficient data: {n_days} days, {n_assets} assets")
            return BacktestResult(
                alpha_name=alpha_name, expression=expression,
                n_days=n_days, n_assets=n_assets,
            )

        # 4. Compute daily returns (long-short portfolio)
        daily_returns, turnovers = self._compute_long_short_returns(
            factor, forward_returns, warmup_days=self.warmup_days
        )

        # 5. Compute IC
        ic_series = self._compute_ic_series(factor, forward_returns, warmup_days=self.warmup_days)

        # 6. Compute metrics
        result = self._compute_metrics(
            daily_returns=daily_returns,
            ic_series=ic_series,
            turnovers=turnovers,
            alpha_name=alpha_name,
            expression=expression,
            n_days=n_days,
            n_assets=n_assets,
        )

        return result

    def _compute_long_short_returns(
        self, factor: pd.DataFrame, forward_returns: pd.DataFrame, warmup_days: int = 0
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Simulate long-short portfolio returns.

        Long top quantile, short bottom quantile.
        """
        daily_rets = []
        turnovers = []

        top_n = max(1, int(len(factor.columns) * self.top_quantile))
        bottom_n = max(1, int(len(factor.columns) * self.bottom_quantile))

        prev_long = set()
        prev_short = set()

        start_idx = max(warmup_days, 0)
        for i in range(start_idx, len(factor) - self.forward_days):
            date = factor.index[i]
            scores = factor.iloc[i].dropna()

            if len(scores) < top_n + bottom_n:
                daily_rets.append(0)
                turnovers.append(0)
                continue

            # Select long and short legs
            sorted_scores = scores.sort_values(ascending=False)
            long_assets = set(sorted_scores.head(top_n).index)
            short_assets = set(sorted_scores.tail(bottom_n).index)

            # Forward returns for these assets
            fwd = forward_returns.iloc[i]

            long_ret = fwd[list(long_assets)].mean()
            short_ret = fwd[list(short_assets)].mean()

            # Long-short return
            ls_ret = long_ret - short_ret

            # Turnover
            turnover = len(long_assets - prev_long) + len(short_assets - prev_short)
            turnover = turnover / (top_n + bottom_n)

            # Transaction cost
            ls_ret -= turnover * self.transaction_cost * 2

            daily_rets.append(ls_ret if not np.isnan(ls_ret) else 0)
            turnovers.append(turnover)

            prev_long = long_assets
            prev_short = short_assets

        return pd.Series(daily_rets), pd.Series(turnovers)

    def _compute_ic_series(
        self, factor: pd.DataFrame, forward_returns: pd.DataFrame, warmup_days: int = 0
    ) -> pd.Series:
        """Compute Information Coefficient (rank correlation) series."""
        ic_values = []

        start_idx = max(warmup_days, 0)
        for i in range(start_idx, len(factor) - self.forward_days):
            f = factor.iloc[i].dropna()
            r = forward_returns.iloc[i].dropna()

            common = f.index.intersection(r.index)
            if len(common) < 5:
                continue

            f_rank = f[common].rank(pct=True)
            r_rank = r[common].rank(pct=True)

            ic = f_rank.corr(r_rank, method="spearman")
            if not np.isnan(ic):
                ic_values.append(ic)

        return pd.Series(ic_values)

    def _compute_metrics(
        self,
        daily_returns: pd.Series,
        ic_series: pd.Series,
        turnovers: pd.Series,
        alpha_name: str,
        expression: str,
        n_days: int,
        n_assets: int,
    ) -> BacktestResult:
        """Compute all performance metrics from return series."""
        if len(daily_returns) < 20:
            return BacktestResult(
                alpha_name=alpha_name, expression=expression,
                n_days=n_days, n_assets=n_assets,
            )

        # Returns
        mean_ret = daily_returns.mean()
        std_ret = daily_returns.std()
        annual_factor = np.sqrt(252)

        sharpe = (mean_ret / std_ret * annual_factor) if std_ret > 0 else 0
        annual_return = mean_ret * 252
        annual_volatility = std_ret * annual_factor

        # Cumulative returns
        cum_returns = (1 + daily_returns).cumprod()

        # Drawdown
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        max_dd = drawdown.min()

        # Calmar
        calmar = annual_return / abs(max_dd) if abs(max_dd) > 0 else 0

        # Win rate
        win_rate = (daily_returns > 0).mean()

        # Turnover
        avg_turnover = turnovers.mean() if len(turnovers) > 0 else 0

        # Fitness (WorldQuant-style)
        fitness = self._compute_fitness(daily_returns, ic_series)

        # IC metrics
        ic_mean = ic_series.mean() if len(ic_series) > 0 else 0
        ic_std = ic_series.std() if len(ic_series) > 0 else 0
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0
        ic_pos_ratio = (ic_series > 0).mean() if len(ic_series) > 0 else 0

        return BacktestResult(
            sharpe=sharpe,
            fitness=fitness,
            turnover=avg_turnover,
            max_drawdown=max_dd,
            annual_return=annual_return,
            annual_volatility=annual_volatility,
            calmar_ratio=calmar,
            win_rate=win_rate,
            ic_mean=ic_mean,
            ic_ir=ic_ir,
            ic_std=ic_std,
            ic_positive_ratio=ic_pos_ratio,
            cumulative_returns=cum_returns,
            daily_returns=daily_returns,
            ic_series=ic_series,
            drawdown_series=drawdown,
            alpha_name=alpha_name,
            expression=expression,
            n_days=n_days,
            n_assets=n_assets,
        )

    def _compute_fitness(
        self,
        daily_returns: pd.Series,
        ic_series: pd.Series,
    ) -> float:
        """
        Compute WorldQuant-style fitness score.

        Combines returns, stability, and IC into a single metric.
        Higher is better.
        """
        if len(daily_returns) < 20:
            return 0.0

        # Split into sub-periods for consistency check
        n = len(daily_returns)
        n_half = n // 2

        ret_1h = daily_returns.iloc[:n_half].mean()
        ret_2h = daily_returns.iloc[n_half:].mean()

        # Stability: ratio of worse half to better half
        if ret_1h > 0 and ret_2h > 0:
            stability = min(ret_1h, ret_2h) / max(ret_1h, ret_2h)
        elif ret_1h < 0 and ret_2h < 0:
            stability = max(ret_1h, ret_2h) / min(ret_1h, ret_2h)
        else:
            stability = -abs(ret_1h - ret_2h) / max(abs(ret_1h), abs(ret_2h), 1e-8)

        # Sharpe
        sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0

        # IC component
        ic = ic_series.mean() if len(ic_series) > 0 else 0

        # Combine
        fitness = 0.4 * sharpe + 0.3 * stability + 0.3 * ic * 10
        return fitness
