# Snapshot Quant OS — 2026-10-17 17:51 UTC

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

- baja_vol: actualizado hace 1.0 min
- btc_tendencia: actualizado hace 1.0 min
- carry_funding: actualizado hace 1.0 min
- combinada: actualizado hace 1.0 min
- examen_2x: actualizado hace 5545.3 min
- flujo_7d: actualizado hace 1.0 min
- flujo_reg200: actualizado hace 1.0 min
- flujo_sectorial: actualizado hace 1.0 min
- flujo_v1: actualizado hace 1.0 min
- lider_azar: actualizado hace 1.0 min
- lider_corto: actualizado hace 1.0 min
- lider_sin_x: actualizado hace 1.0 min
- lider_x: actualizado hace 1.0 min
- mezcla_flujo_carry: actualizado hace 1.0 min
- poly_updown: actualizado hace 14506.9 min
- unlock_short_v1: actualizado hace 45.2 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 913 | -1.8 |
| binance_perp/depth_snapshots | 18 | 3.0 |
| binance_perp/forced_liquidations | 61 | -1.8 |
| binance_perp/futures_market_metrics | 62 | -1.8 |
| binance_perp/futures_open_interest | 62 | -1.8 |
| binance_perp/futures_positioning | 62 | -2.0 |
| binance_perp/orderbook_l2_depth | 138 | -2.3 |
| binance_perp/trade_ticks | 68 | -1.8 |
| deribit/bbo_ticks | 0 | 5544.8 |
| deribit/deribit_metrics | 0 | 5544.8 |
| deribit/trade_ticks | 0 | 5545.8 |
| dexscreener/token_boosts | 0 | 5551.9 |
| dexscreener/token_prices | 0 | 5544.9 |
| dexscreener/token_profiles | 0 | 5546.9 |
| limitless/limitless_book | 0 | 5544.9 |
| limitless/limitless_markets | 0 | 5544.9 |
| polymarket/bbo_ticks | 0 | 5544.8 |
| polymarket/orderbook_l2_depth | 0 | 5544.8 |
| polymarket/polymarket_metadata_history | 0 | 5545.8 |
| polymarket/trade_ticks | 0 | 5544.8 |
| pumpfun/creator_funding | 0 | 5544.9 |
| pumpfun/pumpfun_completes | 0 | 5544.9 |
| pumpfun/pumpfun_creates | 0 | 5544.9 |
| pumpfun/pumpfun_trades | 0 | 5544.9 |
| pumpfun/x_mentions | 0 | 15387.0 |
| telegram/calls | 0 | 5545.9 |

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
{"timestamp_utc": "2026-10-17T16:54:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-17T16:54:32Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-17T16:54:36Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-17T16:55:04Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-17T17:54:08Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-17T17:54:10Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-17T17:54:13Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-17T17:54:57Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.