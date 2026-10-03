# Trading / Quant OS (Quantum-OS)

> **An evidence-driven alpha discovery, validation, allocation, risk and execution operating system.**

Trading / Quant OS is a multi-strategy quantitative operating system designed to host, test, allocate, and govern diverse alpha strategies under strict empirical evidence gates. It is **not** a single-purpose trading bot.

Initial seed research programs (**STR-001**: Polymarket × Deribit Relative Value, and **STR-002**: Impulse / Overshoot Retracement) serve as test candidates within the OS, but do not define its architecture.

---

## 1. Top-Level Authoritative Architecture

```text
MARKET / EXTERNAL DATA
        ↓
DATA FABRIC (Lakehouse Parquet / DuckDB / SHA-256 Manifests)
        ↓
RESEARCH INFRASTRUCTURE (Point-in-Time Loader / Features / Events / Synthetic Generator)
        ↓
ALPHA DISCOVERY / STRATEGY FACTORY (Evidence Admission Gate)
        ↓
STRATEGY CANDIDATES (STR-001 Empirical Pipeline / STR-002 14-Dimension Event Study)
        ↓
DETERMINISTIC BACKTEST ENGINE (Purged Walk-Forward CV / Multiple Testing Corrections)
        ↓
REGIME / POLICY ENGINE (Multi-Tier Macro/Domain/Strategy Regimes / AI Metadata Isolation)
        ↓
PORTFOLIO / CAPITAL ALLOCATION (Evidence-Gated Budgets / $0 Live Allocation Invariant)
        ↓
DETERMINISTIC RISK ENGINE (Circuit Breakers / EventCluster Aggregation / Leverage Ceiling / Burst Rate Limiter)
        ↓
REALISTIC PAPER BROKER (Queue Priority / Execution Latency / Slippage / Maker-Taker Fees / Virtual Dry-Run)
        ↓
PERFORMANCE ATTRIBUTION ENGINE (Alpha / Beta / Fees / Slippage / Implementation Shortfall)
        ↓
GOVERNANCE & LIFECYCLE (Active / Reduced / Paused / Killed / Archived)
```

---

## 2. Core Governance Rules

1. **NO STRATEGY IS PRIVILEGED BY ORIGIN:**
   Human intuition, quantitative research, statistical discovery, ML-discovered signals, and AI-assisted hypotheses compete under identical empirical evidence gates. Origin is metadata; origin is **not** evidence.
2. **EVIDENCE GATES OVER CAPITAL:**
   No candidate strategy receives live capital allocation without passing quantitative backtesting, out-of-sample holdout periods, and real-time paper execution validation. Stages `IDEA`, `RESEARCH`, `VALIDATION`, `HOLDOUT`, `PAPER`, `PAUSED`, `KILLED`, `ARCHIVED` receive strictly $0.00 capital.
3. **RISK IS FINAL AUTHORITY:**
   The Risk Engine holds absolute veto authority over all orders and exposures. It enforces portfolio drawdown circuit breakers (only de-risking allowed if breached), gross leverage ceilings, single-asset concentration limits, high-frequency burst rate limiting, and aggregates risk across **EventCluster** definitions (correlated market shocks).
4. **AI/ML EXECUTION BOUNDARIES:**
   LLMs (Luna) and classification models participate in hypothesis generation, event reasoning, and anomaly detection. They are **strictly forbidden** from direct order routing, modifying stops/targets, or accessing exchange private keys. AI comments are strictly isolated to descriptive advisory metadata.
5. **ZERO LIVE CAPITAL INVARIANT:**
   Live capital remains strictly `LOCKED ($0 Live Risk)`. Virtual dry-run and paper execution are permitted; real exchange routing is physically blocked.

---

## 3. Implementation Status Matrix

