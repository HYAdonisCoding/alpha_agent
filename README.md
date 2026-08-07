<div align="center">

# Alpha Agent

**AI-Powered Quantitative Research Platform for WorldQuant BRAIN Style Alpha Discovery**
**基于 AI 的量化研究平台 · WorldQuant BRAIN 风格 Alpha 发现**

</div>

---

## Table of Contents | 目录

| EN | 中文 |
|---|---|
| [Overview](#overview--项目概述) | [项目概述](#overview--项目概述) |
| [Architecture](#architecture--架构) | [架构](#architecture--架构) |
| [Pipeline](#pipeline--研究流程) | [研究流程](#pipeline--研究流程) |
| [Quick Start](#quick-start--快速开始) | [快速开始](#quick-start--快速开始) |
| [How to Use](#how-to-use--使用指南) | [使用指南](#how-to-use--使用指南) |
| [Configuration](#configuration--配置说明) | [配置说明](#configuration--配置说明) |
| [Core Modules](#core-modules--核心模块) | [核心模块](#core-modules--核心模块) |
| [Scoring](#scoring-system--评分系统) | [评分系统](#scoring-system--评分系统) |
| [Data Sources](#data-sources--数据源) | [数据源](#data-sources--数据源) |
| [Roadmap](#development-roadmap--开发路线) | [开发路线](#development-roadmap--开发路线) |

---

## Overview | 项目概述

**EN**:
Alpha Agent is a personal quantitative research platform that combines AI hypothesis generation, systematic backtesting, and automated quality review to discover and validate alpha factors. The core philosophy:

> AI proposes hypotheses → Python validates → Database accumulates experience → Human reviews and submits

**中文**:
Alpha Agent 是一个个人量化研究平台，结合 AI 假设生成、系统性回测和自动化质量审核，发现并验证 Alpha 因子。核心理念：

> AI 负责提出假设 → Python 负责验证 → 数据库沉淀经验 → 人工审核提交

---

## Architecture | 架构

```
alpha_agent/
├── data/              # Data layer — market data loading & processing
│                     # 数据层 — 行情数据加载与处理
├── alpha/             # Alpha core — generator, operators, templates, optimizer
│                     # Alpha 核心 — 生成器、算子库、模板、优化器
├── backtest/          # Backtest system — engine, metrics, risk validator
│                     # 回测系统 — 引擎、指标、风控
├── brain/             # WorldQuant BRAIN — client, simulator, submitter
│                     # BRAIN 接口 — 客户端、模拟器、提交器
├── ai/                # AI Agent — researcher, reviewer, memory
│                     # AI 代理 — 研究员、审核员、记忆库
├── storage/           # Storage — SQLite database & models
│                     # 存储 — SQLite 数据库与模型
├── report/            # Reports — daily reports & charts
│                     # 报告 — 日报与图表
├── config/            # Configuration — YAML settings
│                     # 配置 — YAML 设置文件
├── scripts/           # Orchestration — daily run, weekly review
│                     # 脚本 — 每日运行、周度复盘
└── tests/             # Test suite
                      # 测试套件
```

### Module Dependency Flow | 模块依赖流

```
                    ┌──────────┐
                    │  data/   │  Market data loading
                    └────┬─────┘  行情数据加载
                         │
                    ┌────▼─────┐
                    │  ai/     │  Market analysis + alpha generation
                    │ researcher│  市场分析 + Alpha 生成
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  alpha/  │  Template instantiation + operators
                    │ generator │  模板实例化 + 算子
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ backtest/│  Backtest + scoring + risk check
                    │  engine  │  回测 + 评分 + 风控
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼───┐ ┌───▼────┐ ┌──▼──────┐
         │  ai/   │ │  ai/   │ │ brain/  │
         │reviewer│ │memory  │ │simulator│
         │ 审核   │ │ 记忆库  │ │ 模拟器   │
         └────┬───┘ └───┬────┘ └─────────┘
              │         │
         ┌────▼─────────▼────┐
         │   storage/        │  SQLite persistence
         │   database        │  SQLite 持久化
         └────────┬──────────┘
                  │
             ┌────▼─────┐
             │ report/  │  Daily report + charts
             │  report  │  日报 + 图表
             └──────────┘
```

---

## Pipeline | 研究流程

```
06:00  Data Update      数据更新
  │       │                │
  ▼       ▼                ▼
Market Analysis    AI Generation    回测 Backtest
  市场环境分析       AI 生成 Alpha
  │
  ▼
Score & Review     评分与审核
  │
  ▼
Save Results       保存结果
  │
  ▼
Daily Report       生成日报
```

**EN**: Every morning, the platform loads market data, analyzes the current regime, generates alpha candidates from templates, backtests them, scores and reviews results, persists everything to SQLite, and generates a daily research report.

**中文**: 每天早上，平台加载行情数据、分析当前市场状态、从模板生成 Alpha 候选因子、回测、评分审核、持久化到 SQLite、生成日报。

---

## Quick Start | 快速开始

### 1. Install Dependencies | 安装依赖

```bash
# Clone the repo | 克隆仓库
git clone https://github.com/yourusername/alpha_agent.git
cd alpha_agent

# Create virtual environment | 创建虚拟环境
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

# Install dependencies | 安装依赖
pip install -r requirements.txt
```

### 2. Run the Daily Pipeline | 运行每日流程

```bash
# Default: 10 candidates, US market, template mode
# 默认：10 个候选因子，美股，模板模式
python scripts/daily_run.py

# Custom options | 自定义参数
python scripts/daily_run.py --n 20 --market us --mode template

# Dry run (no database save) | 试运行（不保存到数据库）
python scripts/daily_run.py --dry-run

# China A-share market | A 股市场
python scripts/daily_run.py --market cn --n 15
```

### 3. Weekly Review | 周度复盘

```bash
# Review last week | 复盘上周
python scripts/weekly_review.py

# Review last 4 weeks | 复盘近 4 周
python scripts/weekly_review.py --weeks 4
```

### 4. Run Tests | 运行测试

```bash
python tests/test_pipeline.py
```

---

## How to Use | 使用指南

### Command-Line Arguments | 命令行参数

#### `daily_run.py` — Daily Research Pipeline | 每日研究流程

| Flag | Default | Description EN | 说明中文 |
|------|---------|---------------|---------|
| `--n` | `10` | Number of alpha candidates to generate | 生成的 Alpha 候选数量 |
| `--market` | `us` | Market universe: `us` or `cn` | 市场范围：美股或 A 股 |
| `--mode` | `template` | Generation mode: `template` or `ai` | 生成模式：模板或 AI |
| `--dry-run` | `False` | Run without saving to database | 试运行，不写入数据库 |
| `--output-dir` | `report/output` | Report output directory | 报告输出目录 |

#### `weekly_review.py` — Weekly Review | 周度复盘

| Flag | Default | Description EN | 说明中文 |
|------|---------|---------------|---------|
| `--weeks` | `1` | Number of weeks to review | 复盘的周数 |

### Full Workflow | 完整工作流

**EN**:

```
Every Day                     When You Have Good Candidates         After BRAIN Results
   │                                    │                              │
   ▼                                    ▼                              ▼
daily_run.py                    submit_alpha.py                feedback_alpha.py
   │                                    │                              │
   ├─ Generate alphas            ├─ --list (review)            ├─ --list-pending
   ├─ Backtest                   ├─ --id <N> --brain-id X      ├─ --id <N> --sharpe ...
   ├─ Score & review             └─ --history (track)          ├─ --history (view)
   ├─ Save to DB (score ≥ 0.3)                                 ├─ --stats (learn)
   └─ Generate daily report                                     └─ → Feeds back to generator
                                                                     (next run = smarter)

Maintenance: cleanup_db.py --max-score 0.3 --force (remove garbage)
```

**中文**:

```
每天运行                      有好的候选时                         BRAIN 出结果后
   │                              │                                │
   ▼                              ▼                                ▼
daily_run.py              submit_alpha.py                  feedback_alpha.py
   │                              │                                │
   ├─ 生成 Alpha            ├─ --list (查看)               ├─ --list-pending (待反馈)
   ├─ 回测                   ├─ --id <N> --brain-id X      ├─ --id <N> --sharpe ...
   ├─ 评分审核               └─ --history (追踪)            ├─ --history (历史)
   ├─ 入库 (score ≥ 0.3)                                     ├─ --stats (学习统计)
   └─ 生成日报                                               └─ → 反哺生成器
                                                                  (下次运行更智能)

维护: cleanup_db.py --max-score 0.3 --force (清理低分数据)
```

### 🚀 BRAIN Submission Workflow | BRAIN 提交流程

**EN**: The platform never auto-submits. You review, you decide. Here's the end-to-end flow:

**中文**: 平台从不自动提交。你审核，你决策。完整流程如下：

```bash
# 1. Daily run — generate and backtest alphas | 每日运行 — 生成+回测 Alpha
python scripts/daily_run.py --n 30

# 2. Check what's worth submitting | 查看哪些值得提交
python scripts/submit_alpha.py --list
# Output shows: ID, name, score, sharpe, expression, and BRAIN-ready properties
# 输出: ID、名称、评分、夏普、表达式、BRAIN 属性

# 3. Copy expression → BRAIN Alpha Creator → paste & submit
#    复制表达式 → BRAIN Alpha Creator → 粘贴提交
#    https://platform.worldquantbrain.com/

# 4. Wait 1-2 days for BRAIN simulation results, then ONE command:
#    等 1-2 天 BRAIN 出模拟结果后，一条命令搞定：
#    → 自动标记"已提交" + 记录 BRAIN 反馈 + 反哺学习

python scripts/feedback_alpha.py --id 3 -s -0.39 -f -0.18 -t 0.1379 -r -0.0283 -d 0.218 -m -0.000411

# 5. System learns → next run generates better alphas
#    系统自动学习 → 下次生成更优 Alpha

# 6. Periodic cleanup | 定期清理
python scripts/cleanup_db.py --stats
```

### Command-Line Tool Reference | 命令行工具速查

#### `daily_run.py` — Daily Research Pipeline | 每日研究流程

| Flag | Default | Description EN | 说明中文 |
|------|---------|---------------|---------|
| `--n` | `10` | Number of alpha candidates to generate | 生成的 Alpha 候选数量 |
| `--market` | `us` | Market universe: `us` or `cn` | 市场范围：美股或 A 股 |
| `--mode` | `template` | Generation mode: `template` or `ai` | 生成模式：模板或 AI |
| `--dry-run` | `False` | Run without saving to database | 试运行，不写入数据库 |
| `--output-dir` | `report/output` | Report output directory | 报告输出���录 |

#### `submit_alpha.py` — BRAIN Submission Tracker | BRAIN 提交追踪

| Flag | Description EN | 说明中文 |
|------|---------------|---------|
| `--list` | List unsubmitted alphas with BRAIN-ready properties | 列出未提交 Alpha（含 BRAIN 属性） |
| `--history` | Show submission history | 显示提交历史 |
| `--id <N>` | Mark alpha by database ID as submitted | 按数据库 ID 标注已提交 |
| `--name <X>` | Mark alpha by name as submitted | 按名称标注已提交 |
| `--brain-id <X>` | BRAIN alpha ID assigned after submission | ���交后 BRAIN 分配的 Alpha ID |
| `--notes <X>` | Submission notes (e.g. simulation results) | 提交备注 |
| `--status <X>` | Status: submitted / accepted / rejected | 状态：已提交/已通过/已拒绝 |

```bash
# 查看可提交的 alpha
python scripts/submit_alpha.py --list

# 查看提交历史
python scripts/submit_alpha.py --history
```

> 💡 BRAIN 出结果后，直接用 `feedback_alpha.py` — 一条命令自动标记提交+记录反馈+反哺学习。

#### `feedback_alpha.py` — BRAIN Performance Feedback | BRAIN 表现反馈

**EN**: Close the learning loop by inputting BRAIN simulation results back into the system so it can optimize future generation.

**中文**: 将 BRAIN 模拟结果喂回系统，形成学习闭环，优化未来的 Alpha 生成。

| Flag | Description EN | 说明中文 |
|------|---------------|---------|
| `--list-pending` | List submitted alphas awaiting BRAIN feedback | 列出等待反馈的已提交 Alpha |
| `--history` | Show BRAIN feedback history | 查看反馈历史 |
| `--stats` | Show BRAIN feedback statistics (for learning) | 查看学习统计（模板/品类通过率） |
| `--id <N>` | Alpha database ID to record feedback for | 要记录反馈的 Alpha ID |
| `--name <X>` | Alpha name to record feedback for | 要记录反馈的 Alpha 名称 |
| `--sharpe` / `-s <F>` | BRAIN Sharpe ratio (e.g. -0.39) | BRAIN 夏普比率（如 -0.39） |
| `--fitness` / `-f <F>` | BRAIN fitness score (e.g. -0.18) | BRAIN 适应度（如 -0.18） |
| `--turnover` / `-t <F>` | BRAIN turnover as decimal (e.g. 0.1325 = 13.25%) | BRAIN 换手率（小数，如 0.1325） |
| `--returns` / `-r <F>` | BRAIN returns as decimal (e.g. -0.0108 = -1.08%) | BRAIN 收益率（小数，如 -0.0108） |
| `--drawdown` / `-d <F>` | BRAIN drawdown as decimal (e.g. 0.1519 = 15.19%) | BRAIN 最大回撤（小数，如 0.1519） |
| `--margin` / `-m <F>` | BRAIN margin (e.g. -1.62) | BRAIN 保证金（如 -1.62） |
| `--status <X>` | Acceptance status: auto / accepted / rejected | 状态：自动检测/已通过/已拒绝 |
| `--notes <X>` | Additional notes | 备注 |

> ⚠️ Turnover/Returns/Drawdown 必须用小数（如 13.25% → 0.1325），不是百分数。

```bash
# 查看等待反馈的 alpha
python scripts/feedback_alpha.py --list-pending

# 提交+反馈 一条命令 (自动创建提交记录 + 记录 BRAIN 指标 + 反哺学习)
python scripts/feedback_alpha.py --id 3 \
    -s -0.39 -f -0.18 -t 0.1379 -r -0.0283 -d 0.218 -m -0.000411

# 按名称反馈
python scripts/feedback_alpha.py --name volume_price_trend_n20 \
    -s -0.10 -f -0.03 -t 0.1325 -r -0.0108 -d 0.1519 -m -1.62

# 查看学习统计
python scripts/feedback_alpha.py --stats
```

**How feedback improves generation | 反馈如何改善生成**:
- Templates that produced BRAIN-**accepted** alphas → boosted weight (more likely to be selected)
- Templates that produced BRAIN-**rejected** alphas → penalized weight (less likely to be selected)
- The influence is multiplicative with market regime weights
- `python scripts/feedback_alpha.py --stats` shows the learning summary

#### `cleanup_db.py` — Database Cleanup | 数据库清理

| Flag | Default | Description EN | 说明中文 |
|------|---------|---------------|---------|
| `--stats` | — | Show database health overview | 显示数据库健康概览 |
| `--dry-run` | `True` | Preview only, no changes (default) | 仅预览，不做修改（默认） |
| `--force` | `False` | Actually delete matching records | 真正删除匹配记录 |
| `--max-score` | `0.5` | Only delete alphas with score ≤ this | 仅删除评分 ≤ 此值的 Alpha |
| `--days` | `0` | Only delete alphas older than N days | 仅删除 N 天前的 Alpha |

> ⚠️ **Safety rules**: `cleanup_db.py` never deletes submitted/accepted alphas. Always `--dry-run` first.
> ⚠️ **安全规则**: `cleanup_db.py` 绝不删除已提交/已接受的 Alpha。请先 `--dry-run` 预览。

#### `weekly_review.py` — Weekly Review | 周度复盘

| Flag | Default | Description EN | 说明中文 |
|------|---------|---------------|---------|
| `--weeks` | `1` | Number of weeks to review | 复盘的周数 |

### Auto-Generated BRAIN Properties | 自动生成 BRAIN 属性

**EN**: When a quality alpha (score ≥ 0.3) enters the database, the platform auto-generates BRAIN submission properties that you can copy directly into the Alpha Creator:

**中文**: 高质量 Alpha（score ≥ 0.3）入库时，平台自动生成 BRAIN 提交属性，可直接复制到 Alpha Creator：

| Property | Generated From | Example |
|----------|---------------|---------|
| `brain_name` | snake_case → Title Case + params | `Volume Price Trend 40D` |
| `tags` | Category + operators + period | `volume, trend, mid-frequency, cross-sectional` |
| `color` | Category-based palette | `#109618` (green for volume) |
| `description` | Template desc + metrics | `Price trend weighted by volume. Sharpe=1.96.` |

View with: `python scripts/submit_alpha.py --list`

### Setting Up Cron (macOS/Linux) | 定时任务设置

```bash
# Edit crontab | 编辑定时任务
crontab -e

# Run daily at 06:00 | 每天 06:00 自动运行
0 6 * * * cd /path/to/alpha_agent && /path/to/venv/bin/python scripts/daily_run.py >> logs/cron.log 2>&1

# Weekly review every Monday 18:00 | 每周一 18:00 周度复盘
0 18 * * 1 cd /path/to/alpha_agent && /path/to/venv/bin/python scripts/weekly_review.py >> logs/cron_weekly.log 2>&1
```

### Using Individual Modules | 单独使用各模块

```python
from alpha.generator import AlphaGenerator
from backtest.engine import BacktestEngine
from backtest.metrics import AlphaMetrics
from ai.reviewer import AIReviewer

# 1. Generate alpha candidates | 生成 Alpha 候选
generator = AlphaGenerator(mode="template")
candidates = generator.generate(n=10, market_state={"regime": "bullish"})

# 2. Backtest each candidate | 回测每个候选
engine = BacktestEngine()
metrics = AlphaMetrics()
reviewer = AIReviewer()

for c in candidates:
    result = engine.run(
        expression=c.expression,
        data={"close": price_df},
        alpha_name=c.name,
    )
    score = metrics.score(result)
    review = reviewer.review(result, score)
    print(f"{c.name}: Score={score.total:.2f} Decision={review.decision.value}")
```

---

## Configuration | 配置说明

All settings live in `config/settings.yaml`:

| Section EN | 说明中文 | Key Fields |
|-----------|---------|------------|
| `data` | 数据 | `sources`, `universe` (stock tickers), `date_range` |
| `backtest` | 回测 | `lookback_days` (252), `forward_days` (20), `transaction_cost` (0.001) |
| `scoring` | 评分 | `weights` (sharpe 0.40, fitness 0.30, turnover 0.15, drawdown 0.10, ic 0.05) |
| `templates` | 模板 | `parameter_ranges` — n: [5,10,20,40,60,120,252], k: [2,3,5,10] |
| `ai` | AI | `model`, `temperature`, `max_alphas_per_run` |
| `brain` | BRAIN | `enabled` (false by default), `api_base`, `max_submissions_per_day` |
| `report` | 报告 | `output_dir`, `formats` (markdown, html) |
| `schedule` | 调度 | `daily_run_time` (06:00), `timezone` (Asia/Shanghai) |

---

## Core Modules | 核心模块

### Alpha Generation (`alpha/`) | Alpha 生成

**EN**: Template-based alpha generation with 20+ pre-built templates across 6 categories:

**中文**: 基于模板的 Alpha 生成，涵盖 6 大类 20+ 个预置模板：

| Category EN | 类别中文 | Example Expression |
|------------|---------|-------------------|
| Momentum | 动量 | `rank(ts_delta(close, {n}))` |
| Mean Reversion | 均值回归 | `-rank(ts_zscore(close, {n}))` |
| Volume | 成交量 | `rank(volume / ts_mean(volume, {n}))` |
| Volatility | 波动率 | `rank(ts_std(close, {n}))` |
| Cross-Sectional | 截面 | `rank(close) - rank(ts_mean(close, {n}))` |
| Combination | 组合 | `rank(ts_delta(close, {n})) * rank(volume)` |

### Factor Operators (`alpha/operators.py`) | 因子算子库

WorldQuant BRAIN-compatible operators:

```
ts_delta, ts_sum, ts_mean, ts_std, ts_rank, ts_zscore,
ts_min, ts_max, ts_corr, rank, scale, signed_power, decay_linear
```

### Backtest Engine (`backtest/`) | 回测引擎

| Feature EN | 功能中文 |
|-----------|---------|
| Long-short portfolio simulation | 多空组合模拟 |
| Top/bottom quantile construction | 分位数分组构建 |
| Sharpe ratio | 夏普比率 |
| Fitness (WorldQuant-style) | Fitness（WorldQuant 风格） |
| Turnover | 换手率 |
| Max drawdown | 最大回撤 |
| IC analysis with IR | IC 分析与信息比率 |
| Risk validation with thresholds | 风控阈值验证 |

### AI Agent (`ai/`) | AI 代理

| Module EN | 模块中文 | Responsibility |
|-----------|---------|---------------|
| `researcher.py` | AI 研究员 | Market regime analysis + alpha hypothesis generation / 市场状态分析 + Alpha 假设生成 |
| `reviewer.py` | AI 审核员 | Simulates quant PM review with structured feedback / 模拟量化主管审核，输出结构化反馈 |
| `memory.py` | 记忆库 | Tracks successful/failed alpha patterns / 记录成功/失败的 Alpha 模式 |

---

## Scoring System | 评分系统

```
Score = Sharpe × 0.40 + Fitness × 0.30
        − Turnover × 0.15 − Drawdown × 0.10 + IC × 0.05
```

| Score | Grade EN | 等级中文 | Action EN | 动作 |
|-------|----------|---------|-----------|------|
| ≥ 1.5 | RECOMMEND_SUBMIT | 推荐提交 | Ready for BRAIN | 可提交 BRAIN |
| 1.0 – 1.5 | NEEDS_OPTIMIZATION | 需优化 | Tune parameters | 调参优化 |
| 0.5 – 1.0 | ARCHIVE | 归档 | Keep for reference | 保留参考 |
| < 0.5 | FAILURE | 失败 | Discard | 丢弃 |

---

## Data Sources | 数据源

| Source EN | 数据源 | Markets | Status |
|-----------|--------|---------|--------|
| Yahoo Finance | Yahoo Finance | US & global | ✅ Built-in |
| AKShare | AKShare | China A-share | ✅ Built-in |
| WorldQuant BRAIN | WorldQuant BRAIN | WQ datasets | 🔜 Planned |
| Alpha Vantage | Alpha Vantage | Global | 🔜 Planned |

---

## Development Roadmap | 开发路线

| Phase EN | 阶段中文 | Status | Deliverables |
|----------|---------|--------|-------------|
| Week 1 | 第 1 周 | ✅ Done | Core architecture, templates, backtest, reports / 核心架构、模板、回测、报告 |
| Week 2-3 | 第 2-3 周 | 🔜 Next | Real data integration, pandas/numpy optimization / 真实数据接入、pandas/numpy 优化 |
| Week 4 | 第 4 周 | 🔜 Planned | LLM-powered alpha generation, SQLite memory / LLM 生成 Alpha、SQLite 记忆库 |
| Month 2 | 第 2 个月 | 🔜 Planned | WorldQuant BRAIN workflow, alpha lifecycle / BRAIN 工作流、Alpha 生命周期管理 |

---

## Project Structure | 项目文件

```
alpha_agent/
├── data/
│   ├── __init__.py
│   ├── loader.py          # MarketDataLoader
│   └── processor.py        # Data cleaning & normalization
├── alpha/
│   ├── __init__.py
│   ├── operators.py        # 13 factor operators
│   ├── templates.py        # 20+ alpha templates (6 categories)
│   ├── generator.py        # AlphaGenerator (template/ai modes)
│   └── optimizer.py        # Parameter grid search
├── backtest/
│   ├── __init__.py
│   ├── engine.py           # BacktestEngine
│   ├── metrics.py          # AlphaMetrics + scoring
│   └── validator.py        # RiskValidator
├── brain/
│   ├── __init__.py
│   ├── client.py           # BRAIN API client
│   ├── simulator.py        # Expression evaluator
│   ├── submitter.py        # Human-in-the-loop submitter
│   └── props_generator.py  # Auto-generate BRAIN submission properties
├── ai/
│   ├── __init__.py
│   ├── researcher.py       # AIResearcher
│   ├── reviewer.py         # AIReviewer
│   └── memory.py           # AlphaMemory (success/failure bank)
├── storage/
│   ├── __init__.py
│   ├── models.py           # Data models
│   └── database.py         # SQLite database wrapper
├── report/
│   ├── __init__.py
│   ├── daily_report.py     # Daily report generator
│   └── charts.py           # Matplotlib chart generation
├── config/
│   └── settings.yaml       # All configuration
├── scripts/
│   ├── daily_run.py        # Daily pipeline orchestration
│   ├── weekly_review.py    # Weekly summary & insights
│   ├── submit_alpha.py     # BRAIN submission tracker
│   ├── feedback_alpha.py   # BRAIN performance feedback loop
│   └── cleanup_db.py       # Database cleanup & maintenance
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py    # 7 integration tests
├── requirements.txt
└── README.md
```

---
## 整理 BRAIN 常见词：


|英文|含义|
|---|---|
|Alpha|预测模型|
|Factor|因子|
|Signal|信号|
|Backtest|回测|
|Simulation|模拟|
|Performance|表现|
|Sharpe Ratio|夏普比率|
|Fitness|综合评分|
|Turnover|换手率|
|Delay|交易延迟|
|Universe|股票池|
|Data Field|数据字段|
|Expression|公式|
|Dataset Category|数据大类|
|Dataset|数据集合|
|Data Field|具体可用数据|
|PV|价格成交量数据|
|Fundamental|财务数据|
|Close|收盘价|
|Volume|成交量|
|Returns|收益率|
|Liquidity|流动性|
|Universe|股票池|
|Momentum|趋势延续|
|Reversion|价格回归|
|250|一年交易日|
|ts_delta|变化量|
|ts_delay|历史数据|
|ts_sum|时间求和|
|returns>0|上涨判断|
|if_else|条件判断|
|Logical Operator|逻辑运算符|
|Condition|条件|
|if_else|条件选择|
|trade_when|条件交易|
|entry|进入条件|
|exit|退出条件|
|positive_days|上涨天数|
|adv20|20日平均成交量|
|Momentum|动量|
|Holding|持仓|
|Liquidate|清仓|
|NaN|无仓位|
|Alpha|预测股票未来走势的数学模型|
|Alpha Pool|Alpha数据库|
|Submission|提交|
|Fitness|综合评分|
|Sharpe|风险收益比|
|Turnover|换手率|
|Weight|股票权重|
|Robustness|稳定性|
|Sub-universe|子股票池|
|Correlation|相关性|
|Self-Correlation|与已有Alpha相似程度|
|Delay1|使用昨天以前的数据|
|Reversion|跌多反弹|
|Momentum|涨多继续涨|
|Alpha Pool|Alpha数据库|
|Submission|提交|
|Fitness|综合表现评分|
|Sharpe Ratio|风险收益比|
|Turnover|换手率|
|Weight|股票资金占比|
|Robustness|稳定性|
|Sub-universe|小股票池测试|
|Correlation|相关性|
|Delay1|使用昨天以前的数据|
|vwap/close|价格偏离|
|volume|资金确认|
|CLV|短期反转|
|operating_income/cap|价值|
|Option|期权|
|Derivative|衍生品|
|Call|看涨期权|
|Put|看跌期权|
|Premium|期权价格|
|Strike Price|执行价格|
|Expiration|到期时间|
|Volatility|价格波动程度|
|Historical Volatility|过去真实波动|
|Implied Volatility|市场预测未来波动|
|Long|做多|
|Short|做空|
|Alpha|预测未来收益的信号|
|Signal|交易依据|
|Expiry|到期周期|
|Option|期权|
|Call Option|看涨期权|
|Put Option|看跌期权|
|Implied Volatility (IV)|市场预测未来波动大小|
|IV Difference|两个IV的差值|
|Demand|市场需求|
|Leverage|杠杆|
|Directionality|上涨/下跌方向|
|Time Value|时间价值|
|Signal|交易信号|
|Alpha|预测未来收益的方法|
|Neutralization|去除某些因素影响|
|Group Neutralization|分组中性化|
|Factor|影响股票收益的因素|
|Alpha|预测超额收益信号|
|Sharpe Ratio|收益/风险比例|
|Return|收益|
|Margin|收益效率|
|Group|股票分类|
|Sector|板块|
|Industry|行业|
|Subindustry|细分行业|
|Bucket|分组工具|
|Densify|压缩分类编号|
|Market Cap(cap)|公司市值|
|IV|隐含波动率|
|Option Demand|期权需求|
|Alpha|可以赚钱的预测信号|
|Data Field|数据字段|
|scl12_buzz|股票网络讨论热度数据|
|Volume|成交量|
|NLP|自然语言处理，让电脑理解文字情绪|
|Leading Indicator|领先指标，提前反映未来变化|
|Lookback Days|回看多少天历史数据|
|Regression|回归分析，寻找变量之间关系|
|Linear Regression|线性回归，用直线描述关系|
|Independent Variable(X)|影响因素|
|Dependent Variable(Y)|被解释因素|
|Coefficient|系数，表示影响方向和强度|
|Residual/Error Term|实际值和预测值之间的差距|
|PnL Shape|收益曲线形状|
|News Alpha|利用新闻信息赚钱的策略|
|Sentiment|情绪|
|Vector Data|一天多个数据值的数据|
|Matrix Data|一天一个数据值的数据|
|vec_avg|计算Vector平均值|
|ts_mean|时间平均|
|ts_sum|时间累加|
|rank|横向排名|
|Condition|判断条件|
|if_else|如果A，否则B|
|Momentum|趋势策略，涨的继续买|
|Reversion|均值回归，涨多了卖|
|Long|买入|
|Short|卖出|
|Threshold|阈值，例如50%分界|
|Noise|随机波动|
|Sentiment|投资者情绪|
|News Data|新闻数据|
|Alpha|预测股票收益的模型|
|scl12_buzz|股票网络关注数量|
|volume|成交量|
|ts_regression|时间序列回归，寻找两个变量关系|
|nws12_afterhsz_sl|新闻后多空优势数据|
|Vector|一天多个数据值|
|vec_avg|把多个值平均成一个|
|Momentum|趋势策略，强者继续强|
|Reversion|反转策略，涨多跌回来|
|rank|排名|
|Condition|条件|
|Signal|交易信号|
|Noise|噪音|
|Alpha|预测股票未来收益的信号|
|Gold Level|BRAIN挑战等级|
|Challenge Point|提交Alpha获得的积分|
|Universe|股票池|
|Neutralization|去除某种风险影响|
|Sector|行业|
|Industry|细分行业|
|Group Neutralize|组内标准化|
|Regression Neutralize|回归方式去风险|
|Position Distribution|仓位分布|
|rank|把股票排序|
|signed_power|改变信号强弱|
|log|压缩极端值|
|Trade_when|满足条件才交易|
|Drawdown|最大亏损幅度|
|Diversification|分散风险|
|In Sample(IS)|训练数据|
|Out Sample(OS)|测试数据|
|Overfit|过拟合|





### 提示词

你现在是我的WorldQuant BRAIN量化导师。

请把下面英文教程：
1. 翻译成中文
2. 用小学能理解的方式解释
3. 解释所有量化术语
4. 给出Python对应实现
5. 告诉我这个知识如何应用到alpha_agent项目

内容如下：

你现在是我的WorldQuant BRAIN量化导师。

请把下面英文教程：
1. 翻译成中文
2. 用小学能理解的方式解释，尽可能简短的解释，不要太长了
3. 解释所有量化术语
4. 告诉我如何应用这个知识到设计表达式

内容如下：




---

|术语|解释|
|---|---|
|Market Neutralization|去除市场风险|
|Market Risk|整体市场涨跌影响|
|Long|买入|
|Short|卖出|
|Long Only|只买|
|Long Short|买强卖弱|
|Center|减平均值|
|Normalize|标准化|
|Weight|资金比例|
|Position|仓位|
|Decay|仓位平滑|
|Linear Decay|线性衰减|
|Equity|股票|
|Bond|债券|
|Future|期货|
|Option|期权|
|Fast Expression|BRAIN公式语言|
|Region|市场地区|
|Universe|股票池|
|Liquidity|流动性|
|Delay|数据延迟|
|Delay1|昨天数据|
|Delay0|接近实时数据|
|Neutralization|风险中性化|
|Industry Neutral|行业中性|
|Decay|仓位平滑|
|Truncation|限制单股票权重|
|NaN|缺失数据|
|Test Period|样本外测试|
|Technical Analysis|技术分析|
|Indicator|指标|
|Factor|因子|
|Alpha|预测模型|
|CLV|收盘价在当天区间的位置|
|High|最高价|
|Low|最低价|
|Close|收盘价|
|Volume|成交量|
|Momentum|动量|
|Reversion|反转|
|Sharpe Ratio|风险调整收益|













## License

MIT
