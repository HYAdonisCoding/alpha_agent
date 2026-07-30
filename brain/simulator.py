"""
BRAIN Simulator
===============
Local simulation of WorldQuant BRAIN alpha evaluation.

Simulates BRAIN's generation + simulation pipeline locally
so you can test alphas before submitting to the live platform.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from backtest.engine import BacktestEngine, BacktestResult
from backtest.metrics import AlphaMetrics, AlphaScore

logger = logging.getLogger(__name__)


class BrainSimulator:
    """
    Local BRAIN-like simulation environment.

    Simulates the alpha evaluation pipeline:
    1. Data preprocessing
    2. Factor computation
    3. Universe selection
    4. Performance simulation
    5. Scoring

    Usage:
        sim = BrainSimulator()
        result = sim.evaluate(expression="rank(ts_delta(close,20))", data=data)
    """

    def __init__(
        self,
        universe: str = "TOP3000",  # BRAIN universe names
        delay: int = 1,               # Data delay in days
        neutralization: str = "market",
        decay: float = 0.0,           # Alpha decay
        pasteurization: str = "ON",
        nan_handling: str = "OFF",
    ):
        self.universe = universe
        self.delay = delay
        self.neutralization = neutralization
        self.decay = decay
        self.pasteurization = pasteurization
        self.nan_handling = nan_handling

        self.engine = BacktestEngine()
        self.metrics = AlphaMetrics()

    def evaluate(
        self,
        expression: str,
        data: Dict[str, Any],
        alpha_name: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate an alpha expression in simulation.

        Returns dict matching BRAIN simulation response format.
        """
        # Run local backtest
        result = self.engine.run(
            expression=expression,
            data=data,
            alpha_name=alpha_name,
            neutralization=self.neutralization,
        )

        # Score the alpha
        score = self.metrics.score(result)

        # Build BRAIN-like response
        return {
            "alpha": alpha_name or "unnamed",
            "expression": expression,
            "status": self._sim_status(result),
            "grade": score.grade.value,
            "is": {
                "sharpe": round(result.sharpe, 4),
                "fitness": round(result.fitness, 4),
                "turnover": round(result.turnover, 4),
                "returns": round(result.annual_return, 4),
                "drawdown": round(result.max_drawdown, 4),
            },
            "pnl": {
                "sharpe": round(result.sharpe, 4),
                "fitness": round(result.fitness, 4),
                "returns": round(result.annual_return, 4),
            },
            "checks": self._sim_checks(result),
            "evaluated_at": datetime.now().isoformat(),
            "universe": self.universe,
            "delay": self.delay,
            "neutralization": self.neutralization,
            "decay": self.decay,
        }

    def _sim_status(self, result: BacktestResult) -> str:
        """Determine simulation status."""
        if result.n_days < 63:
            return "INSUFFICIENT_DATA"
        if result.sharpe > 1.0 and result.fitness > 0.8:
            return "PASSED"
        if result.sharpe > 0.5:
            return "MARGINAL"
        return "FAILED"

    def _sim_checks(self, result: BacktestResult) -> Dict[str, bool]:
        """Run BRAIN-like checks."""
        return {
            "data_sufficient": result.n_days >= 252,
            "positive_sharpe": result.sharpe > 0,
            "positive_fitness": result.fitness > 0,
            "low_turnover": result.turnover < 0.5,
            "low_drawdown": abs(result.max_drawdown) < 0.4,
            "positive_ic": result.ic_mean > 0,
        }

    def evaluate_batch(
        self,
        expressions: List[Dict[str, str]],
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple alpha expressions.

        Args:
            expressions: List of {"name": "...", "expression": "..."}
            data: Market data

        Returns:
            List of evaluation results sorted by fitness
        """
        results = []
        for alpha in expressions:
            result = self.evaluate(
                expression=alpha["expression"],
                data=data,
                alpha_name=alpha.get("name", ""),
            )
            results.append(result)

        results.sort(
            key=lambda r: r.get("is", {}).get("fitness", 0), reverse=True
        )
        return results