| Component | Status | Description |
|---|---|---|
| **Batch 0 Market Data Foundation** | `[IMPLEMENTED]` | Live collectors for Polymarket, Deribit, Binance USDⓈ-M (Public/Market WS), Binance OI poller. |
| **Strict Timestamp Engine** | `[IMPLEMENTED]` | Strict UTC epoch nanoseconds (`ts_exchange_ns`, `ts_received_utc_ns`), local monotonic durations (`ts_received_mono_ns`), clock skew inference, and corrected transit latency. |
| **Lakehouse Storage Sink** | `[IMPLEMENTED]` | Async buffered Parquet writer, Zstandard compression (level 7), atomic `.tmp` rename, SHA-256 partition manifests. |
| **Quant Pricing & Numéraire (Line A)** | `[IMPLEMENTED]` | Black-76, exact Breeden-Litzenberger strike derivative with skew, synthetic smile arbitrage validators, Deribit inverse numéraire proof & normalization. |
| **Strategy Domain & Registry** | `[IMPLEMENTED]` | Pure domain models (`StrategySpec`, `StrategyStage`, `StrategyOrigin`, `StrategyFamily`), `StrategyRegistry` (evidence-gated lifecycle, zero execution authority, seed strategies STR-001 & STR-002). |
| **Data Quality & Acceptance Gates** | `[RUNNING / PENDING]` | Continuous background run active (>4.98M rows recorded, 0 orphan tmp files, 100% verified SHA-256 manifests, 0 causal anomalies). 24h & 72h gates remain strictly `[PENDING]` until required continuous run duration elapses. |
| **Research Infrastructure** | `[IMPLEMENTED]` | Strict Point-in-Time (PIT) data loader, synthetic multi-venue market generator, feature engine (returns, realized vol, imbalance, spread bps), statistical price impulse event detector. |
| **Deterministic Backtest Engine** | `[IMPLEMENTED]` | Event-driven market simulator, limit/market order queue models, purged walk-forward cross-validation splits, Deflated Sharpe / multiple testing adjustments. |
| **Strategy Factory & Candidates** | `[IMPLEMENTED]` | `CandidateHypothesis`, `Signal`, `EvidenceAdmissionGate`, `STR001RelativeValueAlpha` empirical pipeline, and `STR002EventStudy` (14-dimension trajectory & move classification). |
| **Deterministic Risk Engine & EventCluster** | `[IMPLEMENTED]` | Absolute order veto, portfolio max drawdown circuit breaker, gross leverage ceiling, single-asset concentration limits, burst rate limiter, EventCluster correlated exposure aggregation. |
| **Realistic Paper Broker** | `[IMPLEMENTED]` | Queue position FIFO fill modeling, network transit latency simulation, market impact / slippage models, maker-taker fee accounting, multi-asset PnL ledger. |
| **Regime / Policy Engine** | `[IMPLEMENTED]` | Deterministic hierarchical macro/domain/strategy regime classification, capital allocation multipliers, AI metadata advisory isolation. |
| **Portfolio Allocation Framework** | `[IMPLEMENTED]` | Evidence-gated capital budgeting, stage-based capital ceilings ($0 non-live, $5k small-live cap, risk-budgeted active), strict live capital lockout. |
| **Attribution Engine** | `[IMPLEMENTED]` | Multi-factor PnL decomposition: Gross PnL, Alpha, Beta, Maker/Taker Fees, Slippage, and Implementation Shortfall. |
| **End-to-End Replay & Adversarial Tests** | `[IMPLEMENTED]` | Full synthetic tick -> feature -> signal -> regime -> allocator -> risk -> paper broker -> attribution pipeline replay. Adversarial flash crash, spread blowout, burst order flooding, and live lockout tests. |
| **CI / Offline Test Suite** | `[IMPLEMENTED]` | 91 comprehensive offline unit tests across all mathematical, infrastructure, risk, paper broker, portfolio, and replay modules. |

---

## 4. Repository Structure

