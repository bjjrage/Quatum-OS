# Quant Cockpit v1 — Operational UI for Trading / Quant OS

**Quant Cockpit v1** is the institutional-grade operational user interface and command terminal for **Trading / Quant OS** (`bjjrage/Quatum-OS`).

The system connects a high-density, dark-mode Next.js 14 operator terminal directly to the Python Quant OS kernel via an authoritative FastAPI bridge (`apps/api`), providing real-time telemetry across raw data ingestion, liquidity tier classification, algorithmic alpha research, selection gates, portfolio construction, deterministic risk controls, and simulated paper execution.

---

## 1. Architectural Invariants

### 1.1 Zero Live Capital Risk
* **Authorized Live Capital:** Strictly `$0.00` (`LOCKED`).
* **Exchange Routing:** Outbound live order submission is physically blocked and unconfigured. No live API secrets are loaded.
* **Capital Pockets:** Pocket B (Live Capital) is permanently frozen.

### 1.2 Ingestion Acceptance Gates (24h & 72h)
* A candidate data recording run must accumulate unbroken continuous execution time without unhandled exceptions or partition corruption before model promotion.
* Gates remain strictly `PENDING` until elapsed time passes:
  * **24-Hour Gate:** 86,400 seconds
  * **72-Hour Gate:** 259,200 seconds

### 1.3 Liquidity Tier Classification: Tier 5 vs Untradable
* **Tier 5 (Small Tradable):** Symbol is **TRADABLE** (`tradable: true`), restricted to a **$5,000 USD position cap** and **LIMIT ORDERS ONLY** (passive queue placement; market orders forbidden).
* **Tier 6 (Untradable):** Symbol fails liquidity or spread criteria (`tradable: false`), with explicit rejection reasons displayed.
* *Invariant:* Tier 5 Small Tradable is never visually or logically equated with Untradable.

### 1.4 STR-002 v2 Liquidity Shock Architecture
* **Strict Long-Only Invariant:** Short-side signals are intentionally unsupported and hard-blocked.
* **Economic Edge Validation:** Explicitly labeled **NOT VALIDATED**. While mathematical formulations are validated, real-world alpha requires out-of-sample paper validation passing all four Selection Gates.
* **Model Variants:** 8 architectural models (`M0` through `M7`) with multi-horizon BTC conditioning (1m, 5m, 15m) and book-delta reversal detection.

### 1.5 Sealed Holdout Vault (Zero Leakage)
* Out-of-sample partitions remain cryptographically sealed (`SEALED`) and unobserved during model hyperparameter tuning. Opening a holdout partition burns that timeframe and logs an immutable audit event.

### 1.6 Non-Parametric Bootstrap Prop Exam Simulator
* Monte Carlo exam pass probability is evaluated strictly through non-parametric bootstrap resampling of realized trade returns.
* **Prerequisite:** A minimum sample size of **30 empirical trades** ($N \ge 30$) is required. If $N < 30$, the simulator returns **PENDING / INSUFFICIENT DATA**. Parametric Gaussian normal assumptions are strictly forbidden due to fat tails and serial dependence.

---

## 2. Directory Structure

```
TRADING OS/
├── apps/
│   ├── api/                     # Authoritative FastAPI backend bridge
│   │   ├── main.py              # Application entrypoint & CORS configuration
│   │   ├── services/
│   │   │   └── data_service.py  # Singleton binding to core Python modules
│   │   └── routers/             # Domain endpoints (17 modular routers)
│   │       ├── system.py        # System health, git SHA, pytest status
│   │       ├── recorder.py      # Telemetry & 24h/72h acceptance gates
│   │       ├── quality.py       # Lakehouse metrics & clock skew calibration
│   │       ├── markets.py       # Liquidity tier tradability gating
│   │       ├── strategies.py    # Catalog, counterparty thesis & rules
│   │       ├── experiments.py   # Research trials & parameter tracking
│   │       ├── backtests.py     # Deflated Sharpe simulation replays
│   │       ├── holdouts.py      # Sealed partition access ledger
│   │       ├── gates.py         # Gates A, B, C, D evaluation thresholds
│   │       ├── portfolio.py     # Strategy risk budgeting & cluster caps
│   │       ├── paper.py         # Simulated broker accounts & fills
│   │       ├── execution.py     # Order latency & reconciliation
│   │       ├── risk.py          # Real-time risk limits & kill switches
│   │       ├── capital.py       # Capital pockets & balance firewalls
│   │       ├── prop.py          # Prop firm profiles & Monte Carlo
│   │       ├── attribution.py   # PnL return & cost decomposition
│   │       ├── audit.py         # Cryptographic governance audit trail
│   │       └── stream.py        # Server-Sent Events real-time feed
│   └── web/                     # Institutional Quant Terminal Frontend
│       ├── app/
│       │   ├── globals.css      # Dark institutional graphite theme
│       │   ├── layout.tsx       # Root layout & terminal metadata
│       │   └── page.tsx         # Quant Cockpit single-page orchestrator
│       ├── components/
│       │   ├── common/          # Badge, Card, MetricCard, EmptyState
│       │   ├── layout/          # TopStatusStrip, SidebarNavigation
│       │   └── views/           # 16 operational domain views
│       ├── lib/
│       │   └── api.ts           # Typed API client connecting to /api/*
│       └── types/
│           └── index.ts         # Authoritative TypeScript domain models
├── src/                         # Core Python quantitative engine
│   ├── quality/                 # Acceptance gates & tradability policy
│   ├── research/                # Experiments & sealed holdout manager
│   ├── strategies/              # Strategy registry & STR-002 v2 models
│   ├── portfolio/               # Selection gates & risk allocator
│   ├── risk/                    # Risk engine, capital pockets & prop rules
│   ├── paper/                   # Simulated paper broker matching engine
│   └── execution/               # Fill reconciliation & order lifecycle
└── tests/                       # Complete pytest suite (225 passing tests)
    └── test_api_endpoints.py    # 17 comprehensive FastAPI endpoint tests
```

