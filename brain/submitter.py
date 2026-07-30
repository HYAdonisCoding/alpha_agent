"""
Alpha Submitter
===============
Manages the alpha submission workflow:

1. Local validation (backtest + risk check + review)
2. BRAIN simulation
3. Human review prompt
4. Submission to BRAIN
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from backtest.engine import BacktestResult
from backtest.metrics import AlphaMetrics, AlphaScore, AlphaGrade
from backtest.validator import RiskValidator, ValidationResult
from ai.reviewer import AIReviewer, ReviewResult, ReviewDecision
from brain.simulator import BrainSimulator

logger = logging.getLogger(__name__)


class SubmissionStage(str, Enum):
    """Stages of the alpha submission pipeline."""

    GENERATED = "generated"
    BACKTESTED = "backtested"
    VALIDATED = "validated"
    REVIEWED = "reviewed"
    SIMULATED = "simulated"       # BRAIN simulation
    PENDING_APPROVAL = "pending_approval"  # Waiting for human
    SUBMITTED = "submitted"
    REJECTED = "rejected"


@dataclass
class AlphaSubmission:
    """Tracks an alpha through the submission pipeline."""

    name: str
    expression: str
    category: str = ""
    description: str = ""
    parameters: Dict = field(default_factory=dict)
    stage: SubmissionStage = SubmissionStage.GENERATED

    # Results at each stage
    backtest_result: Optional[BacktestResult] = None
    alpha_score: Optional[AlphaScore] = None
    validation_result: Optional[ValidationResult] = None
    review_result: Optional[ReviewResult] = None
    simulation_result: Optional[Dict] = None

    # Timestamps
    created_at: str = ""
    submitted_at: Optional[str] = None


class AlphaSubmitter:
    """
    Manages the end-to-end alpha submission workflow.

    Usage:
        submitter = AlphaSubmitter()
        submission = submitter.process(alpha_candidate, data)
        if submission.review_result.decision == ReviewDecision.APPROVED:
            submitter.submit_to_brain(submission)
    """

    def __init__(
        self,
        auto_submit: bool = False,  # NEVER set to True without human oversight
        max_daily_submissions: int = 10,
    ):
        self.auto_submit = auto_submit
        self.max_daily_submissions = max_daily_submissions

        self.engine = None  # Set externally or use default
        self.metrics = AlphaMetrics()
        self.validator = RiskValidator()
        self.reviewer = AIReviewer()
        self.simulator = BrainSimulator()

        self._daily_count = 0
        self._pipeline: List[AlphaSubmission] = []

    def process(
        self,
        candidate,
        data: Dict[str, Any],
        existing_alphas: Optional[List[Dict]] = None,
    ) -> AlphaSubmission:
        """
        Run an alpha through the full submission pipeline.

        Stages:
        1. Backtest
        2. Score
        3. Risk validation
        4. AI review
        5. (Optional) BRAIN simulation
        6. Decision

        Args:
            candidate: AlphaCandidate from generator
            data: Market data for backtest
            existing_alphas: Existing alphas for uniqueness check

        Returns:
            AlphaSubmission with all stage results
        """
        from datetime import datetime
        import importlib

        submission = AlphaSubmission(
            name=candidate.name,
            expression=candidate.expression,
            category=candidate.category,
            description=candidate.description,
            parameters=candidate.parameters,
            created_at=datetime.now().isoformat(),
        )

        # Stage 1: Backtest
        logger.info(f"Backtesting: {candidate.name}")
        if self.engine is None:
            from backtest.engine import BacktestEngine
            self.engine = BacktestEngine()

        result = self.engine.run(
            expression=candidate.expression,
            data=data,
            alpha_name=candidate.name,
        )
        submission.backtest_result = result
        submission.stage = SubmissionStage.BACKTESTED

        # Stage 2: Score
        score = self.metrics.score(result)
        submission.alpha_score = score

        # Stage 3: Risk validation
        validation = self.validator.validate(result)
        submission.validation_result = validation
        submission.stage = SubmissionStage.VALIDATED

        if not validation.passed:
            logger.warning(
                f"Alpha {candidate.name} failed validation: "
                f"{validation.errors}"
            )
            submission.stage = SubmissionStage.REJECTED

        # Stage 4: AI review
        if validation.passed or len(validation.errors) <= 1:
            review = self.reviewer.review(result, score, existing_alphas)
            submission.review_result = review
            submission.stage = SubmissionStage.REVIEWED

        # Stage 5: BRAIN simulation (optional)
        # submission = self._simulate_on_brain(submission, data)

        self._pipeline.append(submission)
        return submission

    def process_batch(
        self,
        candidates: List,
        data: Dict[str, Any],
    ) -> List[AlphaSubmission]:
        """
        Process multiple candidates through the pipeline.

        Returns submissions sorted by quality.
        """
        submissions = []
        for candidate in candidates:
            try:
                submission = self.process(candidate, data)
                submissions.append(submission)
            except Exception as e:
                logger.error(f"Failed to process {candidate.name}: {e}")

        # Sort by score
        submissions.sort(
            key=lambda s: s.alpha_score.total if s.alpha_score else 0,
            reverse=True,
        )
        return submissions

    def get_approved(self) -> List[AlphaSubmission]:
        """Get submissions approved for BRAIN upload."""
        return [
            s for s in self._pipeline
            if s.review_result
            and s.review_result.decision == ReviewDecision.APPROVED
        ]

    def get_needs_revision(self) -> List[AlphaSubmission]:
        """Get submissions that need revision."""
        return [
            s for s in self._pipeline
            if s.review_result
            and s.review_result.decision == ReviewDecision.REVISE
        ]

    def get_rejected(self) -> List[AlphaSubmission]:
        """Get rejected submissions."""
        return [
            s for s in self._pipeline
            if s.review_result
            and s.review_result.decision == ReviewDecision.REJECT
        ]

    def pipeline_summary(self) -> str:
        """Generate a summary of the submission pipeline."""
        total = len(self._pipeline)
        approved = len(self.get_approved())
        revise = len(self.get_needs_revision())
        rejected = len(self.get_rejected())

        lines = [
            "=" * 40,
            "SUBMISSION PIPELINE SUMMARY",
            "=" * 40,
            f"Total processed: {total}",
            f"Approved: {approved}",
            f"Needs revision: {revise}",
            f"Rejected: {rejected}",
            "=" * 40,
        ]

        if approved > 0:
            lines.append("\nAPPROVED FOR SUBMISSION:")
            for s in self.get_approved():
                score = s.alpha_score.total if s.alpha_score else 0
                lines.append(f"  {s.name} (Score: {score:.2f})")

        return "\n".join(lines)
