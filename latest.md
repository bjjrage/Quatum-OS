# Snapshot Quant OS — 2026-10-13 21:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ -84.10 (291 resueltas) · aciertos 40% · t por ventana -0.8387298218090913
- Criterio: todavía no

## Salud

- api: RUNNING
- web: RUNNING
- os_launcher: RUNNING
- supervisor: RUNNING
- markets_recorder: RUNNING
- paper_runtime: RUNNING
- pumpfun_recorder: DISABLED
- pumpfun_paper: DISABLED
- leader_paper: RUNNING
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 1.6 min
- btc_tendencia: actualizado hace 1.6 min
- carry_funding: actualizado hace 1.6 min
- combinada: actualizado hace 1.6 min
- examen_2x: actualizado hace 25.3 min
- flujo_7d: actualizado hace 1.6 min
- flujo_reg200: actualizado hace 1.6 min
- flujo_sectorial: actualizado hace 1.6 min
- flujo_v1: actualizado hace 1.6 min
- lider_azar: actualizado hace 1.6 min
- lider_corto: actualizado hace 1.6 min
- lider_sin_x: actualizado hace 1.6 min
- lider_x: actualizado hace 1.6 min
- mezcla_flujo_carry: actualizado hace 1.6 min
- poly_updown: actualizado hace 8986.8 min
- unlock_short_v1: actualizado hace 0.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 358 | -0.6 |
| binance_perp/depth_snapshots | 10 | 0.7 |
| binance_perp/forced_liquidations | 34 | -0.3 |
| binance_perp/futures_market_metrics | 36 | -0.3 |
| binance_perp/futures_open_interest | 37 | -0.3 |
| binance_perp/futures_positioning | 35 | -0.3 |
| binance_perp/orderbook_l2_depth | 73 | -1.0 |
| binance_perp/trade_ticks | 36 | -0.3 |
| deribit/bbo_ticks | 35 | 24.7 |
| deribit/deribit_metrics | 35 | 24.7 |
| deribit/trade_ticks | 21 | 25.7 |
| dexscreener/token_boosts | 4 | 31.9 |
| dexscreener/token_prices | 34 | 24.9 |
| dexscreener/token_profiles | 12 | 26.9 |
| limitless/limitless_book | 36 | 24.9 |
| limitless/limitless_markets | 7 | 24.9 |
| polymarket/bbo_ticks | 261 | 24.7 |
| polymarket/orderbook_l2_depth | 35 | 24.7 |
| polymarket/polymarket_metadata_history | 9 | 25.8 |
| polymarket/trade_ticks | 32 | 24.7 |
| pumpfun/creator_funding | 33 | 24.8 |
| pumpfun/pumpfun_completes | 24 | 24.8 |
| pumpfun/pumpfun_creates | 36 | 24.9 |
| pumpfun/pumpfun_trades | 37 | 24.9 |
| pumpfun/x_mentions | 0 | 9866.9 |
| telegram/calls | 9 | 25.9 |

## Problemas en logs (últimos)

### os_launcher.log
```
Traceback (most recent call last):
```
### poly_paper.log
```
{"timestamp_utc": "2026-10-07T16:01:47Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:01:51Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Binance WS: ConnectionClosedError: no close frame received or sent; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:01:52Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:02:18Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:02:33Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:02:46Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: TimeoutError: timed out during opening handshake; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:02:58Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:03:57Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-13T20:56:23Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T21:05:06Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 1s"}
{"timestamp_utc": "2026-10-13T21:05:08Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-13T21:05:08Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 2s"}
{"timestamp_utc": "2026-10-13T21:05:11Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 4s"}
{"timestamp_utc": "2026-10-13T21:05:16Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 8s"}
{"timestamp_utc": "2026-10-13T21:05:25Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 16s"}
{"timestamp_utc": "2026-10-13T21:20:37Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.