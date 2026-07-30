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
# Output shows: ID, name, score, sharpe, and BRAIN-ready name
# 输出: ID、名称、评分、夏普、BRAIN 就绪名称

# 3. Pick a candidate, get its full BRAIN properties | 选一个候选，获取完整 BRAIN 属性
python scripts/submit_alpha.py --list
# → Shows brain_name, tags, color, description for the best alpha
# → 显示最佳 Alpha 的 BRAIN 名称、标签、颜色、描述

# 4. Go to https://platform.worldquantbrain.com/ → Alpha Creator
#    Paste the expression and brain properties manually | 手动粘贴表达式和属性
#    打开 BRAIN → Alpha Creator → 粘贴表达式和属性

# 5. After successful submission, mark it locally | 提交成功后本地标注
python scripts/submit_alpha.py --id 5 --brain-id "BRAIN-abc123"

# 6. Wait for BRAIN simulation results (1-2 days), then input feedback
#    等待 BRAIN 模拟结果（1-2天），然后输入反馈
python scripts/feedback_alpha.py --list-pending   # See what needs feedback
python scripts/feedback_alpha.py --id 5 \\
    --sharpe 0.85 --fitness 0.40 --turnover 0.08 \\
    --returns 0.05 --drawdown 0.15 --margin 0.0002

# 7. System learns from feedback — next run generates better alphas
#    系统从反馈中学习 — 下次运行会生成更优的 Alpha

# 8. Periodically clean low-score unsubmitted alphas | 定期清理低分未提交数据
python scripts/cleanup_db.py --stats          # Check DB health | 查看数据库状态
python scripts/cleanup_db.py --max-score 0.3 --force  # Remove garbage | 清理垃圾
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
| `--sharpe <F>` | BRAIN Sharpe ratio (e.g. -0.39) | BRAIN 夏普比率（如 -0.39） |
| `--fitness <F>` | BRAIN fitness score (e.g. -0.18) | BRAIN 适应度（如 -0.18） |
| `--turnover <F>` | BRAIN turnover as decimal (e.g. 0.1379 = 13.79%) | BRAIN 换手率（小数，如 0.1379） |
| `--returns <F>` | BRAIN returns as decimal (e.g. -0.0283 = -2.83%) | BRAIN 收益率（小数，如 -0.0283） |
| `--drawdown <F>` | BRAIN drawdown as decimal (e.g. 0.218 = 21.80%) | BRAIN 最大回撤（小数，如 0.218） |
| `--margin <F>` | BRAIN margin as decimal (e.g. -0.000411 = -4.11‱) | BRAIN 保证金（小数，如 -0.000411） |
| `--status <X>` | Acceptance status: auto / accepted / rejected | 状态：自动检测/已通过/已拒绝 |
| `--notes <X>` | Additional notes | 备注 |

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


### 提示词

你现在是我的WorldQuant BRAIN量化导师。

请把下面英文教程：
1. 翻译成中文
2. 用小学能理解的方式解释
3. 解释所有量化术语
4. 给出Python对应实现
5. 告诉我这个知识如何应用到alpha_agent项目

内容如下：


---


## License

MIT