---

## 3. Operational Domain Views

| View Name | Nav Tab ID | Description |
|:---|:---|:---|
| **Command Center** | `command-center` | Executive overview, live capital lock, 24h/72h acceptance progress, strategy counts, system alerts. |
| **Data Recorder** | `recorder` | Exchange WebSocket telemetry (Binance, Deribit, Polymarket, Bybit), continuous elapsed timer, Parquet sink health. |
| **Data Quality & 72h** | `data-quality` | Parquet partition file count, byte compression, microsecond clock skew calibration, latency percentiles (P50/P95/P99). |
| **Markets / Tradability** | `tradability` | Pre-trade universe classification: Tier 1–4 (Liquid), Tier 5 (Small Tradable: $5k cap, limit only), Untradable. |
| **Strategy Registry** | `strategy-registry` | Catalog of 4 core seed strategies, stage lifecycle, math validation, and economic edge validation status. |
| **Strategy Detail** | `strategy-detail` | Deep dive into counterparty thesis, economic mechanism, falsification criteria, and individual rule hierarchy. |
| **STR-002 v2 Models** | `str002-specialized` | Dedicated cockpit for M0–M7 variants, multi-horizon BTC matrix (1m/5m/15m), and live factor state. |
| **Experiment Explorer** | `experiments` | Cryptographically tracked trial registry, parameter space search, and gate falsification audit log. |
| **Backtests & Replays** | `backtests` | Full transaction-cost adjusted replay, Bailey-Lopez de Prado Deflated Sharpe Ratio (DSR), and trade history. |
| **Cryptographic Holdouts**| `holdouts` | Sealed out-of-sample data vault, zero-leakage guarantee, and opening access ledger. |
| **Selection Gates (A-D)** | `selection-gates` | Gate A (Deflated Sharpe), Gate B (Latency Sensitivity), Gate C (Execution Realism), Gate D (Parameter Stability). |
| **Multi-Edge Allocator** | `portfolio` | Risk budgeting, paper allocations, event cluster exposure caps, and zero live allocation guard. |
| **Regimes & Policies** | `regimes` | Macro liquidity regime, crypto volatility chop classification, and read-only AI advisory telemetry. |
| **PnL Attribution** | `attribution` | Factor decomposition, pure alpha vs market beta, exchange fees (maker/taker), and slippage drag. |
| **Paper Trading Terminal**| `paper-trading` | Internal paper broker account, open positions, active orders, and simulated execution fills. |
| **Execution Reconciliation**| `execution` | Latency decomposition waterfall, routing authority guard, and zero-mismatch position cross-checks. |
| **Risk Engine & Limits** | `risk-engine` | Pre-trade limits, intraday loss limits, peak trailing drawdown, and automated kill switches. |
| **Event Clusters** | `event-clusters` | High-impact macro/crypto event calendar (FOMC, CPI, Halving, Options Expiry), volatility regimes, and blackout windows. |
| **Capital Pockets** | `capital-pockets` | Isolated balance containers (Pocket A: Prop, Pocket B: Live $0 Locked, Pocket C: Research Sandbox). |
| **Prop Firm Profiles** | `prop-firms` | Machine-readable rule profiles (AlphaFunding, Apex), trailing drawdown calculations, and verified policies. |
| **Monte Carlo Simulator** | `prop-simulator` | Non-parametric bootstrap exam pass simulator requiring $N \ge 30$ empirical trades (zero Gaussian fallback). |
| **Multi-Account Compliance**| `multi-account` | Cross-account isolation, order arrival jitter buffers, anti-copy trading validation, and correlation limits. |
| **Audit Trail** | `audit-trail` | Cryptographically verifiable ledger of runtime state, git SHA provenance, operator actions, and checksums. |
| **Tests & Red-Team CI** | `tests-ci` | Real-time test suite health (225 passing tests, 0 failures), coverage metrics, and execution latency. |
| **Runtime Configuration**| `configuration` | System environment settings, lakehouse directories, and immutable security parameters. |
| **Master Blueprint** | `blueprint` | End-to-end interactive architecture pipeline tracing data ingestion through execution and audit. |

---

## 4. Getting Started

### 4.1 Prerequisites
* **Python:** 3.11+ or 3.12+ managed via `uv`
* **Node.js:** 18+ or 20+
* **npm:** 9+

### 4.2 Starting the FastAPI Backend
From the project root directory:
```bash
# Start FastAPI backend server on port 8000
uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```
The API server will be accessible at `http://localhost:8000`. Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

### 4.3 Starting the Next.js Frontend
From the `apps/web` directory:
```bash
cd apps/web

# Development server
npm run dev

# Or compile and start production build
npm run build
npm start
```
The web application will be accessible at `http://localhost:3000`. The Next.js rewrite proxy automatically routes `/api/*` requests to `http://localhost:8000/api/*`.

### 4.4 Running Automated Verification Tests
From the project root:
```bash
# Run the complete test suite (225 tests)
uv run pytest -v

# Run FastAPI endpoint validation tests
uv run pytest tests/test_api_endpoints.py -v
```
All 225 unit, integration, adversarial, red-team, and API tests will execute in ~2.6 seconds.
