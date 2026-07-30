"""
Database Manager
================
High-level database operations for alpha research platform.

Provides CRUD operations for alphas, backtests, submissions, and daily runs.
"""

import json
import logging
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from pathlib import Path

from .models import init_db

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager for alpha research.

    Usage:
        db = Database("storage/alpha.db")
        alpha_id = db.save_alpha(name="momentum_20", expression="rank(ts_delta(close,20))")
        db.save_backtest(alpha_id=alpha_id, result=backtest_result)
    """

    def __init__(self, db_path: str = "storage/alpha.db"):
        self.db_path = db_path
        self.conn = init_db(db_path)

    def _execute(
        self, sql: str, params: tuple = (), fetch: bool = False
    ) -> Optional[Any]:
        """Execute SQL with error handling."""
        try:
            cursor = self.conn.execute(sql, params)
            self.conn.commit()
            if fetch:
                return cursor.fetchall()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            self.conn.rollback()
            return None

    # ---- Alphas ----

    def save_alpha(
        self,
        name: str,
        expression: str,
        category: str = "unknown",
        description: str = "",
        template_name: str = "",
        parameters: Optional[Dict] = None,
        brain_props: Optional[Dict] = None,
    ) -> Optional[int]:
        """
        Save or update an alpha definition.

        Args:
            name: Internal alpha name
            expression: Alpha factor expression
            category: Strategy category (momentum, mean_reversion, etc.)
            description: Internal description
            template_name: Source template name
            parameters: Template parameter values
            brain_props: BRAIN submission properties {brain_name, tags, color, description}

        Returns alpha_id.
        """
        params_json = json.dumps(parameters) if parameters else "{}"
        brain_json = json.dumps(brain_props) if brain_props else None

        # Upsert: update if exists, insert if not
        sql = """
        INSERT INTO alphas (name, category, description, expression, template_name, parameters, brain_props)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name, expression) DO UPDATE SET
            category=excluded.category,
            description=excluded.description,
            brain_props=COALESCE(excluded.brain_props, brain_props),
            updated_at=CURRENT_TIMESTAMP
        """
        alpha_id = self._execute(
            sql, (name, category, description, expression, template_name, params_json, brain_json)
        )

        if alpha_id is None:
            # Fallback: get existing ID
            row = self._execute(
                "SELECT id FROM alphas WHERE name=? AND expression=?",
                (name, expression),
                fetch=True,
            )
            if row:
                alpha_id = row[0][0]

        return alpha_id

    def get_alpha(self, alpha_id: int) -> Optional[Dict]:
        """Get alpha by ID."""
        rows = self._execute(
            "SELECT * FROM alphas WHERE id=?", (alpha_id,), fetch=True
        )
        if rows:
            return dict(rows[0])
        return None

    def get_alpha_by_name(self, name: str) -> Optional[Dict]:
        """Get alpha by name (most recent)."""
        rows = self._execute(
            "SELECT * FROM alphas WHERE name=? ORDER BY created_at DESC LIMIT 1",
            (name,),
            fetch=True,
        )
        if rows:
            return dict(rows[0])
        return None

    def list_alphas(
        self,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 50,
    ) -> List[Dict]:
        """List alphas with optional filters."""
        sql = "SELECT * FROM alphas WHERE status=?"
        params = [status]

        if category:
            sql += " AND category=?"
            params.append(category)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self._execute(sql, tuple(params), fetch=True)
        return [dict(r) for r in (rows or [])]

    def search_alphas(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Search alphas by name, category, or description."""
        sql = """
        SELECT * FROM alphas
        WHERE name LIKE ? OR category LIKE ? OR description LIKE ?
        ORDER BY created_at DESC LIMIT ?
        """
        pattern = f"%{keyword}%"
        rows = self._execute(sql, (pattern, pattern, pattern, limit), fetch=True)
        return [dict(r) for r in (rows or [])]

    # ---- Backtests ----

    def save_backtest(
        self,
        alpha_id: int,
        result,
        score: float = 0,
        grade: str = "",
    ) -> Optional[int]:
        """
        Save a backtest result.

        Args:
            alpha_id: Alpha ID
            result: BacktestResult from backtest engine
            score: Alpha score
            grade: Alpha grade
        """
        sql = """
        INSERT INTO backtests (
            alpha_id, sharpe, fitness, turnover, max_drawdown,
            annual_return, annual_volatility, calmar_ratio, win_rate,
            ic_mean, ic_ir, ic_std, ic_positive_ratio,
            score, grade, n_days, n_assets
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute(sql, (
            alpha_id,
            result.sharpe,
            result.fitness,
            result.turnover,
            result.max_drawdown,
            result.annual_return,
            result.annual_volatility,
            result.calmar_ratio,
            result.win_rate,
            result.ic_mean,
            result.ic_ir,
            result.ic_std,
            result.ic_positive_ratio,
            score,
            grade,
            result.n_days,
            result.n_assets,
        ))

    def get_latest_backtest(self, alpha_id: int) -> Optional[Dict]:
        """Get the most recent backtest for an alpha."""
        rows = self._execute(
            "SELECT * FROM backtests WHERE alpha_id=? ORDER BY run_at DESC LIMIT 1",
            (alpha_id,),
            fetch=True,
        )
        if rows:
            return dict(rows[0])
        return None

    def get_top_alphas(
        self, min_score: float = 1.0, limit: int = 20
    ) -> List[Dict]:
        """Get top-performing alphas with their latest backtest results."""
        sql = """
        SELECT a.*, b.sharpe, b.fitness, b.turnover, b.max_drawdown,
               b.ic_ir, b.score, b.grade, b.run_at as backtest_date
        FROM alphas a
        INNER JOIN backtests b ON a.id = b.alpha_id
        WHERE b.id IN (
            SELECT MAX(id) FROM backtests GROUP BY alpha_id
        )
        AND b.score >= ?
        ORDER BY b.score DESC
        LIMIT ?
        """
        rows = self._execute(sql, (min_score, limit), fetch=True)
        return [dict(r) for r in (rows or [])]

    # ---- Submissions ----

    def save_submission(
        self,
        alpha_id: int,
        brain_alpha_id: str = "",
        status: str = "pending",
        simulation_result: Optional[Dict] = None,
        notes: str = "",
    ) -> Optional[int]:
        """Record a BRAIN submission."""
        sim_json = json.dumps(simulation_result) if simulation_result else None

        sql = """
        INSERT INTO submissions (alpha_id, brain_alpha_id, status, simulation_result, notes)
        VALUES (?, ?, ?, ?, ?)
        """
        return self._execute(sql, (alpha_id, brain_alpha_id, status, sim_json, notes))

    def update_submission_status(
        self, submission_id: int, status: str, notes: str = "",
        brain_status: Optional[str] = None,
    ):
        """Update submission status and optionally brain_status."""
        if status == "submitted":
            self._execute(
                "UPDATE submissions SET status=?, submitted_at=CURRENT_TIMESTAMP, notes=? WHERE id=?",
                (status, notes, submission_id),
            )
        elif status in ("accepted", "rejected"):
            self._execute(
                "UPDATE submissions SET status=?, accepted_at=CURRENT_TIMESTAMP, notes=? WHERE id=?",
                (status, notes, submission_id),
            )
        else:
            self._execute(
                "UPDATE submissions SET status=?, notes=? WHERE id=?",
                (status, notes, submission_id),
            )

        if brain_status:
            self._execute(
                "UPDATE submissions SET brain_status=? WHERE id=?",
                (brain_status, submission_id),
            )

    # ---- Submission tracking ----

    def mark_submitted(
        self,
        alpha_id: int,
        brain_alpha_id: str = "",
        notes: str = "",
    ) -> Optional[int]:
        """
        Mark an alpha as submitted to BRAIN.

        Creates a submission record with status='submitted'. If a pending
        submission already exists, updates it instead.
        """
        # Check for existing pending/submitted record
        existing = self._execute(
            "SELECT id FROM submissions WHERE alpha_id=? AND status IN ('pending','submitted')",
            (alpha_id,),
            fetch=True,
        )
        if existing:
            sid = existing[0][0]
            self._execute(
                "UPDATE submissions SET status='submitted', brain_alpha_id=?, "
                "submitted_at=CURRENT_TIMESTAMP, notes=? WHERE id=?",
                (brain_alpha_id, notes, sid),
            )
            return sid
        else:
            return self.save_submission(
                alpha_id=alpha_id,
                brain_alpha_id=brain_alpha_id,
                status="submitted",
                notes=notes,
            )

    def get_unsubmitted(
        self,
        min_score: float = 0.0,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Get alphas that have NOT been submitted to BRAIN, with their
        latest backtest scores and brain_props.

        Returns list of dicts with alpha + backtest + brain_props fields.
        """
        sql = """
        SELECT a.id, a.name, a.category, a.expression, a.brain_props,
               a.created_at, a.template_name,
               b.sharpe, b.fitness, b.turnover, b.max_drawdown,
               b.ic_ir, b.score, b.grade, b.run_at as backtest_date,
               CASE WHEN s.id IS NOT NULL THEN s.status ELSE NULL END as submission_status,
               s.brain_alpha_id, s.submitted_at
        FROM alphas a
        INNER JOIN backtests b ON a.id = b.alpha_id
        LEFT JOIN submissions s ON a.id = s.alpha_id
            AND s.id = (SELECT MAX(id) FROM submissions WHERE alpha_id=a.id)
        WHERE b.id IN (SELECT MAX(id) FROM backtests GROUP BY alpha_id)
          AND a.status = 'active'
          AND (s.id IS NULL OR s.status NOT IN ('submitted', 'accepted'))
          AND b.score >= ?
        ORDER BY b.score DESC
        LIMIT ?
        """
        rows = self._execute(sql, (min_score, limit), fetch=True)
        return [dict(r) for r in (rows or [])]

    def get_submitted(self, limit: int = 50) -> List[Dict]:
        """Get alphas that have been submitted to BRAIN."""
        sql = """
        SELECT a.id, a.name, a.category, a.expression, a.template_name, a.brain_props,
               b.sharpe, b.fitness, b.score, b.grade,
               s.id as submission_id,
               s.status as submission_status, s.brain_alpha_id,
               s.brain_sharpe, s.brain_fitness, s.brain_turnover,
               s.brain_returns, s.brain_drawdown, s.brain_margin,
               s.brain_status,
               s.submitted_at, s.accepted_at, s.notes
        FROM alphas a
        INNER JOIN submissions s ON a.id = s.alpha_id
        LEFT JOIN backtests b ON a.id = b.alpha_id
            AND b.id = (SELECT MAX(id) FROM backtests WHERE alpha_id=a.id)
        WHERE s.status IN ('submitted', 'accepted')
        ORDER BY s.submitted_at DESC
        LIMIT ?
        """
        rows = self._execute(sql, (limit,), fetch=True)
        return [dict(r) for r in (rows or [])]

    # ---- Brain Feedback ----

    def save_brain_feedback(
        self,
        alpha_id: int,
        sharpe: float,
        fitness: float,
        turnover: float,
        returns: float,
        drawdown: float,
        margin: float = 0.0,
        status: str = "rejected",
        submission_id: Optional[int] = None,
        notes: str = "",
    ) -> Optional[int]:
        """
        Record BRAIN-side performance feedback for an alpha.

        Updates the submission record with BRAIN metrics and also creates
        a dedicated feedback record for historical tracking.

        Args:
            alpha_id: Alpha database ID
            sharpe: BRAIN Sharpe ratio
            fitness: BRAIN fitness score
            turnover: BRAIN turnover rate (as decimal, e.g. 0.1379 = 13.79%)
            returns: BRAIN returns (as decimal, e.g. -0.0283 = -2.83%)
            drawdown: BRAIN max drawdown (as decimal, e.g. 0.218 = 21.80%)
            margin: BRAIN margin (as decimal, e.g. -0.000411 = -4.11‱)
            status: BRAIN acceptance status (accepted/rejected)
            submission_id: Related submission record ID
            notes: Additional notes

        Returns:
            Feedback record ID
        """
        # 1. Find the latest submission for this alpha if not provided
        if submission_id is None:
            existing = self._execute(
                "SELECT id FROM submissions WHERE alpha_id=? AND status='submitted' ORDER BY id DESC LIMIT 1",
                (alpha_id,),
                fetch=True,
            )
            if existing:
                submission_id = existing[0][0]

        # 2. Update submission record with BRAIN metrics
        if submission_id:
            self._execute(
                """UPDATE submissions SET
                    brain_sharpe=?, brain_fitness=?, brain_turnover=?,
                    brain_returns=?, brain_drawdown=?, brain_margin=?,
                    brain_status=?, notes=CASE WHEN notes='' OR notes IS NULL THEN ? ELSE notes || '; ' || ? END,
                    accepted_at=CASE WHEN ? IN ('accepted','rejected') THEN CURRENT_TIMESTAMP ELSE accepted_at END
                WHERE id=?""",
                (sharpe, fitness, turnover, returns, drawdown, margin,
                 status, notes, notes, status, submission_id),
            )

        # 3. Create dedicated feedback record
        sql = """
        INSERT INTO brain_feedback (alpha_id, submission_id, sharpe, fitness, turnover,
                                     returns, drawdown, margin, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute(sql, (
            alpha_id, submission_id, sharpe, fitness, turnover,
            returns, drawdown, margin, status, notes,
        ))

    def get_pending_feedback(self, limit: int = 50) -> List[Dict]:
        """
        Get submitted alphas that have NOT received BRAIN feedback yet.

        Returns alphas where submission status is 'submitted' but
        brain_status is NULL (no feedback recorded).
        """
        sql = """
        SELECT a.id, a.name, a.category, a.expression, a.template_name,
               s.id as submission_id, s.brain_alpha_id,
               s.submitted_at, s.notes as submission_notes,
               b.sharpe as local_sharpe, b.fitness as local_fitness, b.score as local_score
        FROM alphas a
        INNER JOIN submissions s ON a.id = s.alpha_id
        LEFT JOIN backtests b ON a.id = b.alpha_id
            AND b.id = (SELECT MAX(id) FROM backtests WHERE alpha_id=a.id)
        WHERE s.status = 'submitted'
          AND s.brain_status IS NULL
        ORDER BY s.submitted_at ASC
        LIMIT ?
        """
        rows = self._execute(sql, (limit,), fetch=True)
        return [dict(r) for r in (rows or [])]

    def get_brain_feedback_summary(self) -> Dict[str, Any]:
        """
        Get aggregated BRAIN feedback summary for learning.

        Returns stats by template_name and category:
        - acceptance rate
        - avg BRAIN sharpe
        - best/worst templates
        """
        sql = """
        SELECT a.template_name, a.category,
               COUNT(*) as total,
               SUM(CASE WHEN bf.status='accepted' THEN 1 ELSE 0 END) as accepted,
               AVG(bf.sharpe) as avg_sharpe,
               AVG(bf.fitness) as avg_fitness,
               AVG(bf.turnover) as avg_turnover,
               MAX(bf.sharpe) as best_sharpe,
               MIN(bf.sharpe) as worst_sharpe
        FROM brain_feedback bf
        INNER JOIN alphas a ON bf.alpha_id = a.id
        GROUP BY a.template_name, a.category
        ORDER BY avg_sharpe DESC
        """
        rows = self._execute(sql, fetch=True)

        by_template = {}
        by_category_agg = {}
        for r in (rows or []):
            d = dict(r)
            tmpl = d["template_name"] or "unknown"
            cat = d["category"] or "unknown"
            d["acceptance_rate"] = d["accepted"] / max(d["total"], 1)

            by_template[tmpl] = d

            if cat not in by_category_agg:
                by_category_agg[cat] = {"total": 0, "accepted": 0, "sharpes": []}
            by_category_agg[cat]["total"] += d["total"]
            by_category_agg[cat]["accepted"] += d["accepted"]
            by_category_agg[cat]["sharpes"].append(d["avg_sharpe"])

        by_category = {}
        for cat, agg in by_category_agg.items():
            by_category[cat] = {
                "total": agg["total"],
                "accepted": agg["accepted"],
                "acceptance_rate": agg["accepted"] / max(agg["total"], 1),
                "avg_sharpe": sum(agg["sharpes"]) / max(len(agg["sharpes"]), 1),
            }

        return {
            "by_template": by_template,
            "by_category": by_category,
            "total_feedback": sum(d["total"] for d in (by_template.values())),
        }

    def get_alpha_brain_feedback(self, alpha_id: int) -> List[Dict]:
        """Get all BRAIN feedback records for an alpha."""
        rows = self._execute(
            "SELECT * FROM brain_feedback WHERE alpha_id=? ORDER BY recorded_at DESC",
            (alpha_id,),
            fetch=True,
        )
        return [dict(r) for r in (rows or [])]

    def delete_alpha_cascade(self, alpha_id: int) -> bool:
        """
        Delete an alpha and all related records (backtests, submissions).

        Returns True if successful.
        """
        try:
            self._execute("DELETE FROM submissions WHERE alpha_id=?", (alpha_id,))
            self._execute("DELETE FROM backtests WHERE alpha_id=?", (alpha_id,))
            self._execute("DELETE FROM alphas WHERE id=?", (alpha_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to delete alpha {alpha_id}: {e}")
            self.conn.rollback()
            return False

    def get_low_score_unsubmitted(
        self,
        max_score: float = 0.5,
        older_than_days: int = 0,
    ) -> List[Dict]:
        """
        Get alphas ready for cleanup: low score, unsubmitted, optionally old.

        Args:
            max_score: Alphas with score <= this value
            older_than_days: Only alphas created more than N days ago (0 = any age)
        """
        sql = """
        SELECT a.id, a.name, a.category, a.expression, a.created_at,
               b.sharpe, b.fitness, b.score, b.grade,
               CASE WHEN s.id IS NOT NULL THEN s.status ELSE 'never' END as submission_status
        FROM alphas a
        INNER JOIN backtests b ON a.id = b.alpha_id
        LEFT JOIN submissions s ON a.id = s.alpha_id
            AND s.id = (SELECT MAX(id) FROM submissions WHERE alpha_id=a.id)
        WHERE b.id IN (SELECT MAX(id) FROM backtests GROUP BY alpha_id)
          AND a.status = 'active'
          AND b.score <= ?
          AND (s.id IS NULL OR s.status NOT IN ('submitted', 'accepted'))
        """
        params: list = [max_score]

        if older_than_days > 0:
            sql += " AND a.created_at <= date('now', ?)"
            params.append(f"-{older_than_days} days")

        sql += " ORDER BY b.score ASC"
        rows = self._execute(sql, tuple(params), fetch=True)
        return [dict(r) for r in (rows or [])]

    # ---- Daily Runs ----

    def start_daily_run(
        self, run_date: Optional[str] = None, market_regime: str = ""
    ) -> int:
        """Start a new daily research run."""
        if run_date is None:
            run_date = date.today().isoformat()

        sql = """
        INSERT INTO daily_runs (run_date, market_regime) VALUES (?, ?)
        ON CONFLICT(run_date) DO UPDATE SET started_at=CURRENT_TIMESTAMP
        """
        self._execute(sql, (run_date, market_regime))

        row = self._execute(
            "SELECT id FROM daily_runs WHERE run_date=?", (run_date,), fetch=True
        )
        return row[0][0] if row else 0

    def complete_daily_run(
        self,
        run_id: int,
        alphas_generated: int = 0,
        alphas_backtested: int = 0,
        alphas_approved: int = 0,
        alphas_submitted: int = 0,
        best_alpha_name: str = "",
        best_alpha_score: float = 0,
        notes: str = "",
    ):
        """Mark a daily run as completed with results."""
        sql = """
        UPDATE daily_runs SET
            alphas_generated=?, alphas_backtested=?, alphas_approved=?,
            alphas_submitted=?, best_alpha_name=?, best_alpha_score=?,
            notes=?, completed_at=CURRENT_TIMESTAMP
        WHERE id=?
        """
        self._execute(sql, (
            alphas_generated, alphas_backtested, alphas_approved,
            alphas_submitted, best_alpha_name, best_alpha_score,
            notes, run_id,
        ))

    def get_recent_runs(self, n: int = 10) -> List[Dict]:
        """Get recent daily runs."""
        rows = self._execute(
            "SELECT * FROM daily_runs ORDER BY run_date DESC LIMIT ?",
            (n,),
            fetch=True,
        )
        return [dict(r) for r in (rows or [])]

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        """Get platform statistics."""
        stats = {}

        # Total alphas
        row = self._execute("SELECT COUNT(*) FROM alphas WHERE status='active'", fetch=True)
        stats["total_alphas"] = row[0][0] if row else 0

        # Total backtests
        row = self._execute("SELECT COUNT(*) FROM backtests", fetch=True)
        stats["total_backtests"] = row[0][0] if row else 0

        # Top Sharpe
        row = self._execute(
            "SELECT a.name, b.sharpe FROM alphas a INNER JOIN backtests b ON a.id=b.alpha_id ORDER BY b.sharpe DESC LIMIT 1",
            fetch=True,
        )
        if row:
            stats["top_sharpe_name"] = row[0][0]
            stats["top_sharpe"] = row[0][1]

        # Category breakdown
        rows = self._execute(
            "SELECT category, COUNT(*) as cnt FROM alphas WHERE status='active' GROUP BY category ORDER BY cnt DESC",
            fetch=True,
        )
        stats["by_category"] = {r[0]: r[1] for r in (rows or [])}

        return stats

    def close(self):
        """Close database connection."""
        self.conn.close()
