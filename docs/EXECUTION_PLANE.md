# Quant OS — Execution Plane v1 Specification & Architecture

## 1. Executive Summary

The Execution Plane is the deterministic electronic trading subsystem of Quant OS. It governs how strategy order intents transition through policy, risk validation, capital authorization, routing, and venue transport.

### Critical Safety Invariants
- **Authorized Live Capital = USD $0.00 (Hard Locked)**
- **Live Trading = LOCKED**
- **Economic Edge = NOT VALIDATED** (STR-001 / STR-002)
- **Real Production Orders Sent = 0**
- **Withdrawal Permission = NEVER REQUIRED** (Read-only allowed; Trade only when live phase commences; Withdrawals permanently disabled on API keys).
- **Secrets Management = ZERO LEAKAGE** (Never stored in SQLite, Git, API payloads, exceptions, logs, or audit chains).

---

## 2. Order Pipeline (Strict Non-Bypassable Sequence)

```text
Strategy
  └──> OrderIntent (Canonical, Immutable, Idempotent)
        └──> Pre-Flight Filters (Staleness, Future skew, Instrument metadata, Event Cluster)
              └──> Deterministic Risk Engine (Evaluated inside Router; Veto CANNOT be bypassed)
                    └──> Capital Authorization Gate ($0 Live Cap Policy)
                          └──> Execution Router
                                └──> SubmitPermit (One-time, non-forgeable authorization)
                                      └──> Exchange Adapter (Binance, Bybit, Deribit, Fake)
                                            └──> Venue Transport
```

Strategies never call exchange adapters directly. Every mutating action requires a cryptographically minted `SubmitPermit` issued exclusively by the `ExecutionRouter`.

---

## 3. Execution Modes

1. **`PAPER`**:
   - Simulated execution via in-memory `PaperBroker`.
   - Never touches venue APIs or transmits packets.
   - Preserves slippage, fill ratios, and latency models.
2. **`SHADOW`**:
   - Executes the complete production pipeline (OrderIntent construction, risk evaluation, instrument precision validation, venue request serialization).
   - Produces terminal state `WOULD_SUBMIT`.
   - Persists the serialized request and metadata in `execution_orders` table with `data_source="SHADOW"`.
   - Never transmits over network.
3. **`SANDBOX`**:
   - Executes against exchange testnets (Binance Testnet, Bybit Testnet, Deribit Testnet).
   - Uses dedicated `*_TESTNET_*` credentials and sandbox URLs.
   - Strict sandbox isolation prevents any fallthrough to production endpoints.
4. **`LIVE_LOCKED`** (Default Effective Mode):
   - Real venue connections, market data, and telemetry active.
   - Order submission rejected at the mode dispatch gate.
5. **`LIVE`**:
   - Production venue order submission.
   - **Gated by 9 mandatory conditions**:
     1. `execution_mode == LIVE`
     2. `authorized_live_capital_usd > 0`
     3. `RiskDecision.approved == True`
     4. `kill_switch_active == False`
     5. `reconciliation_status == "HEALTHY"`
     6. `account_status == "KNOWN"`
     7. `credentials_status == "CONFIGURED"`
     8. `instrument_metadata == VALID`
     9. `market_data_age <= max_signal_age_ms` (Freshness guarantee)

---

## 4. State Machine & Lifecycle

### Order States
- `INTENT_CREATED`
- `RISK_APPROVED` / `RISK_REJECTED`
- `ROUTING`
- `SUBMITTING`
- `ACKNOWLEDGED`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCEL_PENDING`
- `CANCELED`
- `REJECTED`
- `EXPIRED`
- `UNKNOWN_OUTCOME`
- `RECONCILIATION_REQUIRED`
- `WOULD_SUBMIT` (Shadow terminal)

### UNKNOWN_OUTCOME Invariant
If a network timeout, socket drop, or 5xx occurs during or after transmission:
- The order state is marked `UNKNOWN_OUTCOME`.
- It is **NEVER** treated as failed or canceled.
- It is **NEVER** blindly retried.
- Resolution requires querying the venue using the deterministic `client_order_id`.
- Only if the venue confirms the order was never received (`venue_absent_confirmed=True`) and freshness/risk checks pass can a safe retry occur.

---

## 5. Reconciliation Engine & Restart Recovery

- **Reconciliation Engine**: Compares locally tracked positions, open orders, and fills against exchange snapshots.
  - Detects `ORPHAN_VENUE_ORDER`, `STATE_DIVERGENCE`, `FILL_MISSING_LOCALLY`, `FILL_QTY_MISMATCH`, and `POSITION_MISMATCH`.
  - Any discrepancy marks the venue as `MISMATCH` and halts new submissions.
- **Restart Recovery**:
  - Re-evaluates all non-terminal orders on system boot.
  - Unacknowledged in-flight submissions (`SUBMITTING`) are converted to `UNKNOWN_OUTCOME`.
  - Marks venue status as `UNKNOWN` and locks execution until reconciliation passes.

---

## 6. Telemetry & Safety Subsystems

1. **Clock Drift Monitor (`ClockMonitor`)**:
   - Continuously samples exchange server time vs local time.
   - Drift `> 250ms`: `WARN`.
   - Drift `> 1000ms`: `BLOCK` (rejects new submissions).
2. **Venue Rate Limiter (`VenueRateLimiter`)**:
   - Tracks request weights in sliding windows.
   - Enforces exponential cooldown on HTTP 429 / 418.
3. **Execution Kill Switch (`ExecutionKillSwitch`)**:
   - Persisted across restarts in `kill_switch_events`.
   - Scopes: `GLOBAL`, `VENUE`, `ACCOUNT`, `STRATEGY`, `SYMBOL`.
   - Cancels open orders when requested; **NEVER** executes automatic market flattening.

---

## 7. Control Plane Persistence Schema

All execution events are recorded in SQLite control plane tables (`data/control_plane/control_plane.db`):
- `execution_intents`: Canonical immutable intents.
- `execution_orders`: Mutable order lifecycle projection.
- `execution_attempts`: Submission attempts (persisted before network transmission).
- `order_state_transitions`: Complete historical state transition log.
- `execution_fills`: Individual trade fills and fee attribution.
- `reconciliation_events`: Reconciliation audit and mismatch diffs.
- `connection_events`: Network and stream connection lifecycles.
- `rate_limit_events`: Rate limiting and penalty logs.
- `latency_samples`: Millisecond-level duration traces.
- `account_snapshots`: Venue balances and equity records.

---

## 8. Operational API Endpoints (Strictly Read-Only)

All `/api/execution/*` endpoints are HTTP `GET` only:
- `GET /api/execution/status` — Operational safety state, effective mode, and invariants.
- `GET /api/execution/venues` — Venue capabilities and health.
- `GET /api/execution/orders` — Historical and active order summaries.
- `GET /api/execution/fills` — Execution fills and fees.
- `GET /api/execution/reconciliation` — Latest reconciliation audit results.
- `GET /api/execution/latency` — Latency percentiles (p50, p95, p99).
- `GET /api/execution/credentials/status` — Configuration status (values never exposed).
- `GET /api/execution/account-status` — Normalized venue account status.
