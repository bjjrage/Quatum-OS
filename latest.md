# Snapshot Quant OS — 2026-10-13 20:51 UTC

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
- pumpfun_recorder: RUNNING
- pumpfun_paper: DISABLED
- leader_paper: RUNNING
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 1.9 min
- btc_tendencia: actualizado hace 1.9 min
- carry_funding: actualizado hace 1.9 min
- combinada: actualizado hace 1.9 min
- examen_2x: actualizado hace 1.9 min
- flujo_7d: actualizado hace 1.9 min
- flujo_reg200: actualizado hace 1.9 min
- flujo_sectorial: actualizado hace 1.9 min
- flujo_v1: actualizado hace 1.9 min
- lider_azar: actualizado hace 1.9 min
- lider_corto: actualizado hace 1.9 min
- lider_sin_x: actualizado hace 1.9 min
- lider_x: actualizado hace 1.9 min
- mezcla_flujo_carry: actualizado hace 1.9 min
- poly_updown: actualizado hace 8927.4 min
- unlock_short_v1: actualizado hace 46.2 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 842 | -6.5 |
| binance_perp/depth_snapshots | 20 | -5.4 |
| binance_perp/forced_liquidations | 64 | -6.3 |
| binance_perp/futures_market_metrics | 66 | -7.4 |
| binance_perp/futures_open_interest | 68 | -8.4 |
| binance_perp/futures_positioning | 69 | -8.4 |
| binance_perp/orderbook_l2_depth | 142 | -10.9 |
| binance_perp/trade_ticks | 70 | -10.4 |
| deribit/bbo_ticks | 71 | -11.4 |
| deribit/deribit_metrics | 73 | -13.1 |
| deribit/trade_ticks | 60 | -15.5 |
| dexscreener/token_boosts | 7 | -15.5 |
| dexscreener/token_prices | 74 | -15.5 |
| dexscreener/token_profiles | 34 | -14.4 |
| limitless/limitless_book | 76 | -15.5 |
| limitless/limitless_markets | 16 | -14.4 |
| polymarket/bbo_ticks | 831 | -16.9 |
| polymarket/orderbook_l2_depth | 76 | -16.5 |
| polymarket/polymarket_metadata_history | 20 | -14.4 |
| polymarket/trade_ticks | 71 | -16.5 |
| pumpfun/creator_funding | 74 | -13.1 |
| pumpfun/pumpfun_completes | 53 | -16.5 |
| pumpfun/pumpfun_creates | 78 | -17.5 |
| pumpfun/pumpfun_trades | 95 | -17.5 |
| pumpfun/x_mentions | 0 | 9807.5 |
| telegram/calls | 14 | -12.6 |

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
{"timestamp_utc": "2026-10-13T20:56:05Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for ORDIUSDT due to polling failure."}
{"timestamp_utc": "2026-10-13T20:56:23Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T21:05:06Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 1s"}
{"timestamp_utc": "2026-10-13T21:05:08Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-13T21:05:08Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 2s"}
{"timestamp_utc": "2026-10-13T21:05:11Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 4s"}
{"timestamp_utc": "2026-10-13T21:05:16Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 8s"}
{"timestamp_utc": "2026-10-13T21:05:25Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 16s"}
```

Detalle completo en latest.json.