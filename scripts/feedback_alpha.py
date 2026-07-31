#!/usr/bin/env python3
"""
BRAIN Performance Feedback
============================
Input BRAIN simulation results back into the system so it can learn
and optimize future alpha generation.

This closes the feedback loop:
  Generate -> Backtest -> Score -> Submit -> [BRAIN results] -> FEEDBACK -> Learn

Usage:
    # List submitted alphas awaiting BRAIN feedback
    python scripts/feedback_alpha.py --list-pending

    # Input BRAIN results for a specific alpha by DB ID
    python scripts/feedback_alpha.py --id 3 \\
        --sharpe -0.39 --fitness -0.18 --turnover 0.1379 \\
        --returns -0.0283 --drawdown 0.218 --margin -0.000411

    # Input and explicitly mark as rejected (auto-detected from negative Sharpe)
    python scripts/feedback_alpha.py --id 3 \\
        --sharpe 0.85 --fitness 0.40 --turnover 0.08 \\
        --returns 0.05 --drawdown 0.15 --margin 0.0002 \\
        --status accepted

    # Input by alpha name
    python scripts/feedback_alpha.py --name volume_price_trend_n20 \\
        --sharpe 1.52 --fitness 0.75 --turnover 0.12 \\
        --returns 0.08 --drawdown 0.10 --margin 0.0005

    # Show feedback history
    python scripts/feedback_alpha.py --history

    # Show BRAIN feedback stats (for learning)
    python scripts/feedback_alpha.py --stats

BRAIN Metrics Reference:
    Aggregate Data section on BRAIN alpha detail page:
    - Sharpe:      Sharpe ratio (e.g. -0.39)
    - Turnover:    Turnover rate (e.g. 13.79% -> 0.1379)
    - Fitness:     Fitness score (e.g. -0.18)
    - Returns:     Return rate (e.g. -2.83% -> -0.0283)
    - Drawdown:    Max drawdown (e.g. 21.80% -> 0.218)
    - Margin:      Margin (e.g. -4.11‱ -> -0.000411)
"""

import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("feedback_alpha")

# BRAIN acceptance thresholds (auto-detection)
# An alpha is auto-marked "accepted" if ALL these conditions are met:
BRAIN_ACCEPT_THRESHOLDS = {
    "sharpe": 0.0,      # Sharpe must be > 0
    "fitness": 0.0,     # Fitness must be > 0
    "returns": 0.0,     # Returns must be > 0
}


