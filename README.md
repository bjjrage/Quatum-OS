# Trading / Quant OS (Quantum-OS) — v1.4.1 Hardened

> **An evidence-driven alpha discovery, validation, allocation, risk and execution operating system.**

Trading / Quant OS is a multi-strategy quantitative operating system designed to host, test, allocate, and govern diverse alpha strategies under strict empirical evidence gates. It is **not** a single-purpose trading bot.

Initial seed research programs (**STR-001**, **STR-002 v2**, **STR-003**, and **STR-PUMP-COPY**) serve as test candidates within the OS, but do not define its architecture.

---

## 1. Top-Level Authoritative Architecture

```text
MARKET / EXTERNAL DATA
        ↓
DATA FABRIC (Lakehouse Parquet / DuckDB / SHA-256 Manifests / Profile v2 100ms)
        ↓
RESEARCH INFRASTRUCTURE (Point-in-Time Loader / Features / Events / Synthetic Generator / ExperimentRegistry)
        ↓
ALPHA DISCOVERY / STRATEGY FACTORY (Counterparty Thesis Gate / Rule Provenance)
        ↓
STRATEGY CANDIDATES (STR-001 Empirical / STR-002 v2 2-Factor Residual Long-Only / STR-003 / STR-PUMP-COPY)
        ↓
PORTFOLIO SELECTION GATES (Latency Sensitivity / Temporal Decay / Multiple Testing DSR / Correlation & Capacity)
        ↓
DETERMINISTIC BACKTEST ENGINE (Purged Walk-Forward CV / Asymmetric Ridge Regression)
        ↓
REGIME / POLICY ENGINE (Hierarchical Macro/Domain/Strategy Regimes / AI Metadata Isolation)
        ↓
PORTFOLIO / CAPITAL ALLOCATION (THE OS DOES NOT SELECT THE BEST BACKTEST / Multi-Edge Ensemble Budgeting)
        ↓
DETERMINISTIC RISK ENGINE & CAPITAL POCKETS (OWN vs PROP Pockets / MultiAccountEvidenceGate / Prop Rule Profiles)
        ↓
REALISTIC PAPER BROKER (Queue Priority / Execution Latency / Slippage / Maker-Taker Fees / Virtual Dry-Run)
        ↓
PERFORMANCE ATTRIBUTION ENGINE (Alpha / Beta / Fees / Slippage / Implementation Shortfall)
        ↓
GOVERNANCE & LIFECYCLE (Active / Reduced / Paused / Killed / Archived)
```

---

## 2. Core Governance Rules & OS Invariants

1. **NO STRATEGY IS PRIVILEGED BY ORIGIN:**
   Human intuition, quantitative research, statistical discovery, ML-discovered signals, and AI-assisted hypotheses compete under identical empirical evidence gates. Origin is metadata; origin is **not** evidence.
2. **THE OS DOES NOT SELECT THE BEST BACKTEST:**
   The operating system never picks a single "winner-take-all" strategy based solely on backtest metrics (Sharpe ratio, CAGR). Sizing is modulated by estimation uncertainty, multiple testing trial counts, cross-strategy correlation, liquidity capacity, and latency margins.
3. **COUNTERPARTY THESIS MANDATORY FOR VALIDATION:**
   A strategy candidate cannot transition from `RESEARCH` to `VALIDATION` without a complete `CounterpartyThesis` detailing counterparty types, economic mechanism, execution urgency, transient impact rationale, and testable falsification conditions.
4. **STR-002 v2 EXECUTION INVARIANT — STRICTLY LONG-ONLY:**
   STR-002 v2 trades forced liquidation overshoot reversals on altcoins using a 2-factor residual model ($r_{alt} - \beta r_{BTC} - \gamma \eta_{ETH}$). Execution is strictly **LONG-ONLY**. Short side is research-only ($0 live or paper risk, 0 orders).
5. **CAPITAL POCKETS & MULTI-ACCOUNT ISOLATION:**
   Two distinct pocket types: `OWN` (direct compounding capital) and `PROP` (funded/eval accounts with trailing drawdowns and daily loss limits). A loss in PROP never reduces OWN capital limits (zero risk transfer). Connecting a second account from the same provider is blocked until written contract terms are provided (`MultiAccountEvidenceGate`). 5 consecutive exam failures triggers the kill switch, permanently marking the strategy `PROP_INELIGIBLE`.
6. **EVIDENCE GATES OVER CAPITAL:**
   No candidate strategy receives live capital allocation without passing quantitative backtesting, out-of-sample holdout periods, and real-time paper execution validation. Stages `IDEA`, `RESEARCH`, `VALIDATION`, `HOLDOUT`, `PAPER`, `PAUSED`, `KILLED`, `ARCHIVED` receive strictly $0.00 capital.
