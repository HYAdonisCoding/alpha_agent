#!/usr/bin/env python3
"""
Daily Alpha Research Pipeline
==============================
Main orchestration script for the daily alpha research workflow.

Pipeline:
  1. Data Update → Load latest market data
  2. Market Analysis → Analyze current market environment
  3. AI Alpha Generation → Generate alpha candidates
  4. Backtest → Backtest all candidates
  5. Scoring & Review → Score and review results
  6. Save Results → Persist to database
  7. Generate Report → Create daily research report

Usage:
    python scripts/daily_run.py
    python scripts/daily_run.py --n 20 --market us
    python scripts/daily_run.py --dry-run
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / "logs" / "daily_run.log", mode="a"),
    ],
)
logger = logging.getLogger("daily_run")

# Ensure logs directory exists
(project_root / "logs").mkdir(exist_ok=True)


def parse_args():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Alpha Agent Daily Research Pipeline"
    )
    parser.add_argument(
        "--n", type=int, default=10,
        help="Number of alpha candidates to generate (default: 10)"
    )
    parser.add_argument(
        "--market", type=str, default="us",
        choices=["us", "cn"],
        help="Market universe (default: us)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without saving to database"
    )
    parser.add_argument(
        "--output-dir", type=str, default="report/output",
        help="Report output directory"
    )
    parser.add_argument(
        "--mode", type=str, default="template",
        choices=["template", "ai"],
        help="Generation mode (default: template)"
    )
    parser.add_argument(
        "--categories", type=str, default=None, nargs="+",
        choices=["momentum", "mean_reversion", "volume", "volatility",
                 "cross_sectional", "combination"],
        help="Limit generation to specific categories (e.g. --categories momentum volatility)"
    )
    return parser.parse_args()


def main():
    """Main daily research pipeline."""
    args = parse_args()

    logger.info("=" * 60)
    logger.info(f"Alpha Agent Daily Run - {datetime.now().isoformat()}")
    logger.info(f"Market: {args.market} | Candidates: {args.n} | Mode: {args.mode}")
    logger.info("=" * 60)

    # ---- Stage 1: Data Update ----
    logger.info("[Stage 1/7] Loading market data...")
    from data.loader import MarketDataLoader

    loader = MarketDataLoader()
    data = loader.load_all(market=args.market)

    prices = data.get("prices", None)
    close = data.get("close", None)
    volume = data.get("volume", None)

    if close is None or close.empty:
        logger.error("No price data available. Aborting.")
        return 1

    logger.info(f"  Loaded {len(close.columns)} symbols, {len(close)} days of data")

    # ---- Stage 2: Market Analysis ----
    logger.info("[Stage 2/7] Analyzing market environment...")
    from ai.researcher import AIResearcher

    researcher = AIResearcher()
    market_state = researcher.analyze_market(prices, volume)
    logger.info(
        f"  Regime: {market_state.regime} | "
        f"Vol: {market_state.volatility:.2%} | "
        f"Trend: {market_state.trend_strength:.3f}"
    )

    # ---- Stage 3: Alpha Generation ----
    logger.info(f"[Stage 3/7] Generating {args.n} alpha candidates...")
    from alpha.generator import AlphaGenerator
    from ai.memory import AlphaMemory

    # Load memory early for dedup — avoid re-generating known failures
    memory = AlphaMemory()
    failed_exprs = memory.get_failed_expressions()
    if failed_exprs:
        logger.info(f"  Memory: {len(failed_exprs)} known-failed expressions will be excluded")

    # Load BRAIN feedback for smarter template selection
    brain_template_weights = memory.get_brain_template_weights()
    brain_category_weights = memory.get_brain_category_weights()
    if brain_template_weights:
        influenced = {k: v for k, v in brain_template_weights.items() if v != 1.0}
        if influenced:
            logger.info(
                f"  BRAIN feedback: {len(influenced)} templates influenced "
                f"(boosted: {sum(1 for v in influenced.values() if v > 1.0)}, "
                f"penalized: {sum(1 for v in influenced.values() if v < 1.0)})"
            )

    generator = AlphaGenerator(mode=args.mode)
    candidates = generator.generate(
        n=args.n,
        market_state={
            "regime": market_state.regime,
        },
        categories=args.categories,
        exclude_expressions=failed_exprs,
        brain_template_weights=brain_template_weights,
        brain_category_weights=brain_category_weights,
    )
    logger.info(f"  Generated {len(candidates)} candidates")

    # ---- Stage 4: Backtest ----
    logger.info("[Stage 4/7] Backtesting candidates...")
    from backtest.engine import BacktestEngine

    engine = BacktestEngine()

    # Prepare data dict for expression evaluation
    eval_data = {"close": close}
    if volume is not None and not volume.empty:
        eval_data["volume"] = volume

    results = []
    for i, candidate in enumerate(candidates, 1):
        logger.info(f"  [{i}/{len(candidates)}] {candidate.name}...")
        try:
            bt_result = engine.run(
                expression=candidate.expression,
                data=eval_data,
                alpha_name=candidate.name,
            )
            results.append({
                "candidate": candidate,
                "backtest": bt_result,
            })
        except Exception as e:
            logger.error(f"  Failed to backtest {candidate.name}: {e}")

    logger.info(f"  Backtested {len(results)}/{len(candidates)} successfully")

    # ---- Stage 5: Scoring & Review ----
    logger.info("[Stage 5/7] Scoring and reviewing...")
    from backtest.metrics import AlphaMetrics
    from ai.reviewer import AIReviewer

    metrics = AlphaMetrics()
    reviewer = AIReviewer()

    # Get existing alphas from memory for uniqueness check
    existing_alphas = memory.query_successes(limit=50)

    scored_results = []
    for r in results:
        score = metrics.score(r["backtest"])
        review = reviewer.review(r["backtest"], score, existing_alphas)

        r["score"] = score
        r["review"] = review

        scored_results.append(r)

        status = "✅" if review.decision.value == "APPROVED" else (
            "🔄" if review.decision.value == "REVISE" else "❌"
        )
        logger.info(
            f"  {status} {r['candidate'].name}: "
            f"Score={score.total:.2f} ({score.grade.value}) | "
            f"Sharpe={r['backtest'].sharpe:.2f} | "
            f"Decision={review.decision.value}"
        )

    # ---- Stage 6: Save Results ----
    n_saved = 0
    n_noise = 0
    n_dup = 0

    if not args.dry_run:
        logger.info("[Stage 6/7] Saving results to database...")
        from storage.database import Database
        from brain.props_generator import generate_brain_props

        db = Database()

        # Load config for thresholds
        import yaml
        with open(project_root / "config" / "settings.yaml") as f:
            config = yaml.safe_load(f)
        min_db_score = config.get("scoring", {}).get("thresholds", {}).get("min_db_score", 0.3)

        # Get already-failed expressions to avoid duplicate DB entries
        failed_exprs = memory.get_failed_expressions()
        # Also check what's already in the DB for this session
        saved_this_run: set = set()

        for r in scored_results:
            c = r["candidate"]
            bt = r["backtest"]
            score = r["score"]
            review = r["review"]

            # ---- Memory recording (always do this — lightweight JSON) ----
            if score.grade.value in ("RECOMMEND_SUBMIT", "NEEDS_OPTIMIZATION"):
                memory.record_success(
                    name=c.name,
                    expression=c.expression,
                    category=c.category,
                    metrics=bt.to_dict(),
                    lessons=f"Score: {score.total:.2f}, {review.decision.value}",
                )
            else:
                memory.record_failure(
                    name=c.name,
                    expression=c.expression,
                    category=c.category,
                    metrics=bt.to_dict(),
                    reason=f"Score: {score.total:.2f}, {review.decision.value}",
                )

            # ---- Database storage (only for quality alphas) ----
            # Skip noise: alphas below minimum quality threshold
            if score.total < min_db_score:
                n_noise += 1
                continue

            # Skip duplicates: already saved this run or previously failed
            if c.expression in saved_this_run or c.expression in failed_exprs:
                n_dup += 1
                continue

            # Generate BRAIN submission properties
            brain_props = generate_brain_props(c, bt)

            alpha_id = db.save_alpha(
                name=c.name,
                expression=c.expression,
                category=c.category,
                description=c.description,
                template_name=c.template_name,
                parameters=c.parameters,
                brain_props=brain_props,
            )

            if alpha_id:
                db.save_backtest(
                    alpha_id=alpha_id,
                    result=bt,
                    score=score.total,
                    grade=score.grade.value,
                )
                saved_this_run.add(c.expression)
                n_saved += 1

        logger.info(
            f"  DB: {n_saved} saved, {n_noise} below threshold ({min_db_score}), "
            f"{n_dup} duplicates skipped"
        )
    else:
        logger.info("[Stage 6/7] Dry run - skipping database save")

    # ---- Stage 7: Generate Report ----
    logger.info("[Stage 7/7] Generating daily report...")
    from report.daily_report import DailyReport

    reporter = DailyReport(output_dir=args.output_dir)

    report_data = []
    for r in scored_results:
        c = r["candidate"]
        bt = r["backtest"]
        review = r["review"]
        score = r["score"]

        report_data.append({
            "name": c.name,
            "category": c.category,
            "description": c.description,
            "expression": c.expression,
            "score": score.total,
            "backtest": bt.to_dict(),
            "review": {
                "decision": review.decision.value,
                "feedback": review.feedback,
            },
        })

    market_state_dict = {
        "regime": market_state.regime,
        "volatility": market_state.volatility,
        "trend_strength": market_state.trend_strength,
    }

    report_content = reporter.generate(
        market_state=market_state_dict,
        results=report_data,
        format="markdown",
    )

    logger.info(f"  Report generated: report/output/")

    # ---- Summary ----
    n_approved = sum(1 for r in scored_results
                     if r["review"].decision.value == "APPROVED")
    n_revise = sum(1 for r in scored_results
                   if r["review"].decision.value == "REVISE")
    n_rejected = sum(1 for r in scored_results
                     if r["review"].decision.value == "REJECT")

    best = max(scored_results, key=lambda r: r["score"].total) if scored_results else None

    logger.info("=" * 60)
    logger.info("DAILY RUN SUMMARY")
    logger.info(f"  Generated: {len(candidates)}")
    logger.info(f"  Backtested: {len(results)}")
    logger.info(f"  Review: Approved={n_approved} Revise={n_revise} Rejected={n_rejected}")
    if not args.dry_run:
        logger.info(f"  DB: {n_saved} saved, {n_noise} noise, {n_dup} dup")
        if n_saved > 0:
            logger.info(f"  → Check saved alphas: python scripts/submit_alpha.py --list")
    if best:
        logger.info(
            f"  Best: {best['candidate'].name} "
            f"(Score: {best['score'].total:.2f}, "
            f"Sharpe: {best['backtest'].sharpe:.2f})"
        )
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
