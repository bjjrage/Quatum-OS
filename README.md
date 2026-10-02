# Trading / Quant OS (Quantum-OS)

> **An evidence-driven alpha discovery, validation, allocation, risk and execution operating system.**

Trading / Quant OS is a multi-strategy quantitative operating system designed to host, test, allocate, and govern diverse alpha strategies under strict empirical evidence gates. It is **not** a single-purpose trading bot.

Initial seed research programs (**STR-001**: Polymarket × Deribit Relative Value, and **STR-002**: Impulse / Overshoot Retracement) serve as test candidates within the OS, but do not define its architecture.

---

## 1. Top-Level Authoritative Architecture

```text
MARKET / EXTERNAL DATA
        ↓
DATA FABRIC
        ↓
FEATURE / CONTEXT LAYER
        ↓
ALPHA DISCOVERY / STRATEGY FACTORY
        ↓
STRATEGY REGISTRY
        ↓
DISCOVERY
        ↓
VALIDATION
        ↓
HOLDOUT
        ↓
PAPER
        ↓
REGIME / POLICY ENGINE
        ↓
PORTFOLIO / CAPITAL ALLOCATION
        ↓
RISK ENGINE
        ↓
EXECUTION ENGINE
        ↓
ATTRIBUTION
        ↓
SCALE / REDUCE / PAUSE / KILL
```

---

## 2. Core Governance Rules

1. **NO STRATEGY IS PRIVILEGED BY ORIGIN:**
   Human intuition, quantitative research, statistical discovery, ML-discovered signals, and AI-assisted hypotheses compete under identical empirical evidence gates. Origin is metadata; origin is **not** evidence.
2. **EVIDENCE GATES OVER CAPITAL:**
   No candidate strategy receives live capital allocation without passing quantitative backtesting, out-of-sample holdout periods, and real-time paper execution validation.
3. **RISK IS FINAL AUTHORITY:**
   The Risk Engine holds absolute veto authority over all orders and exposures. It aggregates risk by **EventCluster** (economic exposure across correlated assets) rather than simple position counts.
4. **AI/ML EXECUTION BOUNDARIES:**
   LLMs (Luna) and classification models (Jev) participate in hypothesis generation, event reasoning, and anomaly detection. They are **strictly forbidden** from direct order routing, modifying stops/targets, or accessing exchange private keys.

---

## 3. Implementation Status Matrix

| Component | Status | Description |
|---|---|---|
| **Batch 0 Market Data Foundation** | `[IMPLEMENTED]` | Live collectors for Polymarket, Deribit, Binance USDⓈ-M (Public/Market WS), Binance OI poller. |
| **Strict Timestamp Engine** | `[IMPLEMENTED]` | Strict UTC epoch nanoseconds (`ts_exchange_ns`, `ts_received_utc_ns`), local monotonic durations (`ts_received_mono_ns`), and observed event age. |
| **Lakehouse Storage Sink** | `[IMPLEMENTED]` | Async buffered Parquet writer, Zstandard compression (level 7), atomic `.tmp` rename, SHA-256 partition manifests. |
| **Quant Pricing & Numéraire (Line A)** | `[IMPLEMENTED]` | Black-76, exact Breeden-Litzenberger strike derivative with skew, synthetic smile arbitrage validators, Deribit inverse numéraire proof & normalization. |
| **Strategy Domain & Registry** | `[IMPLEMENTED]` | Pure domain models (`StrategySpec`, `StrategyStage`, `StrategyOrigin`, `StrategyFamily`), `StrategyRegistry` (zero execution authority, seed strategies STR-001 & STR-002). |
| **CI / Offline Test Suite** | `[IMPLEMENTED]` | GitHub Actions CI workflow, 46 offline unit tests across math, strategies, and storage foundation. |
| **Strategy Factory / Alpha Discovery** | `[ARCHITECTURAL]` | Extensible candidate generator framework designed to host multiple strategy families. |
| **EventCluster Risk Layer** | `[ARCHITECTURAL]` | Economic shock clustering and cross-position risk capping architecture. |
| **Portfolio / Capital Allocation** | `[ARCHITECTURAL]` | Interface and governance specified; numerical allocation formulas deferred. |
| **Regime / Policy Engine** | `[ARCHITECTURAL]` | Multi-tier context model mapping structured domain states into validated risk profiles. |
| **Paper Trading Engine** | `[PLANNED]` | Virtual fill simulator and latency modeling for candidate validation. |
| **Production Risk Engine** | `[PLANNED]` | Standalone circuit breakers, max drawdown gates, and real-time margin governor. |
| **Execution Engine & Adapters** | `[PLANNED]` | Venue-specific order routing, TWAP/VWAP execution, private API key management. |
| **STR-001 Economic Validation** | `[PLANNED]` | Historical backtest, holdout testing, and paper trading for Polymarket × Deribit RV. |
| **STR-002 Economic Validation** | `[PLANNED]` | Statistical testing of impulse overshoot and retracement edge. |

---

## 4. Repository Structure

```
TRADING OS / Quantum-OS
├── .github/
│   └── workflows/
│       └── test.yml                 # GitHub Actions offline CI test suite
├── config/
│   └── settings.py                  # Venue URLs, channels, and contract configs
├── src/
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
│   ├── quant/                       # Mathematical pricing & volatility models
│   │   ├── black76.py               # Black-76 pricing, greeks, and flat-vol probability
│   │   ├── deribit_inverse.py       # Inverse-option numéraire proof & normalization
│   │   ├── digital_probability.py   # Strike derivative with skew & finite difference
│   │   └── smile_validation.py      # Volatility smiles & no-arbitrage validators
│   └── strategies/                  # Strategy domain & lifecycle management
│       ├── models.py                # StrategySpec, StrategyStage, StrategyOrigin, StrategyFamily
│       └── registry.py              # StrategyRegistry (purely declarative, zero execution authority)
├── tests/
│   ├── math/                        # 30 unit tests for pricing, skew, arbitrage, and numéraire
│   ├── test_parsers.py              # Venue payload parsing tests
│   ├── test_storage_sink.py         # Buffered parquet storage tests
│   ├── test_strategies.py           # 10 strategy domain & registry lifecycle tests
│   └── test_types.py                # Schema & timestamp completeness tests
└── scripts/
    ├── run_recorder.py              # Continuous production market recorder
    ├── smoke_test.py                # Live multi-venue connectivity & DuckDB verification
    └── verify_data.py               # Lakehouse dataset inspector
```

---

## 5. Seed Research Programs

### STR-001: Polymarket × Deribit Relative Value
- **Family:** `RELATIVE_VALUE` / `CROSS_MARKET`
- **Origin:** `QUANT`
- **Stage:** `RESEARCH`
- **Status:** Mathematical pricing foundation validated (Deribit inverse numéraire verified). Economic edge **not yet validated** (pending historical backtesting and paper trading).
- **Privilege:** None.

### STR-002: Impulse / Overshoot / Short-Horizon Retracement
- **Family:** `BEHAVIORAL` / `MEAN_REVERSION`
- **Origin:** `HUMAN`
- **Stage:** `RESEARCH`
- **Status:** Human intuition hypothesis. Unvalidated. Evaluated under the exact same empirical criteria as quantitative models.
- **Privilege:** None.

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
*Current test suite: 46 passing tests (0 failures).*

### Running Live Recorder Smoke Verification
```bash
uv run python scripts/smoke_test.py --duration 10
```
