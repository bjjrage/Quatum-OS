# Trading / Quant OS (Quantum-OS)

High-performance market data foundation and quantitative research engine for prediction markets (Polymarket), crypto derivatives (Deribit), and perpetual futures (Binance USDⓈ-M).

---

## Architecture Overview

```
TRADING OS / Quantum-OS
├── config/              # Centralized environment & venue configurations
├── src/
│   ├── collectors/      # Multi-venue live market data recorders & pollers
│   │   ├── binance_oi_poller.py    # REST Open Interest poller (30s cadence)
│   │   ├── binance_recorder.py     # Public/Market WebSocket streams (bookTicker, depth5, aggTrade, markPrice, !forceOrder)
│   │   ├── deribit_recorder.py     # DVOL, index prices, trades, options ticker metrics
│   │   ├── polymarket_recorder.py  # CLOB WS (book, price_change, last_trade_price, tick_size_change)
│   │   └── manager.py              # Orchestration & lifecycle manager
│   ├── common/          # Low-latency primitives, schemas & storage engine
│   │   ├── dns_patch.py            # Transparent DNS resolver fallback for edge routing
│   │   ├── logger.py               # Structured JSON logger
│   │   ├── manifest.py             # SHA-256 partition manifest & verification
│   │   ├── storage_sink.py         # Async buffered Parquet writer (atomic rename, Zstd level 7)
│   │   └── types.py                # Strict nanosecond timestamp types & PyArrow schemas
│   └── quant/           # Pure mathematical pricing & volatility models (Line A)
│       ├── black76.py              # Reference Black-76 pricing, greeks, and flat-vol probability
│       ├── deribit_inverse.py      # Inverse-option numéraire proof & normalization
│       ├── digital_probability.py  # Analytic strike derivative with skew & finite difference
│       └── smile_validation.py     # Volatility smiles & strict no-arbitrage validators
├── tests/
│   ├── math/            # 29 unit tests for pricing, skew, arbitrage, and numéraire
│   └── ...              # Batch 0 storage, schema, and parser unit tests
└── scripts/
    ├── run_recorder.py             # Continuous production market recorder
    ├── smoke_test.py               # Live multi-venue connectivity & DuckDB verification
    └── verify_data.py              # Lakehouse dataset inspector
```

---

## Key Features

1. **Strict Timestamp Architecture:**
   - `ts_exchange_ns`: Exchange epoch timestamp (UTC nanoseconds).
   - `ts_received_utc_ns`: Application receive epoch timestamp (UTC nanoseconds).
   - `ts_received_mono_ns`: Monotonic timestamp local (for internal durations).
   - `observed_event_age_ns`: Latency estimate (`ts_received_utc_ns - ts_exchange_ns`).

2. **Immutable Lakehouse Sink:**
   - Multi-partition Parquet writer with Zstandard compression.
   - Atomic `.tmp` rename pattern prevents partial reads.
   - SHA-256 partition manifests for cryptographic auditability.

3. **Line A Quantitative Engine (Deribit Math Spike):**
   - **Numéraire Proof:** Rigorous proof of terminal payoff equivalence ($\Pi_T^{USD} \equiv \Pi_T^{BTC} \times S_T$) and change of numéraire ($\mathbb{Q} \leftrightarrow \mathbb{Q}^{BTC}$).
   - **Breeden-Litzenberger Digital Probability:** Exact strike derivative with skew:
     $$P_{RN}(S_T \ge K) = \mathcal{N}(d_2) - F \phi(d_1)\sqrt{T}\frac{d\sigma}{dK}$$
   - **Arbitrage Bounds:** Strict checks for call monotonicity, convexity ($d^2C/dK^2 \ge 0$), and non-negative risk-neutral density ($q(K) \ge 0$).

---

## Getting Started

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation
```bash
# Clone the repository
git clone https://github.com/bjjrage/Quatum-OS.git
cd Quatum-OS

# Sync virtual environment and dependencies
uv sync
```

### Running Tests
```bash
# Run all 36 unit tests
uv run pytest -v
```

### Running the Live Smoke Test
```bash
# Run 10-second multi-venue live verification
uv run python scripts/smoke_test.py --duration 10
```

### Starting the Production Recorder
```bash
# Run continuous production market data recorder
uv run python scripts/run_recorder.py
```
