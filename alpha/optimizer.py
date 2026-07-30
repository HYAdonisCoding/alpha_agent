"""
Alpha Optimizer
===============
Parameter optimization for alpha expressions.

Given a template and parameter ranges, systematically searches for
the best parameter combination via grid search or Bayesian optimization.
"""

import logging
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from itertools import product

import pandas as pd
import numpy as np

from .templates import AlphaTemplates, AlphaTemplate
from .operators import FactorOperators

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of an optimization run."""

    template_name: str
    expression: str
    parameters: Dict[str, Any]
    score: float
    metrics: Dict[str, float]
    rank: int = 0


class AlphaOptimizer:
    """
    Optimize alpha expression parameters.

    Supports:
    - Grid search over parameter space
    - (Future) Bayesian optimization via scikit-optimize
    - Walk-forward optimization for robustness

    Usage:
        opt = AlphaOptimizer(backtest_fn=my_backtest_func)
        results = opt.grid_search(template, data)
    """

    def __init__(
        self,
        backtest_fn: Optional[Callable] = None,
        score_fn: Optional[Callable] = None,
    ):
        """
        Args:
            backtest_fn: Function that takes (expression, data) and returns metrics dict
            score_fn: Function that takes metrics dict and returns a single score
        """
        self.backtest_fn = backtest_fn
        self.score_fn = score_fn or self._default_score
        self.templates = AlphaTemplates()
        self.operators = FactorOperators()

    @staticmethod
    def _default_score(metrics: Dict[str, float]) -> float:
        """Default scoring function using config weights."""
        weights = {
            "sharpe": 0.40,
            "fitness": 0.30,
            "turnover": -0.15,  # penalty
            "drawdown": -0.10,  # penalty
            "ic_mean": 0.05,
        }
        score = 0.0
        for metric, weight in weights.items():
            if metric in metrics:
                score += weight * metrics[metric]
        return score

    def grid_search(
        self,
        template: AlphaTemplate,
        data: Dict[str, pd.DataFrame],
        top_n: int = 10,
        verbose: bool = True,
    ) -> List[OptimizationResult]:
        """
        Grid search over all parameter combinations for a template.

        Args:
            template: AlphaTemplate to optimize
            data: Data dict with field names as keys (e.g., {"close": df, "volume": df})
            top_n: Number of top results to return
            verbose: Print progress

        Returns:
            Sorted list of OptimizationResult (best first)
        """
        param_combos = self.templates.get_parameter_combinations(template)

        if verbose:
            logger.info(
                f"Grid searching {template.name}: "
                f"{len(param_combos)} parameter combinations"
            )

        results = []
        for params in param_combos:
            expression = self.templates.instantiate(template, params)

            if self.backtest_fn:
                metrics = self.backtest_fn(expression, data)
                score = self.score_fn(metrics)
            else:
                # Without backtest function, compute basic factor stats
                metrics = self._compute_factor_stats(expression, data)
                score = metrics.get("ic_mean", 0)

            results.append(
                OptimizationResult(
                    template_name=template.name,
                    expression=expression,
                    parameters=params,
                    score=score,
                    metrics=metrics,
                )
            )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        # Assign ranks
        for i, r in enumerate(results):
            r.rank = i + 1

        return results[:top_n]

    def optimize_category(
        self,
        category: str,
        data: Dict[str, pd.DataFrame],
        top_n_per_template: int = 3,
        verbose: bool = True,
    ) -> List[OptimizationResult]:
        """
        Optimize all templates in a category and return top results across templates.

        Args:
            category: Template category name
            data: Data dict
            top_n_per_template: Top N results per template
            verbose: Print progress

        Returns:
            Sorted list of best OptimizationResult across category
        """
        templates = self.templates.get_by_category(category)
        all_results = []

        for template in templates:
            results = self.grid_search(
                template, data, top_n=top_n_per_template, verbose=verbose
            )
            all_results.extend(results)

        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results

    def optimize_all(
        self,
        data: Dict[str, pd.DataFrame],
        top_n: int = 50,
        verbose: bool = True,
    ) -> List[OptimizationResult]:
        """
        Grid search across ALL templates and return top results.

        Args:
            data: Data dict
            top_n: Number of top results to return
            verbose: Print progress

        Returns:
            Sorted list of best OptimizationResult
        """
        all_templates = self.templates.get_all_templates()
        all_results = []

        for template in all_templates:
            results = self.grid_search(
                template, data, top_n=3, verbose=verbose
            )
            all_results.extend(results)

        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:top_n]

    def walk_forward_optimize(
        self,
        template: AlphaTemplate,
        data: Dict[str, pd.DataFrame],
        train_window: int = 252,
        test_window: int = 63,
        step: int = 21,
        top_n: int = 5,
    ) -> List[OptimizationResult]:
        """
        Walk-forward optimization to avoid overfitting.

        Trains on rolling windows and averages scores across periods.

        Args:
            template: Template to optimize
            data: Data dict
            train_window: Training period length (trading days)
            test_window: Test period length
            step: Step size between windows
            top_n: Top results to return

        Returns:
            Best OptimizationResult by average walk-forward score
        """
        param_combos = self.templates.get_parameter_combinations(template)

        # Determine windows
        if "close" in data:
            n_dates = len(data["close"])
        else:
            first_key = list(data.keys())[0]
            n_dates = len(data[first_key])

        scores_by_param = {i: [] for i in range(len(param_combos))}

        window_start = 0
        while window_start + train_window + test_window <= n_dates:
            train_end = window_start + train_window
            test_end = train_end + test_window

            # Slice data for this window
            window_data = {}
            for key, df in data.items():
                window_data[key] = df.iloc[window_start:train_end]

            # Optimize on training window
            for i, params in enumerate(param_combos):
                expression = self.templates.instantiate(template, params)

                if self.backtest_fn:
                    metrics = self.backtest_fn(expression, window_data)
                    score = self.score_fn(metrics)
                else:
                    metrics = self._compute_factor_stats(expression, window_data)
                    score = metrics.get("ic_mean", 0)

                scores_by_param[i].append(score)

            window_start += step

        # Average scores across windows
        results = []
        for i, scores in scores_by_param.items():
            if scores:
                avg_score = np.mean(scores)
                std_score = np.std(scores) if len(scores) > 1 else 0
                # Penalize high variance (unstable performance)
                stability_penalty = 0.2 * std_score
                adjusted_score = avg_score - stability_penalty

                params = param_combos[i]
                expression = self.templates.instantiate(template, params)

                results.append(
                    OptimizationResult(
                        template_name=template.name,
                        expression=expression,
                        parameters=params,
                        score=adjusted_score,
                        metrics={
                            "avg_score": avg_score,
                            "std_score": std_score,
                            "n_windows": len(scores),
                        },
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    def _compute_factor_stats(
        self,
        expression: str,
        data: Dict[str, pd.DataFrame],
    ) -> Dict[str, float]:
        """
        Compute basic factor statistics without full backtest.

        Computes IC (Information Coefficient) with forward returns
        as a quick quality check.
        """
        try:
            factor = self.operators.evaluate_expression(expression, data)
            if factor.empty:
                return {"ic_mean": 0, "ic_ir": 0}

            # Forward returns
            if "close" in data:
                forward_returns = data["close"].pct_change(20).shift(-20)
                common_dates = factor.index.intersection(forward_returns.index)
                common_symbols = factor.columns.intersection(forward_returns.columns)

                if len(common_dates) > 10 and len(common_symbols) > 1:
                    f = factor.loc[common_dates, common_symbols]
                    r = forward_returns.loc[common_dates, common_symbols]

                    # Rank IC
                    f_rank = f.rank(axis=1, pct=True)
                    r_rank = r.rank(axis=1, pct=True)

                    ic = f_rank.corrwith(r_rank, axis=1)
                    ic_mean = ic.mean()
                    ic_ir = ic_mean / ic.std() if ic.std() > 0 else 0

                    return {
                        "ic_mean": round(ic_mean, 4),
                        "ic_ir": round(ic_ir, 4),
                        "ic_std": round(ic.std(), 4),
                    }

        except Exception as e:
            logger.warning(f"Failed to compute factor stats: {e}")

        return {"ic_mean": 0, "ic_ir": 0}