```
TRADING OS / Quantum-OS
├── .github/
│   └── workflows/
│       └── test.yml                 # GitHub Actions offline CI test suite (91 passing tests)
├── config/
│   └── settings.py                  # Venue URLs, channels, and contract configs
├── src/
│   ├── attribution/                 # Performance attribution & factor decomposition
│   │   └── engine.py                # Alpha, Beta, fee drag, slippage, implementation shortfall
│   ├── backtest/                    # Event-driven backtest engine & validation
│   │   ├── engine.py                # Deterministic market simulator, limit/market orders, fees
│   │   └── validation.py            # Purged walk-forward CV, Deflated Sharpe Ratio
│   ├── collectors/                  # Multi-venue live market data collectors
│   │   ├── binance_oi_poller.py     # REST Open Interest poller (30s cadence)
│   │   ├── binance_recorder.py      # Public & Market WebSocket streams
│   │   ├── deribit_recorder.py      # DVOL, index prices, trades, options ticker metrics
│   │   ├── polymarket_recorder.py   # CLOB WS (book, price_change, last_trade_price, tick_size_change)
│   │   └── manager.py               # Orchestration & lifecycle manager
│   ├── common/                      # Core infrastructure primitives
│   │   ├── dns_patch.py             # Transparent DNS fallback for Cloudflare edge routing
│   │   ├── logger.py                # Structured JSON logging
│   │   ├── manifest.py              # SHA-256 partition manifest & verification
│   │   ├── storage_sink.py          # Buffered Parquet writer (atomic rename, Zstd level 7)
│   │   └── types.py                 # Nanosecond timestamp models & PyArrow schemas
│   ├── paper/                       # Realistic paper broker & execution simulator
│   │   └── broker.py                # FIFO queue depth, latency modeling, slippage, maker/taker fees
│   ├── portfolio/                   # Evidence-gated portfolio capital budgeting
│   │   └── allocator.py             # Stage-based capital limits & regime scaling
│   ├── quality/                     # Data Quality & Acceptance Gate Infrastructure
│   │   ├── acceptance.py            # State machine, strict duration gating, runtime manifest
│   │   ├── clock_sync.py            # Local host clock skew inference & transit latency correction
│   │   ├── fingerprint.py           # Deterministic SHA-256 config fingerprinting
│   │   ├── metrics.py               # DuckDB metrics collector (storage, latency, coverage)
│   │   └── reporter.py              # Automated acceptance report generator
│   ├── quant/                       # Mathematical pricing & volatility models
│   │   ├── black76.py               # Black-76 pricing, greeks, and flat-vol probability
│   │   ├── deribit_inverse.py       # Inverse-option numéraire proof & normalization
│   │   ├── digital_probability.py   # Strike derivative with skew & finite difference
│   │   └── smile_validation.py      # Volatility smiles & no-arbitrage validators
│   ├── regime/                      # Regime & Policy Engine
│   │   └── policy_engine.py         # Multi-tier regime classification, risk multipliers, AI isolation
│   ├── research/                    # Research infrastructure & feature engineering
│   │   ├── events.py                # Price impulse & microstructure shock detector
│   │   ├── features.py              # FeatureEngine (returns, vol, imbalance, spread) & BarAggregator
│   │   └── pit_loader.py            # Strict Point-in-Time loader & SyntheticMarketGenerator
│   ├── risk/                        # Deterministic Risk Engine & EventCluster
│   │   ├── engine.py                # Pre-trade order veto, drawdown circuit breaker, leverage ceiling
│   │   └── event_cluster.py         # Cross-asset economic shock clustering & stress loss limits
│   └── strategies/                  # Strategy domain, factory, candidates & lifecycle
│       ├── factory.py               # CandidateHypothesis, Signal, EvidenceAdmissionGate
│       ├── models.py                # StrategySpec, StrategyStage, StrategyOrigin, StrategyFamily
│       ├── registry.py              # StrategyRegistry (purely declarative, zero execution authority)
│       ├── str001_empirical.py      # STR-001 Polymarket x Deribit relative value pipeline
│       └── str002_event_study.py    # STR-002 14-dimension event study & move classification
├── tests/
│   ├── e2e/                         # 5 end-to-end replay & adversarial stress tests
│   ├── math/                        # 30 unit tests for pricing, skew, arbitrage, and numéraire
│   ├── test_backtest.py             # Backtest engine & purged walk-forward validation tests
│   ├── test_paper_broker.py         # Paper broker queue, latency, slippage, and PnL tests
│   ├── test_parsers.py              # Venue payload parsing tests
│   ├── test_portfolio_regime.py     # Policy engine, allocator, and attribution tests
│   ├── test_quality.py              # 10 acceptance gate, duration gating & clock sync tests
│   ├── test_research.py             # PIT data loader, features, events, and synthetic data tests
│   ├── test_risk.py                 # Risk engine circuit breakers, leverage, and cluster tests
│   ├── test_storage_sink.py         # Buffered parquet storage tests
│   ├── test_strategies.py           # Strategy domain, privilege & governance lifecycle tests
│   ├── test_strategy_candidates.py  # Factory admission gate and STR-001/002 tests
│   └── test_types.py                # Schema & timestamp completeness tests
└── scripts/
    ├── data_quality_report.py       # Auditable acceptance gate report generator
    ├── run_recorder.py              # Continuous production market recorder
    ├── smoke_test.py                # Live multi-venue connectivity & DuckDB verification
    └── verify_data.py               # Lakehouse dataset inspector
```

