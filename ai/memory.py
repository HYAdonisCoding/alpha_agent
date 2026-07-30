"""
Alpha Memory Bank
=================
Persistent memory for alpha research experience.

Stores:
- Successful alphas with their metadata
- Failed alphas with lessons learned
- Market regime → effective strategy mappings

Enables the AI agent to learn from past experiments and avoid
repeating failed approaches.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AlphaMemory:
    """
    Persistent memory bank for alpha research.

    Stores experience in JSON files:
    - alpha_success.json: Successful alpha patterns
    - alpha_failed.json: Failed alpha patterns with lessons

    Usage:
        memory = AlphaMemory()
        memory.record_success(alpha_name, metrics, lessons)
        relevant = memory.query("momentum", min_sharpe=1.5)
    """

    def __init__(
        self,
        success_file: str = "ai/alpha_success.json",
        failure_file: str = "ai/alpha_failed.json",
        brain_feedback_file: str = "ai/alpha_brain_feedback.json",
        max_entries: int = 1000,
    ):
        self.success_file = Path(success_file)
        self.failure_file = Path(failure_file)
        self.brain_feedback_file = Path(brain_feedback_file)
        self.max_entries = max_entries
        self._success_cache: List[Dict] = []
        self._failure_cache: List[Dict] = []
        self._brain_feedback_cache: List[Dict] = []
        self._load()

    def _load(self):
        """Load memory from disk."""
        self._success_cache = self._read_json(self.success_file)
        self._failure_cache = self._read_json(self.failure_file)
        self._brain_feedback_cache = self._read_json(self.brain_feedback_file)
        logger.info(
            f"Loaded memory: {len(self._success_cache)} successes, "
            f"{len(self._failure_cache)} failures, "
            f"{len(self._brain_feedback_cache)} brain feedback"
        )

    def _read_json(self, path: Path) -> List[Dict]:
        """Read JSON file, return empty list if not found."""
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read {path}: {e}")
        return []

    def _write_json(self, path: Path, data: List[Dict]):
        """Write data to JSON file, creating parent dirs if needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _trim(self, data: List[Dict]) -> List[Dict]:
        """Trim memory to max_entries, keeping most recent."""
        if len(data) > self.max_entries:
            return data[-self.max_entries:]
        return data

    # ---- Recording ----

    def record_success(
        self,
        name: str,
        expression: str,
        category: str,
        metrics: Dict[str, float],
        lessons: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        Record a successful alpha.

        Args:
            name: Alpha name
            expression: Factor expression
            category: Alpha category
            metrics: Performance metrics dict
            lessons: Lessons learned / why it works
            tags: Searchable tags
        """
        entry = {
            "name": name,
            "expression": expression,
            "category": category,
            "sharpe": metrics.get("sharpe", 0),
            "fitness": metrics.get("fitness", 0),
            "ic_ir": metrics.get("ic_ir", 0),
            "turnover": metrics.get("turnover", 0),
            "max_drawdown": metrics.get("max_drawdown", 0),
            "lesson": lessons or "",
            "tags": tags or [],
            "recorded_at": datetime.now().isoformat(),
        }

        self._success_cache.append(entry)
        self._success_cache = self._trim(self._success_cache)
        self._write_json(self.success_file, self._success_cache)
        logger.info(f"Recorded success: {name} (Sharpe={entry['sharpe']:.2f})")

    def record_failure(
        self,
        name: str,
        expression: str,
        category: str,
        metrics: Dict[str, float],
        reason: str,
        tags: Optional[List[str]] = None,
    ):
        """
        Record a failed alpha with the reason for failure.

        Args:
            name: Alpha name
            expression: Factor expression
            category: Alpha category
            metrics: Performance metrics
            reason: Why it failed (overfitting, low signal, etc.)
            tags: Searchable tags
        """
        entry = {
            "name": name,
            "expression": expression,
            "category": category,
            "sharpe": metrics.get("sharpe", 0),
            "metrics": metrics,
            "reason": reason,
            "tags": tags or [],
            "recorded_at": datetime.now().isoformat(),
        }

        self._failure_cache.append(entry)
        self._failure_cache = self._trim(self._failure_cache)
        self._write_json(self.failure_file, self._failure_cache)
        logger.info(f"Recorded failure: {name} - {reason}")

    def batch_record(
        self,
        results: List[Dict],
        threshold: float = 1.0,
    ):
        """
        Batch record multiple alpha results.

        Args:
            results: List of {name, expression, category, metrics, score}
            threshold: Score threshold for success/failure split
        """
        for r in results:
            if r.get("score", 0) >= threshold:
                self.record_success(
                    name=r["name"],
                    expression=r["expression"],
                    category=r.get("category", "unknown"),
                    metrics=r.get("metrics", {}),
                    lessons=r.get("lesson"),
                    tags=r.get("tags"),
                )
            else:
                self.record_failure(
                    name=r["name"],
                    expression=r["expression"],
                    category=r.get("category", "unknown"),
                    metrics=r.get("metrics", {}),
                    reason=f"Score {r.get('score', 0):.2f} below threshold {threshold}",
                    tags=r.get("tags"),
                )

    # ---- Querying ----

    def query_successes(
        self,
        category: Optional[str] = None,
        min_sharpe: Optional[float] = None,
        min_ic_ir: Optional[float] = None,
        tag: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Query successful alphas with optional filters.

        Args:
            category: Filter by category
            min_sharpe: Minimum Sharpe ratio
            min_ic_ir: Minimum IC IR
            tag: Filter by tag
            limit: Max results

        Returns:
            Matching alpha records, sorted by Sharpe descending
        """
        results = self._success_cache

        if category:
            results = [r for r in results if r.get("category") == category]
        if min_sharpe is not None:
            results = [r for r in results if r.get("sharpe", 0) >= min_sharpe]
        if min_ic_ir is not None:
            results = [r for r in results if r.get("ic_ir", 0) >= min_ic_ir]
        if tag:
            results = [r for r in results if tag in r.get("tags", [])]

        # Sort by Sharpe descending
        results.sort(key=lambda r: r.get("sharpe", 0), reverse=True)
        return results[:limit]

    def query_failures(
        self,
        reason: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Query failed alphas to avoid repeating mistakes.

        Args:
            reason: Filter by failure reason keyword
            category: Filter by category
            limit: Max results
        """
        results = self._failure_cache

        if reason:
            results = [r for r in results if reason.lower() in r.get("reason", "").lower()]
        if category:
            results = [r for r in results if r.get("category") == category]

        results.sort(key=lambda r: r.get("recorded_at", ""), reverse=True)
        return results[:limit]

    def get_lessons(self, category: Optional[str] = None) -> List[str]:
        """Get all lessons learned, optionally filtered by category."""
        lessons = []

        # Success lessons
        successes = self.query_successes(category=category)
        for s in successes:
            if s.get("lesson"):
                lessons.append(f"[SUCCESS] {s['name']}: {s['lesson']}")

        # Failure lessons (what to avoid)
        failures = self.query_failures(category=category)
        for f in failures:
            lessons.append(f"[FAILED] {f['name']}: {f['reason']}")

        return lessons

    def get_top_patterns(
        self, n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get the most effective patterns across all categories.

        Returns list with: category, count, avg_sharpe, best_expression
        """
        from collections import defaultdict

        by_category = defaultdict(list)
        for entry in self._success_cache:
            by_category[entry.get("category", "unknown")].append(entry)

        patterns = []
        for category, entries in by_category.items():
            sharpes = [e.get("sharpe", 0) for e in entries]
            avg_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0
            best = max(entries, key=lambda e: e.get("sharpe", 0))

            patterns.append({
                "category": category,
                "count": len(entries),
                "avg_sharpe": round(avg_sharpe, 3),
                "best_expression": best.get("expression", ""),
                "best_sharpe": best.get("sharpe", 0),
                "best_name": best.get("name", ""),
            })

        patterns.sort(key=lambda p: p["avg_sharpe"], reverse=True)
        return patterns[:n]

    # ---- BRAIN Feedback ----

    def record_brain_feedback(
        self,
        name: str,
        expression: str,
        category: str,
        template_name: str,
        sharpe: float,
        fitness: float,
        turnover: float,
        returns: float,
        drawdown: float,
        margin: float = 0.0,
        status: str = "rejected",
        notes: str = "",
    ):
        """
        Record BRAIN-side performance feedback.

        This is the critical feedback loop: after submitting an alpha to BRAIN,
        the simulation results come back and should be stored here so the
        generator can learn which templates/categories actually work on BRAIN
        (not just on local backtest).

        Args:
            name: Alpha name
            expression: Factor expression
            category: Alpha category
            template_name: Source template name
            sharpe: BRAIN Sharpe ratio
            fitness: BRAIN fitness score
            turnover: BRAIN turnover (decimal, e.g. 0.1379)
            returns: BRAIN returns (decimal, e.g. -0.0283)
            drawdown: BRAIN max drawdown (decimal, e.g. 0.218)
            margin: BRAIN margin (decimal, e.g. -0.000411)
            status: BRAIN acceptance status (accepted/rejected)
            notes: Additional notes
        """
        entry = {
            "name": name,
            "expression": expression,
            "category": category,
            "template_name": template_name,
            "sharpe": sharpe,
            "fitness": fitness,
            "turnover": turnover,
            "returns": returns,
            "drawdown": drawdown,
            "margin": margin,
            "status": status,
            "notes": notes,
            "recorded_at": datetime.now().isoformat(),
        }

        self._brain_feedback_cache.append(entry)
        self._brain_feedback_cache = self._trim(self._brain_feedback_cache)
        self._write_json(self.brain_feedback_file, self._brain_feedback_cache)
        logger.info(
            f"Recorded BRAIN feedback: {name} "
            f"(Sharpe={sharpe:.2f}, Status={status})"
        )

    def get_brain_template_weights(
        self,
        default_weight: float = 1.0,
        boost_factor: float = 2.0,
        penalty_factor: float = 0.3,
    ) -> Dict[str, float]:
        """
        Calculate template generation weights based on BRAIN feedback.

        Templates that produced BRAIN-accepted alphas get boosted.
        Templates that only produced BRAIN-rejected alphas get penalized.
        Templates with no BRAIN feedback keep the default weight.

        Args:
            default_weight: Base weight for templates with no feedback
            boost_factor: Multiplier for BRAIN-accepted templates
            penalty_factor: Multiplier for BRAIN-rejected templates

        Returns:
            Dict mapping template_name -> weight multiplier
        """
        from collections import defaultdict

        by_template = defaultdict(lambda: {"total": 0, "accepted": 0})

        for fb in self._brain_feedback_cache:
            tmpl = fb.get("template_name", "unknown")
            by_template[tmpl]["total"] += 1
            if fb.get("status") == "accepted":
                by_template[tmpl]["accepted"] += 1

        weights = {}
        for tmpl, stats in by_template.items():
            if stats["total"] == 0:
                weights[tmpl] = default_weight
            elif stats["accepted"] > 0:
                # At least one acceptance -> boost
                acc_rate = stats["accepted"] / stats["total"]
                weights[tmpl] = default_weight * (1 + boost_factor * acc_rate)
            else:
                # All rejected -> penalty
                weights[tmpl] = default_weight * penalty_factor

        return weights

    def get_brain_category_weights(
        self,
        default_weight: float = 1.0,
        boost_factor: float = 2.0,
        penalty_factor: float = 0.3,
    ) -> Dict[str, float]:
        """
        Calculate category weights based on BRAIN feedback.

        Same logic as template weights but aggregated by category.
        """
        from collections import defaultdict

        by_cat = defaultdict(lambda: {"total": 0, "accepted": 0})

        for fb in self._brain_feedback_cache:
            cat = fb.get("category", "unknown")
            by_cat[cat]["total"] += 1
            if fb.get("status") == "accepted":
                by_cat[cat]["accepted"] += 1

        weights = {}
        for cat, stats in by_cat.items():
            if stats["total"] == 0:
                weights[cat] = default_weight
            elif stats["accepted"] > 0:
                acc_rate = stats["accepted"] / stats["total"]
                weights[cat] = default_weight * (1 + boost_factor * acc_rate)
            else:
                weights[cat] = default_weight * penalty_factor

        return weights

    def get_brain_feedback_stats(self) -> Dict[str, Any]:
        """Get BRAIN feedback statistics."""
        total = len(self._brain_feedback_cache)
        accepted = sum(1 for f in self._brain_feedback_cache if f.get("status") == "accepted")

        sharpes = [f.get("sharpe", 0) for f in self._brain_feedback_cache]
        avg_sharpe = sum(sharpes) / max(len(sharpes), 1)

        return {
            "total_feedback": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "acceptance_rate": accepted / max(total, 1),
            "avg_brain_sharpe": round(avg_sharpe, 3),
            "best_sharpe": max(sharpes) if sharpes else 0,
            "worst_sharpe": min(sharpes) if sharpes else 0,
        }

    # ---- Utility ----

    def get_failed_expressions(self) -> set:
        """Get set of expressions that have failed, to avoid regenerating."""
        return {f.get("expression", "") for f in self._failure_cache}

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        successes = self._success_cache
        failures = self._failure_cache

        by_cat = {}
        for s in successes:
            cat = s.get("category", "unknown")
            if cat not in by_cat:
                by_cat[cat] = 0
            by_cat[cat] += 1

        return {
            "total_successes": len(successes),
            "total_failures": len(failures),
            "success_rate": len(successes) / max(len(successes) + len(failures), 1),
            "by_category": by_cat,
            "avg_sharpe": (
                sum(s.get("sharpe", 0) for s in successes) / max(len(successes), 1)
            ),
            "top_category": max(by_cat, key=by_cat.get) if by_cat else None,
        }

    def clear(self):
        """Clear all memory (use with caution)."""
        self._success_cache = []
        self._failure_cache = []
        self._brain_feedback_cache = []
        self._write_json(self.success_file, [])
        self._write_json(self.failure_file, [])
        self._write_json(self.brain_feedback_file, [])
        logger.warning("Memory cleared!")
