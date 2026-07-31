"""
AI Reviewer
===========
Simulates a quantitative portfolio manager reviewing alpha candidates.

Provides quality assessment, constructive feedback, and submission recommendations.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

from backtest.engine import BacktestResult
from backtest.metrics import AlphaScore, AlphaGrade

logger = logging.getLogger(__name__)


class ReviewDecision(str, Enum):
    APPROVED = "APPROVED"
    REVISE = "REVISE"
    REJECT = "REJECT"


@dataclass
class ReviewResult:
    """Result of alpha review."""

    decision: ReviewDecision
    score: float
    grade: AlphaGrade
    feedback: str
    suggestions: List[str] = field(default_factory=list)
    key_strengths: List[str] = field(default_factory=list)
    key_weaknesses: List[str] = field(default_factory=list)


class AIReviewer:
    """
    AI reviewer that evaluates alpha quality like a quant PM.

    Provides:
    - Overall decision (APPROVED / REVISE / REJECT)
    - Specific feedback for improvement
    - Comparison against existing alpha library

    Usage:
        reviewer = AIReviewer()
        review = reviewer.review(backtest_result, alpha_score)
    """

    def __init__(
        self,
        min_sharpe: float = 0.5,
        min_ic_ir: float = 0.3,
        max_turnover: float = 0.5,
        max_drawdown: float = 0.35,
    ):
        self.min_sharpe = min_sharpe
        self.min_ic_ir = min_ic_ir
        self.max_turnover = max_turnover
        self.max_drawdown = max_drawdown

    def review(
        self,
        result: BacktestResult,
        score: AlphaScore,
        existing_alphas: Optional[List[Dict]] = None,
    ) -> ReviewResult:
        """
        Review an alpha candidate and make a decision.

        Args:
            result: Backtest result
            score: Computed alpha score
            existing_alphas: List of existing alpha records for comparison

        Returns:
            ReviewResult with decision and feedback
        """
        strengths = []
        weaknesses = []
        suggestions = []

        # Evaluate Sharpe
        if result.sharpe >= 1.5:
            strengths.append(f"Strong Sharpe ratio: {result.sharpe:.2f}")
        elif result.sharpe >= self.min_sharpe:
            strengths.append(f"Adequate Sharpe ratio: {result.sharpe:.2f}")
        else:
            weaknesses.append(f"Low Sharpe ratio: {result.sharpe:.2f}")
            suggestions.append(
                "Consider adding risk management constraints or "
                "reducing factor turnover"
            )

        # Evaluate IC
        if result.ic_ir >= 0.5:
            strengths.append(f"Strong IC IR: {result.ic_ir:.2f}")
        elif result.ic_ir >= self.min_ic_ir:
            strengths.append(f"Adequate IC IR: {result.ic_ir:.2f}")
        else:
            weaknesses.append(f"Low IC IR: {result.ic_ir:.2f}")
            suggestions.append("Review factor construction for predictive power")

        # Evaluate turnover
        if result.turnover <= 0.2:
            strengths.append(f"Low turnover: {result.turnover:.1%}")
        elif result.turnover <= self.max_turnover:
            pass  # Acceptable
        else:
            weaknesses.append(f"High turnover: {result.turnover:.1%}")
            suggestions.append(
                "Increase lookback period or apply decay weighting "
                "to reduce turnover"
            )

        # Evaluate drawdown
        if abs(result.max_drawdown) <= 0.15:
            strengths.append(f"Well-controlled drawdown: {result.max_drawdown:.1%}")
        elif abs(result.max_drawdown) <= self.max_drawdown:
            pass  # Acceptable
        else:
            weaknesses.append(f"Large drawdown: {result.max_drawdown:.1%}")
            suggestions.append("Add stop-loss or position sizing rules")

        # Evaluate stability
        if result.ic_positive_ratio > 0.55:
            strengths.append(
                f"Consistent IC: positive {result.ic_positive_ratio:.0%} of time"
            )
        elif result.ic_positive_ratio < 0.50:
            weaknesses.append(
                f"Unreliable signal: IC positive only "
                f"{result.ic_positive_ratio:.0%} of time"
            )

        # Check against existing alphas
        if existing_alphas:
            uniqueness_feedback = self._check_uniqueness(result, existing_alphas)
            if uniqueness_feedback:
                strengths.append(uniqueness_feedback)

        # Make decision
        decision = self._make_decision(result, score, strengths, weaknesses)

        # Build feedback
        feedback = self._build_feedback(decision, strengths, weaknesses)

        return ReviewResult(
            decision=decision,
            score=score.total,
            grade=score.grade,
            feedback=feedback,
            suggestions=suggestions,
            key_strengths=strengths,
            key_weaknesses=weaknesses,
        )

    def _make_decision(
        self,
        result: BacktestResult,
        score: AlphaScore,
        strengths: List[str],
        weaknesses: List[str],
    ) -> ReviewDecision:
        """Decide whether to approve, request revision, or reject."""
        # Hard reject conditions (only apply to low-score alphas)
        if score.grade == AlphaGrade.FAILURE:
            return ReviewDecision.REJECT
        if result.sharpe < 0.2 and score.total < 1.0:
            return ReviewDecision.REJECT
        if result.annual_return < 0 and result.sharpe < 0.5:
            return ReviewDecision.REJECT

        # Approve conditions
        if score.grade == AlphaGrade.RECOMMEND_SUBMIT and len(weaknesses) <= 2:
            return ReviewDecision.APPROVED

        # If score is marginal but has clear strengths
        if score.grade in (AlphaGrade.NEEDS_OPTIMIZATION, AlphaGrade.RECOMMEND_SUBMIT):
            if len(strengths) >= 3 and len(weaknesses) <= 2:
                return ReviewDecision.APPROVED
            return ReviewDecision.REVISE

        return ReviewDecision.REVISE

    def _build_feedback(
        self,
        decision: ReviewDecision,
        strengths: List[str],
        weaknesses: List[str],
    ) -> str:
        """Build natural language feedback."""
        parts = []

        if decision == ReviewDecision.APPROVED:
            parts.append("RECOMMENDATION: APPROVED for submission.")
        elif decision == ReviewDecision.REVISE:
            parts.append("RECOMMENDATION: REVISE - needs improvement before submission.")
        else:
            parts.append("RECOMMENDATION: REJECTED - does not meet quality thresholds.")

        if strengths:
            parts.append("\nSTRENGTHS:")
            for s in strengths:
                parts.append(f"  + {s}")

        if weaknesses:
            parts.append("\nWEAKNESSES:")
            for w in weaknesses:
                parts.append(f"  - {w}")

        return "\n".join(parts)

    def _check_uniqueness(
        self, result: BacktestResult, existing_alphas: List[Dict]
    ) -> Optional[str]:
        """
        Check if this alpha is too similar to existing ones.
        Returns a strength string if unique, None if not notably unique.
        """
        # This would ideally use factor correlation
        # For now, check name/expression similarity
        existing_names = {a.get("name", "").lower() for a in existing_alphas}
        existing_exprs = {a.get("expression", "") for a in existing_alphas}

        if result.alpha_name.lower() not in existing_names:
            if result.expression not in existing_exprs:
                return "Novel alpha: not redundant with existing library"

        return None

    def batch_review(
        self,
        results: Dict[str, BacktestResult],
        scores: Dict[str, AlphaScore],
    ) -> List[ReviewResult]:
        """Review multiple alphas and return sorted by quality."""
        reviews = []
        for name, result in results.items():
            score = scores.get(name)
            if score:
                review = self.review(result, score)
                reviews.append(review)

        reviews.sort(key=lambda r: r.score, reverse=True)
        return reviews
