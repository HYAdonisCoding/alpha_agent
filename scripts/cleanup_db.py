#!/usr/bin/env python3
"""
Database Cleanup Tool
======================
Safely remove low-score, unsubmitted alphas from the database.

DESIGN PRINCIPLE:
  - NEVER deletes submitted/accepted alphas
  - Always shows what will be deleted BEFORE doing anything
  - Requires explicit confirmation (--force flag)
  - Dry-run by default

Usage:
    # Preview what would be cleaned (safe, no changes)
    python scripts/cleanup_db.py --dry-run

    # Clean alphas with score < 0.5
    python scripts/cleanup_db.py --max-score 0.5 --force

    # Clean alphas older than 30 days with score < 0.3
    python scripts/cleanup_db.py --max-score 0.3 --days 30 --force

    # See current DB stats
    python scripts/cleanup_db.py --stats
"""

import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("cleanup_db")


def parse_args():
    import argparse

    p = argparse.ArgumentParser(
        description="Safely clean low-score unsubmitted alphas from database"
    )
    p.add_argument("--dry-run", action="store_true", default=True,
                   help="Preview only, no changes (default)")
    p.add_argument("--force", action="store_true",
                   help="Actually delete (REQUIRED to make changes)")
    p.add_argument("--max-score", type=float, default=0.5,
                   help="Only delete alphas with score <= this (default: 0.5)")
    p.add_argument("--days", type=int, default=0,
                   help="Only delete alphas older than N days (0 = any age)")
    p.add_argument("--stats", action="store_true",
                   help="Show database statistics")
    return p.parse_args()


def cmd_stats(db):
    """Show database statistics."""
    stats = db.get_stats()
    unsubmitted = db.get_unsubmitted(limit=1000)
    submitted = db.get_submitted(limit=1000)

    print(f"\n  {'Database Statistics':-^50}")
    print(f"  Total active alphas:    {stats.get('total_alphas', 0)}")
    print(f"  Total backtests:        {stats.get('total_backtests', 0)}")
    print(f"  Unsubmitted:            {len(unsubmitted)}")
    print(f"  Submitted:              {len(submitted)}")

    if stats.get("top_sharpe_name"):
        print(f"  Best Sharpe:            {stats['top_sharpe_name']} ({stats['top_sharpe']:.2f})")

    by_cat = stats.get("by_category", {})
    if by_cat:
        print(f"\n  By category:")
        for cat, cnt in sorted(by_cat.items(), key=lambda x: -x[1]):
            print(f"    {cat:<20} {cnt}")

    # Score distribution of unsubmitted
    scores = []
    for a in unsubmitted:
        s = a.get("score")
        if s is not None:
            scores.append(s)

    if scores:
        print(f"\n  Unsubmitted score distribution:")
        buckets = {"< 0.3": 0, "0.3-0.5": 0, "0.5-1.0": 0, "1.0-1.5": 0, "> 1.5": 0}
        for s in scores:
            if s < 0.3: buckets["< 0.3"] += 1
            elif s < 0.5: buckets["0.3-0.5"] += 1
            elif s < 1.0: buckets["0.5-1.0"] += 1
            elif s < 1.5: buckets["1.0-1.5"] += 1
            else: buckets["> 1.5"] += 1
        for label, cnt in buckets.items():
            bar = "█" * cnt
            print(f"    {label:<10} {cnt:>3}  {bar}")

    print()


def cmd_cleanup(db, args):
    """Find and (optionally) delete low-score unsubmitted alphas."""
    candidates = db.get_low_score_unsubmitted(
        max_score=args.max_score,
        older_than_days=args.days,
    )

    if not candidates:
        # Show why: what score range do existing unsubmitted alphas have?
        unsubmitted = db.get_unsubmitted(min_score=0, limit=100)
        if unsubmitted:
            scores = [a.get("score") or 0 for a in unsubmitted]
            lo, hi = min(scores), max(scores)
            print(f"\n  No alphas found with score <= {args.max_score} (unsubmitted).")
            print(f"  Current unsubmitted score range: {lo:.2f} ~ {hi:.2f}")
            print(f"  Try --max-score {max(lo, 0.3):.1f} to catch the lowest-scored alpha.\n")
        else:
            print(f"\n  No unsubmitted alphas in database. Nothing to clean.\n")
        return 0

    # Show what would be deleted
    print(f"\n  {'ID':<4} {'Name':<38} {'Score':>7} {'Sharpe':>8} {'Category':<18} {'Created':>12}")
    print(f"  {'-'*4} {'-'*38} {'-'*7} {'-'*8} {'-'*18} {'-'*12}")

    for a in candidates:
        score = a.get("score") or 0
        sharpe = a.get("sharpe") or 0
        created = (a.get("created_at") or "")[:10]
        print(
            f"  {a['id']:<4} {a['name']:<38} {score:>7.2f} {sharpe:>8.2f} "
            f"{a['category']:<18} {created:>12}"
        )

    print(f"\n  {'='*50}")
    print(f"  Candidates for cleanup: {len(candidates)}")
    print(f"  Conditions: score <= {args.max_score}, unsubmitted")
    if args.days > 0:
        print(f"              older than {args.days} days")

    if args.force:
        print(f"\n  ⚠️  DELETING {len(candidates)} alphas from database...")

        deleted = 0
        failed = 0
        for a in candidates:
            if db.delete_alpha_cascade(a["id"]):
                logger.info(f"  Deleted: {a['name']} (ID={a['id']}, Score={a.get('score', 0):.2f})")
                deleted += 1
            else:
                logger.error(f"  FAILED: {a['name']} (ID={a['id']})")
                failed += 1

        print(f"\n  Done. Deleted: {deleted}, Failed: {failed}\n")
    else:
        print(f"\n  💡 This is a DRY RUN. No changes made.")
        print(f"  Run with --force to actually delete these {len(candidates)} entries.\n")

    return 0


def main():
    args = parse_args()
    from storage.database import Database

    db = Database()

    try:
        if args.stats:
            cmd_stats(db)
            return 0

        if args.force:
            print(f"\n  ⚠️  此操作将不可逆地删除数据库记录！")
            print(f"  Conditions: score <= {args.max_score}, unsubmitted, active")
            if args.days > 0:
                print(f"              older than {args.days} days")

            # Show preview first
            candidates = db.get_low_score_unsubmitted(
                max_score=args.max_score,
                older_than_days=args.days,
            )
            if candidates:
                print(f"  Will delete: {len(candidates)} alphas")
            else:
                unsubmitted = db.get_unsubmitted(min_score=0, limit=100)
                if unsubmitted:
                    scores = [a.get("score") or 0 for a in unsubmitted]
                    lo, hi = min(scores), max(scores)
                    print(f"  No alphas match. Unsubmitted score range: {lo:.2f} ~ {hi:.2f}")
                    print(f"  Try --max-score {max(lo, 0.3):.1f} if you want to clean the lowest.\n")
                else:
                    print(f"  No unsubmitted alphas in database.\n")
                return 0

            # Require interactive confirmation
            try:
                resp = input(f"\n  Type 'yes' to confirm deletion of {len(candidates)} alphas: ")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.\n")
                return 1

            if resp.strip().lower() != "yes":
                print("  Cancelled.\n")
                return 0

        return cmd_cleanup(db, args)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