7. **TIER 5 UNTRADABLE EXECUTION LOCK:**
   Every market evaluated for execution has a point-in-time `TradabilityScore`. If spread, book depth, volume, clock skew, or manifest validity breach limits, the market is classified as `TIER_5_UNTRADABLE` and execution is strictly blocked.
8. **RISK IS FINAL AUTHORITY:**
   The Risk Engine holds absolute veto authority over all orders and exposures. It enforces portfolio drawdown circuit breakers, gross leverage ceilings across all accounts combined, single-asset concentration limits, high-frequency burst rate limiting, and aggregates risk across **EventCluster** definitions.
9. **ZERO LIVE CAPITAL INVARIANT:**
   Live capital remains strictly `LOCKED ($0 Live Risk)`. Virtual dry-run and paper execution are permitted; real exchange routing is physically blocked.
10. **LIQUIDATION PROXY TAGGING:**
    Exchange liquidation streams (e.g. Binance `!forceOrder@arr`) are explicitly tagged as `PARTIAL_LIQUIDATION_INDICATOR`. They represent a throttled sample, never the exhaustive universe of liquidation events.

---

## 3. Implementation Status Matrix

| Component | Status | Description |
|---|---|---|
| **Batch 0 Market Data Foundation** | `[IMPLEMENTED]` | Live collectors for Polymarket, Deribit, Binance USDⓈ-M (Public/Market WS), Binance OI poller. Continuous recorder running in background (PID 15552). |
| **Recorder Profile v2** | `[IMPLEMENTED]` | High-frequency `depth20@100ms`, `!forceOrder@arr` tagged as `PARTIAL_LIQUIDATION_INDICATOR`, separate `data/raw_v2/` storage sink. |
| **Bybit Linear Adapter** | `[IMPLEMENTED]` | Normalized orderbook and liquidation parsing for Bybit v5 USDT perpetuals; continuous recorder integration pending. |
| **Strict Timestamp Engine** | `[IMPLEMENTED]` | Strict UTC epoch nanoseconds (`ts_exchange_ns`, `ts_received_utc_ns`), local monotonic durations (`ts_received_mono_ns`), clock skew inference, and corrected transit latency. |
| **Lakehouse Storage Sink** | `[IMPLEMENTED]` | Async buffered Parquet writer, Zstandard compression (level 7), atomic `.tmp` rename, SHA-256 partition manifests. |
| **Data Quality & Tradability Tiers** | `[IMPLEMENTED]` | Continuous background run active with continuity preserved across restarts via `RuntimeManifest.resume_or_create`. Point-in-time `TradabilityScore` and `LiquidityTierPolicy` (Tier 5 execution lock). 24h & 72h data gates `[PENDING]`. |
| **Research Infrastructure & Experiments** | `[IMPLEMENTED]` | Strict Point-in-Time (PIT) data loader, synthetic multi-venue generator, feature engine, `ExperimentRegistry` (durable JSON-lines storage, automatic trial counting, forbidden deletion), and parameter fingerprinting. |
| **Four Portfolio Selection Gates** | `[IMPLEMENTED]` | Gate A (Latency Sensitivity / `LATENCY_RACE`), Gate B (Temporal Stability & Decay), Gate C (Multiple Testing DSR / FDR), Gate D (Correlation & Capacity). Fully auditable `StrategyGateResult` contract with thresholds documented as provisional research priors. |
| **Portfolio Allocator (Multi-Edge Ensemble)** | `[IMPLEMENTED]` | Allocator enforcing "the OS does not select the best backtest". Modulated by uncertainty, capacity, latency margin, and EventClusters. Actions: `SCALE`, `REDUCE`, `PAUSE`, `KILL`. |
| **STR-001 Empirical Pipeline** | `[IMPLEMENTED]` | Black-76, exact Breeden-Litzenberger strike derivative with skew, synthetic smile arbitrage validators, Deribit inverse numéraire proof & normalization. Mathematical foundation validated; economic edge NOT validated. |
| **STR-002 v2 Liquidity Shock Reversal** | `[IMPLEMENTED]` | Complete engineering framework implemented (2-factor residual $r_{alt} - \beta_{down} r_{BTC} - \gamma \eta_{ETH}$, BTC multi-horizon decision matrix, pluggable first reversal detectors, reference price exit, isolated M0-M7 variants, strictly `LONG ONLY`). Economic edge NOT validated (hypothesis status only). |
| **Capital Pockets & Multi-Account Risk** | `[IMPLEMENTED]` | `OWN` vs `PROP` isolation, `MultiAccountEvidenceGate` (written contract terms enforcement), versioned `PropRuleProfile`, aggregate multi-account risk limits. |
| **Prop Exam Monte Carlo Simulator** | `[IMPLEMENTED]` | Path-dependent empirical block-bootstrap trade return simulator. Gaussian IID fallback strictly rejected. 5-attempt consecutive failure kill switch per strategy/provider combination. |
| **Deterministic Risk Engine & EventCluster** | `[IMPLEMENTED]` | Absolute order veto, portfolio max drawdown circuit breaker, gross leverage ceiling, single-asset concentration limits, burst rate limiter, EventCluster correlated exposure aggregation. |
| **Execution Domain Contracts & Tracker** | `[IMPLEMENTED]` | Pure execution domain contracts (`OrderIntent`, `ExecutionReport`, state transitions `CREATED` → `ROUTED` → `ACKNOWLEDGED` → `FILLED`), deterministic SHA-256 idempotency key generation, and in-memory reconciliation tracker. |
| **Realistic Paper Broker** | `[IMPLEMENTED]` | Queue position FIFO fill modeling, network transit latency simulation (orders execute strictly against post-latency market state, never stale T0 BBO quotes), market impact / slippage models, maker-taker fee accounting, multi-asset PnL ledger. |
| **Regime / Policy Engine** | `[IMPLEMENTED]` | Deterministic hierarchical macro/domain/strategy regime classification, capital allocation multipliers, AI metadata advisory isolation. |
| **Attribution Engine** | `[IMPLEMENTED]` | Multi-factor PnL decomposition: Gross PnL, Net PnL, Alpha, Beta, Maker/Taker Fees, Slippage, and Implementation Shortfall. |
| **24-Point Red-Team Attack Matrix** | `[IMPLEMENTED]` | Comprehensive verification of 24 attack vectors: recorder continuity, BTC regime gating, z-score validation status, parameter fingerprinting, durable registry persistence, Pydantic field rejection, Tier 5 tradability, Monte Carlo sample size & Gaussian rejection, prop kill switches, multi-account copy rules, cross-account risk evasion, risk hard stops, post-latency market order execution, execution idempotency, holdout freeze, direct active injection, and locked live capital. |
| **CI / Offline Test Suite** | `[IMPLEMENTED]` | **178 passing tests (0 failures)** across all mathematical, infrastructure, risk, paper broker, portfolio, prop simulator, red-team, and full governance lifecycle modules. |


