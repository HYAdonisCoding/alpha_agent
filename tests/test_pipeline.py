"""
Integration test: Alpha pipeline end-to-end with synthetic data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np


def generate_synthetic_data(
    n_dates: int = 500, n_symbols: int = 20, seed: int = 42
) -> dict:
    """Generate synthetic market data for testing."""
    np.random.seed(seed)
    dates = pd.date_range("2022-01-01", periods=n_dates, freq="B")

    data = {}
    price_data = {}

    for i in range(n_symbols):
        symbol = f"STOCK_{i:02d}"

        # Random walk with drift
        returns = np.random.randn(n_dates) * 0.02
        # Add some momentum
        momentum = np.convolve(returns, np.ones(5) / 5, mode="same")
        returns = 0.7 * returns + 0.3 * momentum
        returns[0] = 0

        prices = 100 * np.exp(np.cumsum(returns * 0.01))
        volumes = np.random.lognormal(10, 1, n_dates) * 1e6

        price_data[(symbol, "close")] = prices
        price_data[(symbol, "volume")] = volumes

    prices = pd.DataFrame(price_data, index=dates)
    prices.columns = pd.MultiIndex.from_tuples(prices.columns, names=["symbol", "field"])

    close = prices.xs("close", level="field", axis=1)
    volume = prices.xs("volume", level="field", axis=1)

    return {
        "prices": prices,
        "close": close,
        "volume": volume,
    }


def test_alpha_generation():
    """Test alpha template generation."""
    from alpha.templates import AlphaTemplates
    from alpha.generator import AlphaGenerator

    templates = AlphaTemplates()
    all_t = templates.get_all_templates()
    assert len(all_t) > 5, f"Expected >5 templates, got {len(all_t)}"

    for t in all_t:
        combos = templates.get_parameter_combinations(t)
        if combos:
            params = combos[0]
            expr = templates.instantiate(t, params)
            assert expr, f"Empty expression for {t.name}"
            assert "{" not in expr, f"Unreplaced parameter in {expr}"

    gen = AlphaGenerator()
    candidates = gen.generate(n=5, market_state={"regime": "bullish"})
    assert len(candidates) == 5
    assert all(c.expression for c in candidates)

    print(f"  Generated {len(candidates)} candidates from {len(all_t)} templates")
    return True


def test_operators():
    """Test factor operator library."""
    from alpha.operators import FactorOperators

    data = generate_synthetic_data(n_dates=200, n_symbols=10)
    close = data["close"]
    volume = data["volume"]

    ops = FactorOperators()

    # Test each operator
    delta = ops.ts_delta(close, 20)
    assert delta.shape == close.shape

    rank = ops.rank(close)
    assert rank.shape == close.shape
    assert (rank.max().max() <= 1.0)
    assert (rank.min().min() >= 0.0)

    zscore = ops.ts_zscore(close, 40)
    assert zscore.shape == close.shape

    decay = ops.decay_linear(close, 20)
    assert decay.shape == close.shape

    mean = ops.ts_mean(close, 20)
    assert mean.shape == close.shape

    print("  All operators tested successfully")
    return True


def test_backtest_engine():
    """Test backtest engine with synthetic data."""
    from backtest.engine import BacktestEngine
    from backtest.metrics import AlphaMetrics

    data = generate_synthetic_data(n_dates=500, n_symbols=15)

    engine = BacktestEngine(
        lookback_days=252,
        forward_days=20,
    )

    # Test with a known-good expression
    result = engine.run(
        expression="rank(ts_delta(close, 20))",
        data={"close": data["close"]},
        alpha_name="test_momentum_20",
    )

    assert result.n_days > 0
    assert result.n_assets > 0

    metrics = AlphaMetrics()
    score = metrics.score(result)

    print(f"  Alpha: {result.alpha_name}")
    print(f"  Sharpe: {result.sharpe:.3f}")
    print(f"  Fitness: {result.fitness:.3f}")
    print(f"  Score: {score.total:.3f} ({score.grade.value})")
    print(f"  IC Mean: {result.ic_mean:.4f}, IC IR: {result.ic_ir:.3f}")

    return True


def test_ai_modules():
    """Test AI researcher and reviewer."""
    from ai.researcher import AIResearcher
    from ai.reviewer import AIReviewer
    from backtest.engine import BacktestEngine
    from backtest.metrics import AlphaMetrics

    data = generate_synthetic_data(n_dates=300, n_symbols=10)

    # Test market analysis
    researcher = AIResearcher()
    market = researcher.analyze_market(data["prices"], data["volume"])
    assert market.regime in ("bullish", "bearish", "neutral", "volatile")

    # Test research
    ideas = researcher.research(market_context=market, n_ideas=3)
    assert len(ideas) > 0

    # Test reviewer
    engine = BacktestEngine()
    bt_result = engine.run(
        expression="rank(ts_delta(close, 20))",
        data={"close": data["close"]},
        alpha_name="test",
    )
    metrics = AlphaMetrics()
    score = metrics.score(bt_result)

    reviewer = AIReviewer()
    review = reviewer.review(bt_result, score)
    assert review.decision.value in ("APPROVED", "REVISE", "REJECT")

    print(f"  Market regime: {market.regime}")
    print(f"  Generated {len(ideas)} ideas")
    print(f"  Review decision: {review.decision.value}")
    print(f"  Review feedback: {review.feedback[:80]}...")

    return True


def test_memory():
    """Test alpha memory bank."""
    from ai.memory import AlphaMemory
    import tempfile, os

    tmpdir = tempfile.mkdtemp()
    success_file = os.path.join(tmpdir, "success.json")
    failure_file = os.path.join(tmpdir, "failure.json")

    try:
        memory = AlphaMemory(
            success_file=success_file,
            failure_file=failure_file,
        )

        memory.record_success(
            name="test_momentum",
            expression="rank(ts_delta(close, 20))",
            category="momentum",
            metrics={"sharpe": 1.5, "fitness": 1.2, "ic_ir": 0.5},
            lessons="20-day momentum works well in trending markets",
        )

        memory.record_failure(
            name="test_overfit",
            expression="rank(ts_delta(close, 2))",
            category="momentum",
            metrics={"sharpe": 0.1},
            reason="Too short lookback, overfit to noise",
        )

        results = memory.query_successes(min_sharpe=1.0)
        assert len(results) >= 1
        assert results[0]["name"] == "test_momentum"

        failures = memory.query_failures()
        assert len(failures) >= 1

        stats = memory.get_stats()
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 1

        print(f"  Memory stats: {stats}")
        print(f"  Top patterns: {memory.get_top_patterns()}")

    finally:
        import shutil
        shutil.rmtree(tmpdir)

    return True


def test_database():
    """Test database operations."""
    from storage.database import Database
    from backtest.engine import BacktestEngine
    import tempfile, os

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")

    try:
        db = Database(db_path)

        # Save alpha
        alpha_id = db.save_alpha(
            name="test_db_alpha",
            expression="rank(ts_delta(close, 20))",
            category="momentum",
        )
        assert alpha_id is not None

        # List alphas
        alphas = db.list_alphas()
        assert len(alphas) >= 1

        # Search
        results = db.search_alphas("momentum")
        assert len(results) >= 1

        # Stats
        stats = db.get_stats()
        assert stats["total_alphas"] >= 1

        print(f"  Saved alpha ID: {alpha_id}")
        print(f"  Total alphas: {stats['total_alphas']}")
        print(f"  By category: {stats['by_category']}")

    finally:
        import shutil
        shutil.rmtree(tmpdir)

    return True


def test_full_pipeline():
    """Test the complete pipeline end-to-end."""
    print("\n" + "=" * 60)
    print("FULL PIPELINE TEST")
    print("=" * 60)

    from alpha.generator import AlphaGenerator
    from alpha.optimizer import AlphaOptimizer
    from backtest.engine import BacktestEngine
    from backtest.metrics import AlphaMetrics
    from backtest.validator import RiskValidator
    from ai.reviewer import AIReviewer
    from ai.memory import AlphaMemory
    from brain.simulator import BrainSimulator
    from report.daily_report import DailyReport

    data = generate_synthetic_data(n_dates=500, n_symbols=15)
    eval_data = {"close": data["close"], "volume": data["volume"]}

    # 1. Generate
    generator = AlphaGenerator()
    candidates = generator.generate(n=5)

    # 2. Backtest
    engine = BacktestEngine()
    metrics = AlphaMetrics()
    validator = RiskValidator()
    reviewer = AIReviewer()
    simulator = BrainSimulator()

    results = []
    for c in candidates:
        bt = engine.run(c.expression, eval_data, c.name)
        score = metrics.score(bt)
        validation = validator.validate(bt)
        review = reviewer.review(bt, score)
        sim = simulator.evaluate(c.expression, eval_data, c.name)

        results.append({
            "name": c.name,
            "category": c.category,
            "expression": c.expression,
            "description": c.description,
            "score": score.total,
            "grade": score.grade.value,
            "sharpe": bt.sharpe,
            "review_decision": review.decision.value,
            "validation_passed": validation.passed,
            "sim_status": sim.get("status", "unknown"),
        })

    # 3. Report
    reporter = DailyReport(output_dir="report/output")
    market_state = {"regime": "neutral", "volatility": 0.20, "trend_strength": 0.5}

    report_data = []
    for r in results:
        report_data.append({
            "name": r["name"],
            "category": r["category"],
            "expression": r["expression"],
            "score": r["score"],
            "backtest": {
                "sharpe": r["sharpe"],
            },
            "review": {
                "decision": r["review_decision"],
            },
        })

    report = reporter.generate(market_state, report_data)

    # Print summary
    print(f"\nGenerated: {len(candidates)}")
    print(f"Backtested: {len(results)}")
    for r in results:
        status = "✅" if r["review_decision"] == "APPROVED" else (
            "🔄" if r["review_decision"] == "REVISE" else "❌"
        )
        print(
            f"  {status} {r['name']:30s} Score={r['score']:.2f} "
            f"Sharpe={r['sharpe']:.2f} Grade={r['grade']}"
        )

    print(f"\nReport generated with {len(report)} characters")
    return True


if __name__ == "__main__":
    print("Alpha Agent - Test Suite")
    print("=" * 60)

    tests = [
        ("Alpha Templates & Generation", test_alpha_generation),
        ("Factor Operators", test_operators),
        ("Backtest Engine", test_backtest_engine),
        ("AI Modules (Researcher + Reviewer)", test_ai_modules),
        ("Alpha Memory", test_memory),
        ("Database", test_database),
        ("Full Pipeline", test_full_pipeline),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n[TEST] {name}")
        print("-" * 40)
        try:
            test_fn()
            passed += 1
            print(f"  ✅ PASSED")
        except Exception as e:
            failed += 1
            print(f"  ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60)
