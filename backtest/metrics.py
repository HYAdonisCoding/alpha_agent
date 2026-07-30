"""
Alpha Metrics & Scoring
========================
Performance metrics calculation and alpha quality scoring.

The scoring system evaluates each alpha and classifies it into:
- RECOMMEND_SUBMIT (>= 1.5): Ready for BRAIN submission
- NEEDS_OPTIMIZATION (1.0 - 1.5): Good idea, needs tuning
- ARCHIVE (0.5 - 1.0): Marginal, keep as reference
- FAILURE (< 0.5): Discard
"""

from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass

import pandas as pd
import numpy as np

from .engine import BacktestResult


class AlphaGrade(str, Enum):
    """Alpha quality grade based on composite score."""

    RECOMMEND_SUBMIT = "RECOMMEND_SUBMIT"    # >= 1.5
    NEEDS_OPTIMIZATION = "NEEDS_OPTIMIZATION"  # 1.0 - 1.5
    ARCHIVE = "ARCHIVE"                        # 0.5 - 1.0
    FAILURE = "FAILURE"                        # < 0.5


@dataclass
class AlphaScore:
    """Composite alpha score with breakdown."""

    total: float
    grade: AlphaGrade
    breakdown: Dict[str, float]


class AlphaMetrics:
    """
    Compute performance metrics and score alphas.

    Usage:
        metrics = AlphaMetrics()
        score = metrics.score(result)
        print(f"Alpha Grade: {score.grade}")
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Args:
            weights: Dict of metric -> weight for scoring
            thresholds: Dict of grade -> minimum score
        """
        self.weights = weights or {
            "sharpe": 0.35,
            "fitness": 0.25,
            "turnover_penalty": 0.15,
            "drawdown_penalty": 0.10,
            "ic_factor": 0.15,
        }

        self.thresholds = thresholds or {
            "RECOMMEND_SUBMIT": 1.5,
            "NEEDS_OPTIMIZATION": 1.0,
            "ARCHIVE": 0.5,
        }

    def score(self, result: BacktestResult) -> AlphaScore:
        """
        Compute composite alpha score from backtest result.

        Higher is better. Score = weighted sum of normalized metrics.
        """
        breakdown = {}

        # 1. Sharpe component (normalized: 0 = bad, 2 = great)
        sharpe = max(0, min(result.sharpe, 3.0))
        breakdown["sharpe"] = sharpe / 1.5  # 0 to 2

        # 2. Fitness component
        fitness = max(0, min(result.fitness, 3.0))
        breakdown["fitness"] = fitness / 1.5

        # 3. Turnover penalty (lower is better)
        turnover = result.turnover
        turnover_penalty = max(0, 1.0 - turnover / 0.5)  # 0% -> 1, 50%+ -> 0
        breakdown["turnover_penalty"] = turnover_penalty

        # 4. Drawdown penalty (lower is better)
        dd = abs(result.max_drawdown)
        dd_penalty = max(0, 1.0 - dd / 0.3)  # 0% -> 1, 30%+ -> 0
        breakdown["drawdown_penalty"] = dd_penalty

        # 5. IC factor
        ic_ir = max(0, min(result.ic_ir, 2.0))
        breakdown["ic_factor"] = ic_ir / 1.0  # 0 to 2

        # Composite score
        total = sum(
            self.weights.get(k, 0) * v for k, v in breakdown.items()
        )

        # Normalize to 0-2 scale
        max_possible = sum(self.weights.values())
        total = total / max_possible * 2.0

        # Grade
        if total >= self.thresholds["RECOMMEND_SUBMIT"]:
            grade = AlphaGrade.RECOMMEND_SUBMIT
        elif total >= self.thresholds["NEEDS_OPTIMIZATION"]:
            grade = AlphaGrade.NEEDS_OPTIMIZATION
        elif total >= self.thresholds["ARCHIVE"]:
            grade = AlphaGrade.ARCHIVE
        else:
            grade = AlphaGrade.FAILURE

        return AlphaScore(
            total=round(total, 4),
            grade=grade,
            breakdown={k: round(v, 4) for k, v in breakdown.items()},
        )

    @staticmethod
    def compute_rolling_metrics(
        daily_returns: pd.Series,
        window: int = 60,
    ) -> pd.DataFrame:
        """
        Compute rolling performance metrics.

        Returns DataFrame with columns:
        - rolling_sharpe
        - rolling_volatility
        - rolling_return
        - rolling_max_drawdown
        """
        if len(daily_returns) < window:
            return pd.DataFrame()

        annual_factor = np.sqrt(252)

        roll_mean = daily_returns.rolling(window).mean() * 252
        roll_std = daily_returns.rolling(window).std() * annual_factor
        roll_sharpe = roll_mean / roll_std

        cum = (1 + daily_returns).cumprod()
        roll_max = cum.rolling(window).max()
        roll_dd = (cum - roll_max) / roll_max
        roll_max_dd = roll_dd.rolling(window).min()

        return pd.DataFrame({
            "rolling_sharpe": roll_sharpe,
            "rolling_volatility": roll_std,
            "rolling_return": roll_mean,
            "rolling_max_drawdown": roll_max_dd,
        })

    @staticmethod
    def compute_ic_decay(
        ic_series: pd.Series, lookback: int = 20
    ) -> Dict[int, float]:
        """
        Compute IC decay over multiple forward horizons.

        Returns dict of horizon -> mean IC.
        Useful for understanding signal decay over time.
        """
        # This is approximate — full implementation would
        # recompute IC for each horizon
        decay = {}
        for horizon in [1, 5, 10, 20]:
            if len(ic_series) > horizon:
                decay[horizon] = ic_series.iloc[:-horizon].mean()
        return decay

    def compare_alphas(
        self, results: Dict[str, BacktestResult]
    ) -> pd.DataFrame:
        """
        Compare multiple alphas side by side.

        Args:
            results: Dict of alpha_name -> BacktestResult

        Returns:
            DataFrame with comparison metrics
        """
        rows = []
        for name, result in results.items():
            score = self.score(result)
            rows.append({
                "name": name,
                "score": score.total,
                "grade": score.grade.value,
                "sharpe": round(result.sharpe, 3),
                "fitness": round(result.fitness, 3),
                "turnover": f"{result.turnover:.1%}",
                "max_dd": f"{result.max_drawdown:.1%}",
                "ic_ir": round(result.ic_ir, 3),
                "ann_return": f"{result.annual_return:.1%}",
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("score", ascending=False)
        return df