---

## 4. Seed Research Programs

### STR-001: Polymarket × Deribit Relative Value
- **Family:** `RELATIVE_VALUE` / `CROSS_MARKET`
- **Origin:** `QUANT`
- **Stage:** `RESEARCH`
- **Status:** Mathematical pricing foundation validated (Deribit inverse numéraire verified). Empirical pipeline implemented with `digital_call_prob_analytic` and hurdle rates. Complete `CounterpartyThesis` registered.
- **Privilege:** None (`is_privileged` is strictly read-only `False`).

### STR-002 v2: Liquidity Shock Reversal
- **Family:** `BEHAVIORAL` / `MEAN_REVERSION`
- **Origin:** `HUMAN`
- **Stage:** `RESEARCH`
- **Execution Invariant:** Strictly **LONG-ONLY**. Short side is research-only ($0 capital, 0 orders).
- **Core Mechanism:** 2-factor residual model separating systemic BTC/ETH moves from idiosyncratic liquidation cascades.
  - Ridge-regularized asymmetric beta ($\beta_{down} > \beta_{up}$).
  - BTC State Module & Decision Matrix (`FLAT`, `UP`, `DOWN`, `RUNNING_HARD`).
  - Pluggable First Reversal Detectors: Aggressor flow flip, book replenishment (>50%), microstructure higher low.
  - Reference Price Exit Targets: Pre-shock VWAP, origin price, half-retracement, 15-minute time decay.
  - Complete point-in-time `RegimeSnapshot` recorded on every candidate trade.
- **Privilege:** None (`is_privileged` is strictly read-only `False`).

### STR-003: Scheduled Supply Events / Unlock Overshoot
- **Family:** `EVENT_NEWS`
- **Origin:** `QUANT`
- **Stage:** `RESEARCH`
- **Thesis:** Microstructure and basis dislocations around scheduled contractual token vesting unlocks.
- **Privilege:** None (`is_privileged` is strictly read-only `False`).

### STR-PUMP-COPY: Pump.fun Copytrading Research
- **Family:** `ON_CHAIN`
- **Origin:** `STATISTICAL`
- **Stage:** `RESEARCH` ($0 capital, prop ineligible, strictly on-chain if ever validated).
- **Risk Profile:** 100% loss probability per token, gas + priority fee drag, sandwich vulnerability, copy-latency decay.
- **Privilege:** None (`is_privileged` is strictly read-only `False`).

---

## 5. Development & Verification

### Running the Offline Test Suite
```bash
uv run pytest -v
```
*Current test suite: **178 passing tests (0 failures)** across all modules in ~1.4s.*

### Auditable Data Quality & Acceptance Reporting
```bash
# Generate comprehensive acceptance report and formatted console summary
uv run python scripts/data_quality_report.py

# Output raw JSON report for automated monitoring
uv run python scripts/data_quality_report.py --json-only
```