def parse_args():
    import argparse

    p = argparse.ArgumentParser(
        description="Input BRAIN performance feedback for learning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/feedback_alpha.py --list-pending
  python scripts/feedback_alpha.py --id 3 --sharpe -0.39 --fitness -0.18 --turnover 0.1379 --returns -0.0283 --drawdown 0.218 --margin -0.000411
  python scripts/feedback_alpha.py --stats
""",
    )
    # Query commands
    p.add_argument("--list-pending", action="store_true",
                   help="List submitted alphas awaiting BRAIN feedback")
    p.add_argument("--history", action="store_true",
                   help="Show BRAIN feedback history")
    p.add_argument("--stats", action="store_true",
                   help="Show BRAIN feedback summary statistics for learning")

    # Alpha identification
    p.add_argument("--id", type=int,
                   help="Alpha database ID to record feedback for")
    p.add_argument("--name", type=str,
                   help="Alpha name to record feedback for")

    # BRAIN metrics (all required when recording feedback)
    p.add_argument("--sharpe", "-s", type=float,
                   help="BRAIN Sharpe ratio (e.g. -0.39)")
    p.add_argument("--fitness", "-f", type=float,
                   help="BRAIN fitness score (e.g. -0.18)")
    p.add_argument("--turnover", "-t", type=float,
                   help="BRAIN turnover rate as decimal (e.g. 0.1379 = 13.79%%)")
    p.add_argument("--returns", "-r", type=float,
                   help="BRAIN return rate as decimal (e.g. -0.0283 = -2.83%%)")
    p.add_argument("--drawdown", "-d", type=float,
                   help="BRAIN max drawdown as decimal (e.g. 0.218 = 21.80%%)")
    p.add_argument("--margin", "-m", type=float, default=0.0,
                   help="BRAIN margin as decimal (e.g. -0.000411 = -4.11‱)")

    # Status
    p.add_argument("--status", type=str, default="auto",
                   choices=["auto", "accepted", "rejected"],
                   help="BRAIN acceptance status (auto: detect from metrics, default)")
    p.add_argument("--notes", type=str, default="",
                   help="Additional notes about the BRAIN result")

    return p.parse_args()


def auto_detect_status(sharpe, fitness, returns):
    """Auto-detect BRAIN acceptance based on thresholds."""
    if (sharpe > BRAIN_ACCEPT_THRESHOLDS["sharpe"] and
        fitness > BRAIN_ACCEPT_THRESHOLDS["fitness"] and
        returns > BRAIN_ACCEPT_THRESHOLDS["returns"]):
        return "accepted"
    return "rejected"


def format_pct(value: float) -> str:
    """Format decimal as percentage string."""
    return f"{value * 100:.2f}%"


def format_bp(value: float) -> str:
    """Format decimal as basis points string."""
    return f"{value * 10000:.2f}‱"


def cmd_list_pending(db):
    """List submitted alphas that haven't received BRAIN feedback."""
    pending = db.get_pending_feedback(limit=50)

    if not pending:
        print("\n  No alphas awaiting BRAIN feedback. All submitted alphas have been processed.\n")
        return

    print(f"\n  {'ID':<4} {'Name':<35} {'Category':<18} {'Local Score':>10} {'Submitted':<20}")
    print(f"  {'-'*4} {'-'*35} {'-'*18} {'-'*10} {'-'*20}")

    for a in pending:
        submitted_at = (a.get("submitted_at") or "")[:19]
        local_score = a.get("local_score") or 0

        print(
            f"  {a['id']:<4} {a['name']:<35} {a['category']:<18} "
            f"{local_score:>10.2f} {submitted_at:<20}"
        )

    print(f"\n  Total: {len(pending)} alphas awaiting BRAIN feedback")
    print(f"  → Use --id <N> --sharpe ... --fitness ... to record feedback\n")


def cmd_history(db):
    """Show BRAIN feedback history."""
    sql = """
    SELECT bf.*, a.name as alpha_name, a.category, a.template_name
    FROM brain_feedback bf
    INNER JOIN alphas a ON bf.alpha_id = a.id
    ORDER BY bf.recorded_at DESC
    LIMIT 50
    """
    rows = db._execute(sql, fetch=True)
    feedbacks = [dict(r) for r in (rows or [])]

    if not feedbacks:
        print("\n  No BRAIN feedback recorded yet.\n")
        return

    print(f"\n  {'Alpha':<35} {'Category':<18} {'BRAIN Sharpe':>12} {'BRAIN Status':>13} {'Recorded':<20}")
    print(f"  {'-'*35} {'-'*18} {'-'*12} {'-'*13} {'-'*20}")

    for f in feedbacks:
        recorded = (f.get("recorded_at") or "")[:19]
        status_icon = "✅" if f["status"] == "accepted" else "❌"

        print(
            f"  {f['alpha_name']:<35} {f['category']:<18} "
            f"{f['sharpe']:>12.2f} {status_icon} {f['status']:<8} "
            f"{recorded:<20}"
        )

    print(f"\n  Total: {len(feedbacks)} feedback records\n")


def cmd_stats(db):
    """Show BRAIN feedback statistics for learning purposes."""
    summary = db.get_brain_feedback_summary()

    total = summary.get("total_feedback", 0)
    if total == 0:
        print("\n  No BRAIN feedback data available yet.\n")
        return

    print(f"\n  ═══ BRAIN Feedback Summary ({total} total) ═══\n")

    # Category stats
    print("  By Category:")
    print(f"  {'Category':<20} {'Count':>6} {'Accepted':>9} {'Rate':>8} {'Avg Sharpe':>10}")
    print(f"  {'-'*20} {'-'*6} {'-'*9} {'-'*8} {'-'*10}")

    by_cat = summary.get("by_category", {})
    for cat in sorted(by_cat.keys()):
        c = by_cat[cat]
        print(
            f"  {cat:<20} {c['total']:>6} {c['accepted']:>9} "
            f"{c['acceptance_rate']:>7.0%} {c['avg_sharpe']:>10.2f}"
        )

    # Template stats
    print(f"\n  By Template:")
    print(f"  {'Template':<35} {'Count':>6} {'Accepted':>9} {'Rate':>8} {'Avg Sharpe':>10}")
    print(f"  {'-'*35} {'-'*6} {'-'*9} {'-'*8} {'-'*10}")

    by_tmpl = summary.get("by_template", {})
    for tmpl in sorted(by_tmpl.keys()):
        t = by_tmpl[tmpl]
        print(
            f"  {tmpl:<35} {t['total']:>6} {t['accepted']:>9} "
            f"{t['acceptance_rate']:>7.0%} {t.get('avg_sharpe', 0):>10.2f}"
        )

    # Best and worst
    all_templates = [(k, v) for k, v in by_tmpl.items()]
    if all_templates:
        best = max(all_templates, key=lambda x: x[1].get("avg_sharpe", -999))
        worst = min(all_templates, key=lambda x: x[1].get("avg_sharpe", 999))
        print(f"\n  🏆 Best template:  {best[0]} (avg BRAIN Sharpe: {best[1].get('avg_sharpe', 0):.2f})")
        print(f"  📉 Worst template: {worst[0]} (avg BRAIN Sharpe: {worst[1].get('avg_sharpe', 0):.2f})")

    print()


def cmd_feedback(db, args):
    """Record BRAIN performance feedback for an alpha."""
    from ai.memory import AlphaMemory

    # Validate required metrics
    required = ["sharpe", "fitness", "turnover", "returns", "drawdown"]
    missing = [f for f in required if getattr(args, f) is None]
    if missing:
        logger.error(f"Missing required BRAIN metrics: {', '.join(missing)}")
        logger.error("All required: --sharpe --fitness --turnover --returns --drawdown")
        return 1

    # Find alpha
    if args.id:
        alpha = db.get_alpha(args.id)
        if not alpha:
            logger.error(f"No alpha found with ID={args.id}")
            return 1
    elif args.name:
        alpha = db.get_alpha_by_name(args.name)
        if not alpha:
            logger.error(f"No alpha found with name='{args.name}'")
            return 1
    else:
        logger.error("Must specify --id or --name")
        return 1

    alpha_id = alpha["id"]
    alpha_name = alpha["name"]

    # Determine BRAIN acceptance status
    if args.status == "auto":
        status = auto_detect_status(args.sharpe, args.fitness, args.returns)
        logger.info(f"  Auto-detected status: {status}")
    else:
        status = args.status

    status_icon = "✅" if status == "accepted" else "❌"

    # Display what we're about to record
    print(f"\n  Recording BRAIN feedback for: {alpha_name} (ID={alpha_id})")
    print(f"  Category: {alpha.get('category', 'N/A')}")
    print(f"  Template: {alpha.get('template_name', 'N/A')}")
    print(f"  {'-'*40}")
    print(f"  BRAIN Sharpe:   {args.sharpe:>8.2f}")
    print(f"  BRAIN Fitness:  {args.fitness:>8.2f}")
    print(f"  BRAIN Turnover: {format_pct(args.turnover):>8}")
    print(f"  BRAIN Returns:  {format_pct(args.returns):>8}")
    print(f"  BRAIN Drawdown: {format_pct(args.drawdown):>8}")
    print(f"  BRAIN Margin:   {format_bp(args.margin):>8}")
    print(f"  BRAIN Status:   {status_icon} {status}")
    print()

    # Save to database
    feedback_id = db.save_brain_feedback(
        alpha_id=alpha_id,
        sharpe=args.sharpe,
        fitness=args.fitness,
        turnover=args.turnover,
        returns=args.returns,
        drawdown=args.drawdown,
        margin=args.margin,
        status=status,
        notes=args.notes,
    )

    if feedback_id:
        logger.info(f"  Saved BRAIN feedback (ID={feedback_id})")
    else:
        logger.error("  Failed to save feedback to database")
        return 1

    # Record in memory for future generation
    memory = AlphaMemory()
    memory.record_brain_feedback(
        name=alpha_name,
        expression=alpha.get("expression", ""),
        category=alpha.get("category", "unknown"),
        template_name=alpha.get("template_name", ""),
        sharpe=args.sharpe,
        fitness=args.fitness,
        turnover=args.turnover,
        returns=args.returns,
        drawdown=args.drawdown,
        margin=args.margin,
        status=status,
        notes=args.notes,
    )
    logger.info(f"  Recorded in AI memory for future learning")

    # Verify the submission record was updated
    brain_status_value = db._execute(
        "SELECT brain_status, brain_sharpe FROM submissions WHERE alpha_id=? AND brain_sharpe IS NOT NULL ORDER BY id DESC LIMIT 1",
        (alpha_id,),
        fetch=True,
    )
    if brain_status_value:
        logger.info(f"  Submission updated: brain_status={brain_status_value[0][0]}, brain_sharpe={brain_status_value[0][1]}")

    print(f"\n  ✅ Feedback recorded. System will use this to optimize future generation.\n")
    return 0


def main():
    args = parse_args()
    from storage.database import Database

    db = Database()

    try:
        if args.list_pending:
            cmd_list_pending(db)
        elif args.history:
            cmd_history(db)
        elif args.stats:
            cmd_stats(db)
        elif args.id or args.name:
            return cmd_feedback(db, args)
        else:
            # Default: show overview
            pending = db.get_pending_feedback(limit=100)

            summary = db.get_brain_feedback_summary()
            total_fb = summary.get("total_feedback", 0)

            print(f"\n  ═══ Feedback Loop Status ═══")
            print(f"  Awaiting feedback:  {len(pending)} submitted alphas")
            print(f"  Feedback recorded:  {total_fb} BRAIN results")
            print()
            print(f"  Commands:")
            print(f"    --list-pending     See alphas needing feedback")
            print(f"    --id <N> --sharpe ... --fitness ...     Input BRAIN results")
            print(f"    --history          View feedback history")
            print(f"    --stats            View learning statistics")
            print()
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