---

## 5. Seed Research Programs

### STR-001: Polymarket × Deribit Relative Value
- **Family:** `RELATIVE_VALUE` / `CROSS_MARKET`
- **Origin:** `QUANT`
- **Stage:** `ACTIVE` (Simulated Paper Validation)
- **Status:** Mathematical pricing foundation validated (Deribit inverse numéraire verified). Empirical pipeline implemented with `digital_call_prob_analytic` and hurdle rates.
- **Privilege:** None (Hardened invariant: `is_privileged` is read-only `False`).

### STR-002: Impulse / Overshoot / Short-Horizon Retracement
- **Family:** `BEHAVIORAL` / `MEAN_REVERSION`
- **Origin:** `HUMAN`
- **Stage:** `RESEARCH`
- **Thesis:** Extreme short-horizon price impulses, normalized by prior volatility, may exhibit an exploitable overshoot followed by retracement.
- **Evaluation Criteria:**
  - Order-book information is an evaluation **feature**, not the definition of the strategy.
  - Distinguishes **Informative Moves** (hacks, delistings, fundamental news that may rationally never revert) from **Forced Moves** (cascading liquidations, stop cascades, deleveraging that overshoot and retrace).
  - Evaluated across 14 empirical dimensions (impulse magnitude, prior volatility, forward returns, MFE, MAE, retracement ratio, time-to-retracement, liquidity, spread, depth, funding, OI, forced liquidations, market regime).
- **Status:** Evaluated under the exact same empirical criteria as quantitative models.
- **Privilege:** None (Hardened invariant: `is_privileged` is read-only `False`).

---

## 6. Development & Verification

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup
```bash
git clone https://github.com/bjjrage/Quatum-OS.git
cd Quatum-OS
uv sync
```

### Running the Offline Test Suite
```bash
uv run pytest -v
```
*Current test suite: **91 passing tests (0 failures)** across all modules in ~1.2s.*

### Auditable Data Quality & Acceptance Reporting
```bash
# Generate comprehensive acceptance report and formatted console summary
uv run python scripts/data_quality_report.py

# Output raw JSON report for automated monitoring
uv run python scripts/data_quality_report.py --json-only
```

#### Acceptance Gate Invariants:
- **24h Acceptance Gate (`MIN_24H_SECONDS = 86400`):** Continuous production recording without data corruption, valid SHA-256 partition manifests, zero orphan `.tmp` files, and continuous coverage of all configured venues. Under 24 continuous hours, this gate evaluates strictly as `PENDING`.
- **72h Acceptance Gate (`MIN_72H_SECONDS = 259200`):** Extended stability run verifying long-horizon continuity, feed reconnection resilience, and storage projection consistency. Under 72 continuous hours, this gate evaluates strictly as `PENDING`.
- **Live Capital Policy:** **LOCKED ($0 Live Risk)**. No capital is unblocked until formal acceptance gates are satisfied.
